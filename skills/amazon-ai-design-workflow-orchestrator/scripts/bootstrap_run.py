from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import struct
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# Camera/phone formats the workflow cannot read; they are reported for conversion.
CONVERTIBLE_PHOTO_EXTENSIONS = {".heic", ".heif", ".avif", ".tif", ".tiff", ".dng"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "raw_generated", "preview", "workers"}
SOURCE_MARKERS = {
    "产品", "拍摄", "实拍", "实物", "原图", "素材",
    "photo", "source", "reference", "product", "img_", "dsc",
}
# Competitor evidence, design inspiration and workflow outputs are never product photos.
NON_SOURCE_MARKERS = {
    "竞品", "competitor", "大牌", "案例", "灵感", "inspiration",
    "输出", "output", "白底", "white_bg", "white-bg", "white-background", "white_background",
    "参考图库", "reference_library", "style_samples", "quick_samples", "小样",
    "main_1x1", "main_portrait", "a_plus",
}
COMPETITOR_MARKERS = ("竞品", "competitor")
RUN_OUTPUT_PARENT = "输出"
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


def project_files(root: Path, extensions: set[str]) -> list[Path]:
    """Files under the project, matched on their project-relative path only.

    Folder names above the project root (for example ~/亚马逊产品项目/) must never
    decide what a file is.
    """
    matches: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS or part.startswith(".") for part in relative_parts):
            continue
        matches.append(path)
    return sorted(matches)


def has_marker(root: Path, path: Path, markers: set[str] | tuple[str, ...]) -> bool:
    lowered = path.relative_to(root).as_posix().lower()
    return any(marker in lowered for marker in markers)


def source_candidates(root: Path) -> tuple[list[Path], str]:
    images = [
        path
        for path in project_files(root, IMAGE_EXTENSIONS)
        if not has_marker(root, path, NON_SOURCE_MARKERS)
    ]
    marked = [path for path in images if has_marker(root, path, SOURCE_MARKERS)]
    if marked:
        return marked, "MARKED_SOURCE_PATHS"
    if images:
        return images, "FALLBACK_ALL_PROJECT_IMAGES"
    return [], "NO_SUPPORTED_PHOTOS"


def convertible_photos(root: Path) -> list[Path]:
    return [
        path
        for path in project_files(root, CONVERTIBLE_PHOTO_EXTENSIONS)
        if not has_marker(root, path, NON_SOURCE_MARKERS)
    ]


def competitor_archives(root: Path) -> list[Path]:
    return [
        path
        for path in project_files(root, {".zip"})
        if has_marker(root, path, COMPETITOR_MARKERS)
    ]


def competitor_evidence_folders(root: Path) -> set[str]:
    """Folders of competitor screenshots/archives, registered so the scanner sees them."""
    return {
        relative_path(root, path.parent)
        for path in project_files(root, IMAGE_EXTENSIONS | {".zip", ".pdf"})
        if has_marker(root, path, COMPETITOR_MARKERS) and path.parent != root
    }


def run_output_folder(run_identity: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|\s]+', "-", run_identity).strip(".-") or "run"
    return f"{RUN_OUTPUT_PARENT}/{safe}"


def source_detection_warnings(source_detection: str, convertible: list[str]) -> list[str]:
    warnings: list[str] = []
    if source_detection == "FALLBACK_ALL_PROJECT_IMAGES":
        warnings.append(
            "No folder or file name marked the product photos, so every non-competitor "
            "image was inventoried. Confirm with the user which images are the real "
            "product photos before writing reference_strategy.json."
        )
    elif source_detection == "NO_SUPPORTED_PHOTOS":
        warnings.append(
            "No .jpg/.jpeg/.png/.webp product photos were found. Ask the user for the "
            "real product photo folder."
        )
    if convertible:
        warnings.append(
            f"{len(convertible)} photo(s) use a format this workflow cannot read "
            f"(for example {convertible[0]}). Convert them to JPEG first, e.g. on macOS: "
            "sips -s format jpeg <photo.heic> --out <photo.jpg>; then rerun bootstrap "
            "with the same run identity."
        )
    return warnings


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

    sources, source_detection = source_candidates(root)
    convertible = [relative_path(root, path) for path in convertible_photos(root)]
    warnings = source_detection_warnings(source_detection, convertible)
    images: list[dict[str, Any]] = []
    for path in sources:
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
    # Every generated artifact of this run lives under one registered folder, so the
    # state scanner sees new references, samples and outputs without old runs.
    run_output_root = run_output_folder(run_identity)
    (root / run_output_root).mkdir(parents=True, exist_ok=True)
    active_paths = sorted(
        {
            str(Path(item["path"]).parent.as_posix())
            for item in images + archives
            if Path(item["path"]).parent.as_posix() != "."
        }
        | competitor_evidence_folders(root)
        | {run_output_root}
    )
    active = {
        "version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "run_identity": run_identity,
        "created_at": now,
        "active_paths": active_paths,
        "run_output_root": run_output_root,
        "include_root_files": True,
        "scoped": True,
    }
    source_inventory = {
        "version": 1,
        "run_identity": run_identity,
        "generated_at": now,
        "source_detection": source_detection,
        "images": images,
        "convertible_photos": convertible,
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
        "source_detection": source_detection,
        "competitor_zip_count": len(archives),
        "active_paths": active_paths,
        "run_output_root": run_output_root,
        "warnings": warnings,
    }


def add_active_path(root: Path, folder: str) -> dict[str, Any]:
    """Register an existing project folder that holds current-run artifacts."""
    root = root.expanduser().resolve()
    active_path = root / "active_run.json"
    if not active_path.is_file():
        raise ValueError("active_run.json is missing; run bootstrap with --run-identity first")
    data = json.loads(active_path.read_text(encoding="utf-8"))
    target = (root / folder).resolve()
    try:
        value = target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"active path escapes project root: {folder}") from exc
    if value == ".":
        raise ValueError("register a subfolder, not the project root")
    if not target.is_dir():
        raise ValueError(f"active path is not an existing folder: {folder}")
    paths = [str(item) for item in data.get("active_paths", []) if str(item).strip()]
    if value not in paths:
        paths.append(value)
    data["active_paths"] = sorted(paths)
    atomic_write_json(active_path, data)
    return {"run_identity": data.get("run_identity"), "active_paths": data["active_paths"]}


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
    parser.add_argument(
        "--add-active-path",
        help="Register an existing project folder that holds current-run artifacts.",
    )
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    if args.add_active_path:
        print(json.dumps(add_active_path(root, args.add_active_path), ensure_ascii=False, indent=2))
        return 0
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
