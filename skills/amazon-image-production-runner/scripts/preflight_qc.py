from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any


# BOUNDED_RATIO_EXPORT: image tools return a fixed pixel budget, so raw ratios
# land a fraction of a percent off non-square targets (for example 1959x803 for
# 1464x600). Keep this equal to postprocess_images.py and design_workflow_state.py.
MAX_ASPECT_CORRECTION_PCT = 1.0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:32]
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        return struct.unpack(">II", header[16:24])
    from PIL import Image

    with Image.open(path) as image:
        return int(image.width), int(image.height)


def normalize_text(value: str) -> str:
    return "".join(re.findall(r"[\w\u4e00-\u9fff]+", value.casefold()))


def aspect_error_pct(actual: tuple[int, int], target: tuple[int, int]) -> float:
    actual_ratio = actual[0] / actual[1]
    target_ratio = target[0] / target[1]
    return abs(actual_ratio / target_ratio - 1.0) * 100.0


def resolve_project_path(root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {value}") from exc
    return resolved


def load_manifest_corrections(manifest_path: Path | None) -> list[dict[str, Any]]:
    if manifest_path is None or not manifest_path.is_file():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    corrections = data.get("dimension_corrections", []) if isinstance(data, dict) else []
    return corrections if isinstance(corrections, list) else []


def run_ocr(path: Path, command: str) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            [command, str(path), "stdout"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "OCR_ERROR", str(exc)
    if completed.returncode != 0:
        return "OCR_ERROR", completed.stderr.strip() or f"exit {completed.returncode}"
    return "OCR_CAPTURED", completed.stdout


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def run_preflight(
    root: Path,
    plan_path: Path,
    *,
    manifest_path: Path | None = None,
    ocr_command: str | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    slots = plan.get("slots", []) if isinstance(plan, dict) else []
    errors: list[str] = []
    slot_results: list[dict[str, Any]] = []
    corrections = load_manifest_corrections(manifest_path)
    correction_by_output: dict[str, dict[str, Any]] = {}
    for correction in corrections:
        if not isinstance(correction, dict):
            continue
        output = str(correction.get("output_path", ""))
        try:
            correction_by_output[str(resolve_project_path(root, output))] = correction
        except ValueError as exc:
            errors.append(str(exc))

    command = shutil.which("tesseract") if ocr_command is None else ocr_command
    needs_visual_qc = False
    for slot in slots:
        slot_id = str(slot.get("slot_id", ""))
        output_value = str(slot.get("output_path", ""))
        inspection_value = str(slot.get("raw_output_path", output_value))
        slot_errors: list[str] = []
        result: dict[str, Any] = {
            "slot_id": slot_id,
            "output_path": output_value,
            "inspection_path": inspection_value,
            "exists": False,
            "sha256": None,
            "dimensions": None,
            "dimension_status": "NOT_CHECKED",
            "ocr_status": "NOT_REQUIRED",
            "requires_visual_qc": False,
            "errors": slot_errors,
        }
        try:
            output = resolve_project_path(root, inspection_value)
        except ValueError as exc:
            slot_errors.append(str(exc))
            errors.append(f"{slot_id}: {exc}")
            slot_results.append(result)
            continue
        if not output.is_file():
            slot_errors.append("inspection output file is missing")
            errors.append(f"{slot_id}: inspection output file is missing")
            slot_results.append(result)
            continue
        result["exists"] = True
        result["sha256"] = file_sha256(output)
        try:
            actual = image_dimensions(output)
            result["dimensions"] = list(actual)
        except Exception as exc:
            slot_errors.append(f"cannot read dimensions: {exc}")
            errors.append(f"{slot_id}: cannot read dimensions")
            slot_results.append(result)
            continue
        target_value = slot.get("target_size", [])
        if (
            not isinstance(target_value, list)
            or len(target_value) != 2
            or not all(isinstance(value, int) and value > 0 for value in target_value)
        ):
            slot_errors.append("target_size must contain two positive integers")
            errors.append(f"{slot_id}: invalid target_size")
            slot_results.append(result)
            continue
        target = (target_value[0], target_value[1])
        if actual != target:
            ratio_error = aspect_error_pct(actual, target)
            result["aspect_error_pct"] = round(ratio_error, 6)
            if actual[0] * target[1] == target[0] * actual[1]:
                result["dimension_status"] = "SAME_ASPECT_RESIZE_REQUIRED"
                result["requires_visual_qc"] = True
                needs_visual_qc = True
            elif ratio_error <= MAX_ASPECT_CORRECTION_PCT:
                result["dimension_status"] = "SMALL_RATIO_CORRECTION_CANDIDATE"
                result["requires_visual_qc"] = True
                needs_visual_qc = True
            else:
                result["dimension_status"] = "FAIL"
                slot_errors.append(
                    f"dimensions {actual[0]}x{actual[1]} exceed the {MAX_ASPECT_CORRECTION_PCT:g}% "
                    f"BOUNDED_RATIO_EXPORT limit for target {target_value}"
                )
                errors.append(
                    f"{slot_id}: BOUNDED_RATIO_EXPORT ratio error exceeds {MAX_ASPECT_CORRECTION_PCT:g}%"
                )
        else:
            result["dimension_status"] = "PASS"

        try:
            final_output = resolve_project_path(root, output_value)
        except ValueError:
            final_output = output
        correction = correction_by_output.get(str(final_output)) or correction_by_output.get(str(output))
        if correction:
            ratio_error = correction.get("aspect_error_pct")
            if (
                correction.get("method") != "SMALL_RATIO_CORRECTION"
                or not isinstance(ratio_error, (int, float))
                or ratio_error > MAX_ASPECT_CORRECTION_PCT
            ):
                slot_errors.append(
                    f"dimension correction exceeds the {MAX_ASPECT_CORRECTION_PCT:g}% BOUNDED_RATIO_EXPORT limit"
                )
                errors.append(
                    f"{slot_id}: BOUNDED_RATIO_EXPORT correction exceeds {MAX_ASPECT_CORRECTION_PCT:g}%"
                )

        expected_copy = [str(item) for item in slot.get("image_embedded_copy", []) if str(item).strip()]
        if expected_copy:
            if not command:
                result["ocr_status"] = "OCR_UNAVAILABLE"
                result["requires_visual_qc"] = True
                needs_visual_qc = True
            else:
                capture_status, captured = run_ocr(output, command)
                if capture_status != "OCR_CAPTURED":
                    result["ocr_status"] = capture_status
                    result["requires_visual_qc"] = True
                    result["ocr_detail"] = captured
                    needs_visual_qc = True
                else:
                    normalized_capture = normalize_text(captured)
                    missing_copy = [
                        item
                        for item in expected_copy
                        if normalize_text(item) not in normalized_capture
                    ]
                    if missing_copy:
                        result["ocr_status"] = "FAIL"
                        result["missing_copy"] = missing_copy
                        slot_errors.append("OCR did not find all expected copy")
                        errors.append(f"{slot_id}: OCR copy mismatch")
                    else:
                        result["ocr_status"] = "PASS"
        slot_results.append(result)

    status = "FAIL" if errors else ("NEEDS_VISUAL_QC" if needs_visual_qc else "PASS")
    report = {
        "version": 1,
        "status": status,
        "max_aspect_correction_pct": MAX_ASPECT_CORRECTION_PCT,
        "ocr_engine": command or None,
        "slots": slot_results,
        "errors": errors,
    }
    atomic_write_json(root / "preview/preflight_qc.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cheap deterministic checks before visual/model QC.")
    parser.add_argument("--base-dir", required=True, type=Path)
    parser.add_argument("--plan", default="production_plan.json", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--disable-ocr", action="store_true")
    args = parser.parse_args()
    root = args.base_dir.expanduser().resolve()
    plan = args.plan if args.plan.is_absolute() else root / args.plan
    manifest = args.manifest
    if manifest is not None and not manifest.is_absolute():
        manifest = root / manifest
    report = run_preflight(
        root,
        plan,
        manifest_path=manifest,
        ocr_command="" if args.disable_ocr else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
