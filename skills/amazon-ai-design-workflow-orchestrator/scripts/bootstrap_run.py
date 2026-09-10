from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import struct
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "raw_generated", "preview", "workers"}
SOURCE_MARKERS = {"产品", "拍摄", "实拍", "photo", "source", "reference", "素材"}
WORKFLOW_VERSION = "1.0.0"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int | None, int | None, str | None]:
    try:
        header = path.read_bytes()[:32]
    except OSError as exc:
        return None, None, str(exc)
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        width, height = struct.unpack(">II", header[16:24])
        return width, height, None
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return int(width), int(height), None
    except Exception as exc:  # Pillow may be absent; inventory must still complete.
        return None, None, f"DIMENSIONS_UNAVAILABLE: {exc}"


def atomic_write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return path


def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def source_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        lowered = path.as_posix().lower()
        if any(marker in lowered for marker in SOURCE_MARKERS):
            candidates.append(path)
    return sorted(candidates)


def competitor_archives(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.zip")
        if path.is_file()
        and any(marker in path.as_posix().lower() for marker in ("竞品", "competitor"))
    )


def initialize_run(root: Path, run_identity: str, *, overwrite: bool = False) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    run_identity = run_identity.strip()
    if not run_identity:
        raise ValueError("run_identity is required")

    active_path = root / "active_run.json"
    if active_path.exists() and not overwrite:
        existing = json.loads(active_path.read_text(encoding="utf-8"))
        if existing.get("run_identity") != run_identity:
            raise FileExistsError(
                "active_run.json already belongs to another run; use --overwrite explicitly"
            )

    images: list[dict[str, Any]] = []
    for path in source_candidates(root):
        width, height, dimensions_error = image_dimensions(path)
        images.append(
            {
                "path": relative_path(root, path),
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
                "width": width,
                "height": height,
                "dimensions_error": dimensions_error,
            }
        )
    archives = [
        {
            "path": relative_path(root, path),
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in competitor_archives(root)
    ]
    now = datetime.now().isoformat(timespec="seconds")
    active_paths = sorted(
        {
            str(Path(item["path"]).parent.as_posix())
            for item in images + archives
            if Path(item["path"]).parent.as_posix() != "."
        }
    )
    active = {
        "version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "run_identity": run_identity,
        "created_at": now,
        "active_paths": active_paths,
        "include_root_files": True,
        "scoped": True,
    }
    source_inventory = {
        "version": 1,
        "run_identity": run_identity,
        "generated_at": now,
        "images": images,
    }
    zip_inventory = {
        "version": 1,
        "run_identity": run_identity,
        "generated_at": now,
        "archives": archives,
    }
    scope_template = {
        "_template": True,
        "_instruction": "Fill all requested counts once, then atomically promote to production_scope.json.",
        "main": {"enabled": None, "count": None, "count_by_ratio": {}, "ratios": []},
        "aplus": {"enabled": None, "type": None},
    }
    atomic_write_json(active_path, active)
    atomic_write_json(root / "source_inventory.json", source_inventory)
    atomic_write_json(root / "competitor_zip_inventory.json", zip_inventory)
    template_path = root / "production_scope.template.json"
    if overwrite or not template_path.exists():
        atomic_write_json(template_path, scope_template)
    return {
        "run_identity": run_identity,
        "source_count": len(images),
        "competitor_zip_count": len(archives),
        "active_paths": active_paths,
    }


def write_scope_atomic(root: Path, scope: dict[str, Any]) -> Path:
    if not isinstance(scope, dict):
        raise ValueError("production scope must be a JSON object")
    main = scope.get("main")
    aplus = scope.get("aplus")
    if not isinstance(main, dict) or not isinstance(aplus, dict):
        raise ValueError("production scope must define main and aplus objects")
    if not bool(main.get("enabled")) and not bool(aplus.get("enabled")):
        raise ValueError("at least one of main or aplus must be enabled")
    state_path = Path(__file__).resolve().parent / "design_workflow_state.py"
    spec = importlib.util.spec_from_file_location("amazon_stable_scope_state", state_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load stable scope validator: {state_path}")
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    # Validate a temporary candidate using the same contract as workflow state before promotion.
    with tempfile.TemporaryDirectory(prefix="amazon-stable-scope-") as tmp:
        candidate = atomic_write_json(Path(tmp) / "production_scope.json", scope)
        errors = state.validate_production_scope([candidate])["errors"]
    if errors:
        raise ValueError("; ".join(errors))
    return atomic_write_json(root.expanduser().resolve() / "production_scope.json", scope)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap one Amazon FULL_FLOW run.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--run-identity")
    parser.add_argument("--scope-json", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    if args.scope_json:
        scope = json.loads(args.scope_json.read_text(encoding="utf-8"))
        print(write_scope_atomic(root, scope))
        return 0
    if not args.run_identity:
        parser.error("--run-identity is required unless --scope-json is used")
    result = initialize_run(root, args.run_identity, overwrite=args.overwrite)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
