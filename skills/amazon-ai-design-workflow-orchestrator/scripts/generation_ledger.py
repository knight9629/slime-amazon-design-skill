from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


VALID_ROUTES = {"DIRECT_IMAGE_INPUT", "VISUAL_CONTEXT_RELAY"}
VALID_ERROR_TYPES = {"AUTH", "NETWORK", "RATE_LIMIT", "TIMEOUT", "TRANSPORT", "OTHER"}
TIMING_TOLERANCE_MS = 2_000
MAX_ELAPSED_MS = 7 * 24 * 60 * 60 * 1000


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_png_dimensions(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    position = 8
    width: int | None = None
    height: int | None = None
    idat_parts: list[bytes] = []
    saw_iend = False
    first_chunk = True
    while position < len(data):
        if position + 12 > len(data):
            return None
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        chunk_end = position + 12 + length
        if chunk_end > len(data):
            return None
        chunk_data = data[position + 8 : position + 8 + length]
        stored_crc = struct.unpack(">I", data[position + 8 + length : chunk_end])[0]
        if (zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF) != stored_crc:
            return None
        if first_chunk and chunk_type != b"IHDR":
            return None
        if chunk_type == b"IHDR":
            if not first_chunk or length != 13:
                return None
            (
                width,
                height,
                bit_depth,
                color_type,
                compression_method,
                filter_method,
                interlace_method,
            ) = struct.unpack(">IIBBBBB", chunk_data)
            allowed_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if (
                width <= 0
                or height <= 0
                or bit_depth not in allowed_depths.get(color_type, set())
                or compression_method != 0
                or filter_method != 0
                or interlace_method not in {0, 1}
            ):
                return None
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                return None
            saw_iend = True
            position = chunk_end
            break
        first_chunk = False
        position = chunk_end
    if width is None or height is None or not idat_parts or not saw_iend:
        return None
    try:
        if not zlib.decompress(b"".join(idat_parts)):
            return None
    except zlib.error:
        return None
    return width, height


def dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        image_size = verified_png_dimensions(data)
        return image_size if image_size is not None else (None, None)
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = int(image.width), int(image.height)
            image.verify()
        return width, height
    except Exception:
        return None, None


def parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def finite_elapsed_ms(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0 or numeric > MAX_ELAPSED_MS:
        return None
    return numeric


def project_relative(root: Path, path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(root.expanduser().resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {path}") from exc


def create_record(
    *,
    root: Path,
    run_identity: str,
    generation_id: str,
    stage: str,
    slot_id: str,
    route: str,
    prompt: str,
    reference_paths: list[Path],
    output_path: Path,
    elapsed_ms: int,
    pairwise_controls_sha256: str | None = None,
) -> dict[str, Any]:
    if route not in VALID_ROUTES:
        raise ValueError(f"unsupported generation route: {route}")
    elapsed_value = finite_elapsed_ms(elapsed_ms)
    if elapsed_value is None:
        raise ValueError("elapsed_ms must be finite and within the supported range")
    normalized_controls_hash = (
        str(pairwise_controls_sha256).strip().lower()
        if pairwise_controls_sha256 is not None
        else ""
    )
    if stage == "VISUAL_PREFERENCE_PAIRWISE" and not normalized_controls_hash:
        raise ValueError(
            "pairwise_controls_sha256 is required for VISUAL_PREFERENCE_PAIRWISE"
        )
    if normalized_controls_hash and not re.fullmatch(
        r"[0-9a-f]{64}", normalized_controls_hash
    ):
        raise ValueError("pairwise_controls_sha256 must be a SHA-256 hash")
    output_path = output_path.expanduser().resolve()
    if not output_path.is_file():
        raise FileNotFoundError(output_path)
    completed_at = datetime.now()
    started_at = completed_at - timedelta(milliseconds=elapsed_value)
    width, height = dimensions(output_path)
    references = []
    for path in reference_paths:
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        references.append(
            {
                "path": project_relative(root, resolved),
                "sha256": file_sha256(resolved),
                "role": "PRODUCT_REFERENCE",
            }
        )
    record = {
        "version": 1,
        "provider": "image2",
        "run_identity": run_identity,
        "generation_id": generation_id,
        "stage": stage,
        "slot_id": slot_id,
        "status": "SUCCEEDED",
        "route": route,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "reference_inputs": references,
        "started_at": started_at.isoformat(timespec="milliseconds"),
        "completed_at": completed_at.isoformat(timespec="milliseconds"),
        "elapsed_ms": elapsed_ms,
        "output_path": project_relative(root, output_path),
        "width": width,
        "height": height,
        "output_sha256": file_sha256(output_path),
    }
    profile_path = root.expanduser().resolve() / "visual_preference_profile.json"
    if profile_path.is_file() and stage != "VISUAL_PREFERENCE_PAIRWISE":
        record["visual_preference_profile_sha256"] = file_sha256(profile_path)
    if normalized_controls_hash:
        record["pairwise_controls_sha256"] = normalized_controls_hash
    return record


def create_failure_record(
    *,
    run_identity: str,
    generation_id: str,
    stage: str,
    slot_id: str,
    error_type: str,
    error_message: str,
    elapsed_ms: int,
) -> dict[str, Any]:
    normalized_error = error_type.strip().upper()
    if normalized_error not in VALID_ERROR_TYPES:
        raise ValueError(
            "unsupported error_type; expected one of "
            + ", ".join(sorted(VALID_ERROR_TYPES))
        )
    elapsed_value = finite_elapsed_ms(elapsed_ms)
    if elapsed_value is None:
        raise ValueError("elapsed_ms must be finite and within the supported range")
    if not error_message.strip():
        raise ValueError("error_message is required")
    completed_at = datetime.now()
    started_at = completed_at - timedelta(milliseconds=elapsed_value)
    return {
        "version": 1,
        "provider": "image2",
        "run_identity": run_identity,
        "generation_id": generation_id,
        "stage": stage,
        "slot_id": slot_id,
        "status": "FAILED",
        "error_type": normalized_error,
        "transport_error": normalized_error != "OTHER",
        "error_message": error_message.strip(),
        "started_at": started_at.isoformat(timespec="milliseconds"),
        "completed_at": completed_at.isoformat(timespec="milliseconds"),
        "elapsed_ms": elapsed_ms,
    }


def append_record(path: Path, record: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return path


def read_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return records, ["generation_ledger.jsonl is missing"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(
                line,
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    ValueError(f"non-finite JSON number {constant}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"line {line_number} invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number} must be an object")
            continue
        records.append(value)
    return records, errors


def validate_output_evidence(
    ledger_path: Path,
    *,
    root: Path,
    output_path: Path,
    run_identity: str,
    stage: str,
) -> dict[str, Any]:
    records, errors = read_records(ledger_path)
    output_path = output_path.expanduser().resolve()
    if not output_path.is_file():
        errors.append(f"output does not exist: {output_path}")
        return {"valid": False, "errors": errors, "record": None}
    relative = project_relative(root, output_path)
    matches = [
        record
        for record in records
        if record.get("output_path") == relative
        and record.get("run_identity") == run_identity
        and record.get("stage") == stage
        and record.get("status") == "SUCCEEDED"
    ]
    if not matches:
        errors.append(f"no successful image2 ledger record for {relative} at {stage}")
        return {"valid": False, "errors": errors, "record": None}
    record = matches[-1]
    if record.get("version") != 1:
        errors.append(f"ledger version must be 1 for {relative}")
    if record.get("provider") != "image2":
        errors.append(f"provider is not image2 for {relative}")
    for field in ("generation_id", "slot_id"):
        if not str(record.get(field, "")).strip():
            errors.append(f"{field} is missing for {relative}")
    elapsed_ms = record.get("elapsed_ms")
    elapsed_value = finite_elapsed_ms(elapsed_ms)
    if elapsed_value is None:
        errors.append(f"elapsed_ms is missing or invalid for {relative}")
    started_at = parse_iso_timestamp(record.get("started_at"))
    completed_at = parse_iso_timestamp(record.get("completed_at"))
    if started_at is None or completed_at is None:
        errors.append(f"timestamps are missing or invalid for {relative}")
    elif started_at.tzinfo != completed_at.tzinfo:
        errors.append(f"timestamps mix timezone-aware and naive values for {relative}")
    else:
        measured_ms = (completed_at - started_at).total_seconds() * 1000
        if measured_ms < 0:
            errors.append(f"timestamps are reversed for {relative}")
        elif elapsed_value is not None:
            if abs(measured_ms - elapsed_value) > TIMING_TOLERANCE_MS:
                errors.append(f"elapsed_ms is inconsistent with timestamps for {relative}")
    if record.get("route") not in VALID_ROUTES:
        errors.append(f"invalid route for {relative}")
    if not isinstance(record.get("prompt_sha256"), str) or len(record["prompt_sha256"]) != 64:
        errors.append(f"prompt hash is missing or invalid for {relative}")
    if record.get("output_sha256") != file_sha256(output_path):
        errors.append(f"output hash mismatch for {relative}")
    actual_width, actual_height = dimensions(output_path)
    if actual_width is None or actual_height is None:
        errors.append(f"output dimensions are unavailable for {relative}")
    elif (
        isinstance(record.get("width"), bool)
        or isinstance(record.get("height"), bool)
        or not isinstance(record.get("width"), int)
        or not isinstance(record.get("height"), int)
        or record.get("width", 0) <= 0
        or record.get("height", 0) <= 0
        or record.get("width") != actual_width
        or record.get("height") != actual_height
    ):
        errors.append(f"output dimensions mismatch for {relative}")
    references = record.get("reference_inputs")
    if not isinstance(references, list):
        errors.append(f"reference_inputs must be a list for {relative}")
    elif stage == "STYLE_SAMPLES" and not references:
        errors.append(f"reference_inputs are required for style sample {relative}")
    else:
        for index, item in enumerate(references):
            if not isinstance(item, dict):
                errors.append(f"reference_inputs[{index}] is invalid for {relative}")
                continue
            ref_path = root / str(item.get("path", ""))
            if not ref_path.is_file():
                errors.append(f"reference input is missing: {item.get('path')}")
            elif item.get("sha256") != file_sha256(ref_path):
                errors.append(f"reference hash mismatch: {item.get('path')}")
    return {"valid": not errors, "errors": errors, "record": record}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record or validate image2 provenance.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--project-root", required=True, type=Path)
    record_parser.add_argument("--run-identity", required=True)
    record_parser.add_argument("--generation-id", required=True)
    record_parser.add_argument("--stage", required=True)
    record_parser.add_argument("--slot-id", required=True)
    record_parser.add_argument("--route", required=True, choices=sorted(VALID_ROUTES))
    record_parser.add_argument("--prompt-file", required=True, type=Path)
    record_parser.add_argument("--reference", action="append", default=[], type=Path)
    record_parser.add_argument("--output", required=True, type=Path)
    record_parser.add_argument("--elapsed-ms", required=True, type=int)
    record_parser.add_argument("--pairwise-controls-sha256")
    failure_parser = subparsers.add_parser("record-failure")
    failure_parser.add_argument("--project-root", required=True, type=Path)
    failure_parser.add_argument("--run-identity", required=True)
    failure_parser.add_argument("--generation-id", required=True)
    failure_parser.add_argument("--stage", required=True)
    failure_parser.add_argument("--slot-id", required=True)
    failure_parser.add_argument(
        "--error-type", required=True, choices=sorted(VALID_ERROR_TYPES)
    )
    failure_parser.add_argument("--error-message", required=True)
    failure_parser.add_argument("--elapsed-ms", required=True, type=int)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    if args.command == "record-failure":
        record = create_failure_record(
            run_identity=args.run_identity,
            generation_id=args.generation_id,
            stage=args.stage,
            slot_id=args.slot_id,
            error_type=args.error_type,
            error_message=args.error_message,
            elapsed_ms=args.elapsed_ms,
        )
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8")
        record = create_record(
            root=root,
            run_identity=args.run_identity,
            generation_id=args.generation_id,
            stage=args.stage,
            slot_id=args.slot_id,
            route=args.route,
            prompt=prompt,
            reference_paths=args.reference,
            output_path=args.output,
            elapsed_ms=args.elapsed_ms,
            pairwise_controls_sha256=args.pairwise_controls_sha256,
        )
    append_record(root / "generation_ledger.jsonl", record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
