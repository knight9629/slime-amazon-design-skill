from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


DELEGATION_THRESHOLD_SECONDS = 120
HARD_MAX_CHILD_WORKERS = 3
VALID_GROUPS = {"MAIN", "APLUS_BASIC", "APLUS_PREMIUM_DESKTOP", "APLUS_PREMIUM_MOBILE"}
VISUAL_PREFERENCE_REQUIRED_SINCE = (0, 6, 10)
SLOT_GROUP_DIRECTORIES = {
    "main": "main_1x1", "main_portrait": "main_portrait",
    "basic_aplus": "a_plus_basic",
    "premium_aplus_desktop": "a_plus_premium_desktop",
    "premium_aplus_mobile": "a_plus_premium_mobile",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def atomic_write_json(path: Path, data: dict[str, Any]) -> Path:
    return atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def safe_relative_path(root: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"plan path must be relative: {value}")
    project_root = root.resolve()
    resolved = (project_root / candidate).resolve()
    try:
        relative = resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"plan path escapes project root: {value}") from exc
    return relative.as_posix()


def should_delegate(task: dict[str, Any]) -> bool:
    seconds = task.get("estimated_seconds")
    return (
        isinstance(seconds, (int, float))
        and seconds >= DELEGATION_THRESHOLD_SECONDS
        and task.get("independent") is True
        and task.get("parallel_gain") is True
    )


def workflow_version_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.\d+)?", value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def visual_preference_required(root: Path) -> bool:
    project_root = root.expanduser().resolve()
    if (project_root / "visual_reference_pool.json").is_file() or (
        project_root / "visual_preference_profile.json"
    ).is_file():
        return True
    active_run_path = project_root / "active_run.json"
    if not active_run_path.is_file():
        return False
    try:
        active_run = json.loads(active_run_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return True
    if not isinstance(active_run, dict):
        return True
    if "workflow_version" not in active_run:
        return False
    raw_version = active_run.get("workflow_version")
    version = workflow_version_tuple(raw_version)
    if version is None:
        return True
    return version >= VISUAL_PREFERENCE_REQUIRED_SINCE


def slot_manifest_for_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Derive the explicit stable exporter contract without inventing filenames or paths."""
    slots: list[dict[str, Any]] = []
    for slot in plan["slots"]:
        slot_id = str(slot.get("slot_id", "")).strip()
        if not re.fullmatch(r"[A-Z]{1,5}\d{2}(?:S\d+)?", slot_id):
            raise ValueError(f"invalid stable export slot_id: {slot_id}")
        size = slot["target_size"]
        group = str(slot["group"]).upper()
        if group == "MAIN":
            if size[0] == size[1]:
                export_group = "main"
            elif size[0] * 5 == size[1] * 4:
                export_group = "main_portrait"
            else:
                raise ValueError(f"MAIN slot {slot_id} requires a 1:1 or 4:5 target")
        else:
            export_group = {
                "APLUS_BASIC": "basic_aplus",
                "APLUS_PREMIUM_DESKTOP": "premium_aplus_desktop",
                "APLUS_PREMIUM_MOBILE": "premium_aplus_mobile",
            }[group]
            fixed = {"basic_aplus": [970, 600], "premium_aplus_desktop": [1464, 600],
                     "premium_aplus_mobile": [600, 450]}
            if size != fixed[export_group]:
                raise ValueError(f"{slot_id} {export_group} target must be {fixed[export_group]}")
        output = Path(slot["output_path"])
        raw = Path(slot["raw_output_path"])
        directory = SLOT_GROUP_DIRECTORIES[export_group]
        if output.parent.as_posix() != directory or output.suffix.lower() != ".png":
            raise ValueError(f"{slot_id}.output_path must be a .png directly under {directory}")
        if raw.parent.as_posix() != "raw_generated":
            raise ValueError(f"{slot_id}.raw_output_path must be directly under raw_generated")
        if raw.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError(f"{slot_id}.raw_output_path requires a supported image extension")
        slots.append({"slot_id": slot_id, "group": export_group, "raw_file": raw.name,
                      "output_file": output.name, "size": size})
    if sum(slot["group"] == "basic_aplus" for slot in slots) > 5:
        raise ValueError("stable Basic A+ supports at most 5 standalone images")
    return {"version": 1, "slots": slots}


def validate_plan(root: Path, plan: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["production_plan.json root must be an object"]
    if plan.get("version") != 1:
        errors.append("production_plan.json version must be 1")
    if not str(plan.get("run_identity", "")).strip():
        errors.append("production_plan.json run_identity is required")
    if plan.get("status") != "APPROVED":
        errors.append("production_plan.json status must be APPROVED")
    if str(plan.get("selected_style", "")).upper() not in {"A", "B", "C"}:
        errors.append("production_plan.json selected_style must be A, B, or C")
    project_root = root.expanduser().resolve()
    profile_path = project_root / "visual_preference_profile.json"
    if visual_preference_required(project_root) and not profile_path.is_file():
        errors.append(
            "visual_preference_profile.json is required before deriving production artifacts"
        )
    elif profile_path.is_file() and plan.get(
        "visual_preference_profile_sha256"
    ) != file_sha256(profile_path):
        errors.append(
            "production_plan.json visual_preference_profile_sha256 does not match "
            "the current visual_preference_profile.json"
        )
    slots = plan.get("slots")
    if not isinstance(slots, list) or not slots:
        errors.append("production_plan.json slots must be a non-empty list")
        return errors
    seen_slots: set[str] = set()
    seen_outputs: set[str] = set()
    for index, slot in enumerate(slots):
        prefix = f"slots[{index}]"
        if not isinstance(slot, dict):
            errors.append(f"{prefix} must be an object")
            continue
        slot_id = str(slot.get("slot_id", "")).strip()
        if not slot_id:
            errors.append(f"{prefix}.slot_id is required")
        elif slot_id in seen_slots:
            errors.append(f"duplicate slot_id: {slot_id}")
        seen_slots.add(slot_id)
        group = str(slot.get("group", "")).upper()
        if group not in VALID_GROUPS:
            errors.append(f"{prefix}.group is invalid: {group}")
        output_path = str(slot.get("output_path", "")).strip()
        if not output_path:
            errors.append(f"{prefix}.output_path is required")
        else:
            try:
                output_path = safe_relative_path(root, output_path)
            except ValueError as exc:
                errors.append(str(exc))
            if output_path in seen_outputs:
                errors.append(f"duplicate output_path: {output_path}")
            seen_outputs.add(output_path)
        raw_output_path = str(slot.get("raw_output_path", "")).strip()
        if not raw_output_path:
            errors.append(f"{prefix}.raw_output_path is required")
        else:
            try:
                raw_output_path = safe_relative_path(root, raw_output_path)
            except ValueError as exc:
                errors.append(str(exc))
            if (
                not raw_output_path
                or Path(raw_output_path).parts[0].lower() != "raw_generated"
            ):
                errors.append(
                    f"{prefix}.raw_output_path must be inside raw_generated"
                )
            if raw_output_path in seen_outputs:
                errors.append(f"duplicate output_path: {raw_output_path}")
            seen_outputs.add(raw_output_path)
        target_size = slot.get("target_size")
        if (
            not isinstance(target_size, list)
            or len(target_size) != 2
            or not all(isinstance(item, int) and item > 0 for item in target_size)
        ):
            errors.append(f"{prefix}.target_size must contain two positive integers")
        for field in ("module_task", "product_role", "product_exposure", "prompt"):
            if not str(slot.get(field, "")).strip():
                errors.append(f"{prefix}.{field} is required")
        reference_inputs = slot.get("reference_inputs", [])
        if not isinstance(reference_inputs, list):
            errors.append(f"{prefix}.reference_inputs must be a list")
        elif not all(
            isinstance(value, str) and value.strip() for value in reference_inputs
        ):
            errors.append(
                f"{prefix}.reference_inputs entries must be non-empty paths"
            )
        if not isinstance(slot.get("image_embedded_copy", []), list):
            errors.append(f"{prefix}.image_embedded_copy must be a list")
        if not isinstance(slot.get("independent"), bool):
            errors.append(f"{prefix}.independent must be true or false")
        if not isinstance(slot.get("parallel_gain"), bool):
            errors.append(f"{prefix}.parallel_gain must be true or false")
    state_path = Path(__file__).resolve().parent / "design_workflow_state.py"
    spec = importlib.util.spec_from_file_location("amazon_stable_plan_state", state_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load stable plan scope validator: {state_path}")
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    errors.extend(state.validate_scope_plan_counts(project_root, slots))
    if not errors:
        try:
            slot_manifest_for_plan(plan)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def packet_for_slot(root: Path, plan: dict[str, Any], slot: dict[str, Any]) -> dict[str, Any]:
    task_id = f"IMG-{slot['slot_id']}"
    reference_paths = [
        str(
            Path(value).expanduser().resolve()
            if Path(value).expanduser().is_absolute()
            else (root / Path(value).expanduser()).resolve()
        )
        for value in slot.get("reference_inputs", [])
    ]
    raw_output_path = (
        root / safe_relative_path(root, slot["raw_output_path"])
    ).resolve()
    return {
        "task_id": task_id,
        "slot_id": slot["slot_id"],
        "prompt": slot["prompt"].strip(),
        "referenced_image_paths": reference_paths,
        "output_path": str(raw_output_path),
    }


def derive_artifacts(
    root: Path, plan_path: Path, *, activate_registry: bool = False
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    plan_path = plan_path.expanduser().resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    errors = validate_plan(root, plan)
    if errors:
        raise ValueError("; ".join(errors))
    slot_manifest = slot_manifest_for_plan(plan)

    matrix_lines = [
        "# 完整出图版式规划矩阵",
        "",
        "> Canonical source: `production_plan.json`; do not edit this derived file by hand.",
        "",
        "| Slot | Group | Target | Module task | Product role | Exposure | Output |",
        "|---|---|---:|---|---|---|---|",
    ]
    prompt_lines = [
        "# Full Production Prompts",
        "",
        "> Canonical source: `production_plan.json`; regenerate after plan changes.",
        "",
    ]
    preflight_slots: list[dict[str, Any]] = []
    registry_tasks: list[dict[str, Any]] = []
    delegated: list[str] = []
    direct: list[str] = []

    for slot in plan["slots"]:
        width, height = slot["target_size"]
        matrix_lines.append(
            f"| {slot['slot_id']} | {slot['group']} | {width}x{height} | "
            f"{slot['module_task']} | {slot['product_role']} | {slot['product_exposure']} | "
            f"{slot['output_path']} |"
        )
        prompt_lines.extend(
            [
                f"## {slot['slot_id']}",
                "",
                f"- Output: `{slot['output_path']}`",
                f"- Target: `{width}x{height}`",
                f"- References: {', '.join(slot.get('reference_inputs', [])) or 'none (approved P0 only)' }",
                "",
                slot["prompt"].strip(),
                "",
            ]
        )
        preflight_slots.append(
            {
                "slot_id": slot["slot_id"],
                "output_path": slot["output_path"],
                "target_size": slot["target_size"],
                "expected_copy": slot.get("image_embedded_copy", []),
            }
        )
        task_id = f"IMG-{slot['slot_id']}"
        if slot.get("independent") is True and slot.get("parallel_gain") is True:
            delegated.append(task_id)
            packet = packet_for_slot(root, plan, slot)
            atomic_write_json(root / f"workers/packets/{task_id}.json", packet)
            registry_tasks.append(
                {
                    "task_id": task_id,
                    "role": "IMAGE_WORKER",
                    "slot_id": slot["slot_id"],
                    "stage": "IMAGE_GENERATION",
                    "depends_on": [],
                    "status": "PLANNED",
                    "estimated_seconds": slot["estimated_seconds"],
                    "independent": True,
                    "parallel_gain": True,
                    "allowed_write_paths": [packet["output_path"]],
                }
            )
        else:
            direct.append(task_id)

    for task in plan.get("supporting_tasks", []):
        task_id = str(task.get("task_id", "")).strip() or "UNNAMED-TASK"
        if should_delegate(task):
            delegated.append(task_id)
            role = str(task.get("role", "RESEARCH_WORKER")).strip() or "RESEARCH_WORKER"
            allowed_write_paths = task.get(
                "allowed_write_paths", [f"workers/outputs/{task_id}"]
            )
            if not isinstance(allowed_write_paths, list) or not allowed_write_paths:
                raise ValueError(f"supporting task {task_id} needs allowed_write_paths")
            packet = {
                "version": 1,
                "run_identity": plan["run_identity"],
                "task_id": task_id,
                "role": role,
                "stage": str(task.get("stage", "PRODUCTION_PLANNING")),
                "depends_on": task.get("depends_on", []),
                "objective": str(task.get("objective", task_id)),
                "read_only_inputs": task.get("read_only_inputs", ["production_plan.json"]),
                "fact_authority": task.get(
                    "fact_authority", ["production_plan.json", "01_product_truth.md"]
                ),
                "allowed_claims": task.get("allowed_claims", []),
                "forbidden_claims": task.get(
                    "forbidden_claims", ["unconfirmed product facts"]
                ),
                "allowed_write_paths": allowed_write_paths,
                "acceptance_checks": task.get(
                    "acceptance_checks", ["source-backed", "task-scoped"]
                ),
                "required_report_path": f"workers/reports/{task_id}.json",
            }
            atomic_write_json(root / f"workers/packets/{task_id}.json", packet)
            atomic_write_json(
                root / f"workers/report_templates/{task_id}.template.json",
                {
                    "task_id": task_id,
                    "status": "FILL_AFTER_EXECUTION",
                    "actual_output_paths": [],
                    "checks": [],
                },
            )
            registry_tasks.append(
                {
                    "task_id": task_id,
                    "role": role,
                    "stage": packet["stage"],
                    "depends_on": packet["depends_on"],
                    "status": "PLANNED",
                    "estimated_seconds": task["estimated_seconds"],
                    "independent": True,
                    "parallel_gain": True,
                    "allowed_write_paths": allowed_write_paths,
                    "required_report_path": packet["required_report_path"],
                }
            )
        else:
            direct.append(task_id)

    registry = {
        "version": 1,
        "run_identity": plan["run_identity"],
        "max_parallel_workers": HARD_MAX_CHILD_WORKERS,
        "tasks": registry_tasks,
    }
    atomic_write_text(root / "完整出图版式规划矩阵.md", "\n".join(matrix_lines) + "\n")
    atomic_write_text(root / "prompts/full_production_prompts.md", "\n".join(prompt_lines) + "\n")
    atomic_write_json(root / "preview/preflight_qc_spec.json", {"version": 1, "slots": preflight_slots})
    atomic_write_json(root / "slot_manifest.json", slot_manifest)
    atomic_write_json(root / "agent_task_registry.template.json", registry)
    if activate_registry and registry_tasks:
        atomic_write_json(root / "agent_task_registry.json", registry)
    return {
        "delegated_task_ids": delegated,
        "controller_direct_task_ids": direct,
        "registry_activated": bool(activate_registry and registry_tasks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive production artifacts from one canonical plan.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--plan", default="production_plan.json", type=Path)
    parser.add_argument("--activate-registry", action="store_true")
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    plan = args.plan if args.plan.is_absolute() else root / args.plan
    result = derive_artifacts(root, plan, activate_registry=args.activate_registry)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
