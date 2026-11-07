from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TEXT_EXTENSIONS = {".md", ".txt", ".docx", ".xlsx", ".xls", ".csv", ".json"}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".cache",
}
GENERATED_PATH_MARKERS = [
    "raw_generated",
    "style_samples",
    "quick_samples",
    "white_bg_reference",
    "white-background",
    "preview",
    "main_1x1",
    "main_portrait",
    "a_plus_basic",
    "a_plus_premium",
]
WHITE_REFERENCE_MARKERS = [
    "white_bg_reference",
    "white-bg",
    "white_background",
    "white-background",
    "白底参考",
    "参考图库",
    "main-reference",
    "angle-reference",
    "structure-reference",
]
COMPETITOR_MARKERS = ["竞品", "competitor"]
# Workflow bookkeeping such as competitor_zip_inventory.json is not competitor evidence.
COMPETITOR_EVIDENCE_EXTENSIONS = IMAGE_EXTENSIONS | {".zip", ".pdf"}
OUT_OF_SCOPE_WHITE_REFERENCES = "out-of-scope white-background references"
DIAGNOSTIC_FOUND_KEYS = {"quick sample artifacts", OUT_OF_SCOPE_WHITE_REFERENCES}

STATE_VERSION = 14
SKILL_VERSION = "1.0.0"
VISUAL_PREFERENCE_REQUIRED_SINCE = (0, 6, 10)
TIMING_TOLERANCE_MS = 2_000
MAX_ELAPSED_MS = 7 * 24 * 60 * 60 * 1000
# BOUNDED_RATIO_EXPORT limit; must equal the runner's preflight_qc.py and
# postprocess_images.py so preflight reports and state validation agree.
MAX_ASPECT_CORRECTION_PCT = 1.0
RESIZABLE_DIMENSION_STATUSES = {"SAME_ASPECT_RESIZE_REQUIRED", "SMALL_RATIO_CORRECTION_CANDIDATE"}
FULL_FLOW_MODE = "FULL_FLOW"
AGENT_TASK_STATUSES = {
    "PLANNED",
    "DISPATCHED",
    "RUNNING",
    "REPORTED",
    "VERIFIED",
    "FAILED",
    "CANCELLED",
}
AGENT_TASK_PENDING_STATUSES = {"PLANNED", "DISPATCHED", "RUNNING", "REPORTED"}
AGENT_TASK_ROLES = {
    "RESEARCH_WORKER",
    "COPY_WORKER",
    "LAYOUT_WORKER",
    "PROMPT_WORKER",
    "IMAGE_WORKER",
    "QC_WORKER",
}
AGENT_REPORT_SUCCESS_STATUSES = {
    "PASS",
    "PASS_WITH_NOTES",
    "SUCCESS",
    "SUCCEEDED",
    "COMPLETED",
}
IMAGE2_FAILURE_ERROR_TYPES = {
    "AUTH",
    "NETWORK",
    "RATE_LIMIT",
    "TIMEOUT",
    "TRANSPORT",
    "OTHER",
}
QC_PROFILE_FILES = {
    "QC_PRODUCT_STRUCTURE": "qc_product_structure.json",
    "QC_COPY_STYLE": "qc_copy_style.json",
    "QC_TECHNICAL": "qc_technical.json",
}
QC_VERDICT_FILES = {
    "MAIN": "main_batch_qc_verdict.json",
    "APLUS": "aplus_batch_qc_verdict.json",
}
CAROUSEL_DEFERRED = "DEFERRED_TO_LAYOUT_MATRIX"
CAROUSEL_RESOLVED = "RESOLVED"
VISUAL_REFERENCE_CORE_SOURCES = {
    "ZCOOL",
    "ZHISHEJI",
    "DIGITALING",
    "BEHANCE",
    "FONTS_IN_USE",
    "ADS_OF_THE_WORLD",
    "GTN9",
    "WBDS",
}
VISUAL_REFERENCE_SUPPLEMENT_SOURCES = {"PENTAWARDS", "OTHER_TRACEABLE"}
VISUAL_REFERENCE_SOURCE_DOMAINS = {
    "ZCOOL": {"zcool.com.cn"},
    "ZHISHEJI": {"zhisheji.com"},
    "DIGITALING": {"digitaling.com"},
    "BEHANCE": {"behance.net"},
    "FONTS_IN_USE": {"fontsinuse.com"},
    "ADS_OF_THE_WORLD": {"adsoftheworld.com"},
    "GTN9": {"gtn9.com"},
    "WBDS": {"worldbranddesign.com"},
    "PENTAWARDS": {"pentawards.com"},
}
VISUAL_REFERENCE_FORBIDDEN_DOMAINS = {
    "awwwards.com",
    "dribbble.com",
    "huaban.com",
    "land-book.com",
    "mobbin.com",
    "pinterest.com",
    "siteinspire.com",
}
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "ref",
    "referrer",
    "source",
}
VISUAL_REFERENCE_ROLES = {
    "SELLING_LOGIC",
    "VISUAL_STYLE",
    "LAYOUT",
    "TYPOGRAPHY_ICON",
    "CONTRAST",
}
VISUAL_REFERENCE_TIERS = {
    "SAME_CATEGORY",
    "ADJACENT_PREMIUM",
    "EDITORIAL_BRAND",
    "CONTRAST",
}
VISUAL_REFERENCE_QUALITY_FLAGS = {
    "product_subject",
    "purchase_reason",
    "information_hierarchy",
    "amazon_transferability",
    "traceable_project",
}
MODULE_CARD_REQUIRED_SINCE = (0, 6, 11)
MODULE_CARD_EVIDENCE_ROLES = {
    "HERO",
    "SELLING_MODULE",
    "LAYOUT_SYSTEM",
    "TYPOGRAPHY_ICON",
    "FULL_PROJECT_OVERVIEW",
    "CAMPAIGN_VARIATION",
}
MODULE_CARD_REQUIRED_ROLES = {
    "HERO",
    "SELLING_MODULE",
    "LAYOUT_SYSTEM",
    "TYPOGRAPHY_ICON",
}
MIN_MODULE_WIDTH = 240
MIN_MODULE_HEIGHT = 160
MAX_MODULE_ASPECT_RATIO = 5.0
PERCEPTUAL_DUPLICATE_DISTANCE = 2.5
PAIRWISE_CONTROLS = {"same_product", "same_copy", "same_slot", "same_canvas"}
CANONICAL_STATE_FILE = "design_workflow_state.md"
CANONICAL_JSON_FILE = "design_workflow_state.json"
LEGACY_STATE_FILE = "设计流程状态.md"
ACTIVE_RUN_FILE = "active_run.json"

TRANSITION_TABLE = [
    ("INIT", "Project root and real product photos are known", "SCOPE_CONFIRMATION"),
    ("SCOPE_CONFIRMATION", "Valid production_scope.json exists", "REFERENCE_ASSESSMENT"),
    (
        "REFERENCE_ASSESSMENT",
        "reference_strategy.json selects DIRECT_SOURCE or MINIMAL_LIBRARY",
        "REFERENCE_FIDELITY_LOCK",
    ),
    (
        "REFERENCE_FIDELITY_LOCK",
        "reference_fidelity_lock.json binds structural locks to selected source hashes",
        "REFERENCE_LIBRARY_BUILD",
    ),
    (
        "REFERENCE_LIBRARY_BUILD",
        "At least three white-background reference images from photographed sources exist",
        "REFERENCE_QC",
    ),
    (
        "REFERENCE_QC",
        "Reference QC is PASS or PASS_WITH_NOTES",
        "REFERENCE_APPROVAL",
    ),
    ("REFERENCE_APPROVAL", "Manual approval exists", "PRODUCT_DETAIL_LOCKS"),
    (
        "PRODUCT_DETAIL_LOCKS",
        "01_product_truth.md and 03_product_detail_locks.md exist",
        "COMPETITOR_RESEARCH",
    ),
    ("COMPETITOR_RESEARCH", "Competitor display-logic brief exists", "PRODUCT_BRIEF"),
    ("PRODUCT_BRIEF", "Self-product selling-point brief exists", "PRODUCT_FACTS_GATE"),
    ("PRODUCT_FACTS_GATE", "Product facts confirmation passes", "BIG_BRAND_RESEARCH"),
    (
        "BIG_BRAND_RESEARCH",
        "Current big-brand case library exists",
        "VISUAL_PREFERENCE_CALIBRATION",
    ),
    (
        "VISUAL_PREFERENCE_CALIBRATION",
        "Reference pool and approved two-axis preference profile validate",
        "STYLE_RECOMMENDATION",
    ),
    ("STYLE_RECOMMENDATION", "Three Style Specs exist", "STYLE_SAMPLES"),
    (
        "STYLE_SAMPLES",
        "One representative sample exists for A, B, and C",
        "STYLE_CHOICE",
    ),
    ("STYLE_CHOICE", "User selects one style", "CONTEXT_PACK_PREP"),
    (
        "CONTEXT_PACK_PREP",
        "production_handoff.md and production_context_pack.md exist",
        "PRODUCTION_PLAN",
    ),
    ("PRODUCTION_PLAN", "Approved production_plan.json exists", "LAYOUT_MATRIX"),
    (
        "LAYOUT_MATRIX",
        "Full layout matrix exists and deferred Premium carousel assignment is resolved",
        "PROMPT_WRITING",
    ),
    ("PROMPT_WRITING", "Production prompts exist", "PROMPT_QC"),
    ("PROMPT_QC", "Prompt QC passes", "SCHEDULER_SETUP"),
    ("SCHEDULER_SETUP", "Phase-boundary scheduler authorizes up to three image workers", "IMAGE_GENERATION"),
    ("IMAGE_GENERATION", "Every planned raw production slot exists", "DETERMINISTIC_PREFLIGHT"),
    ("DETERMINISTIC_PREFLIGHT", "Cheap file, hash, dimension, ratio, and OCR checks finish", "IMAGE_QC"),
    ("IMAGE_QC", "Post-generation product, copy/style, and technical QC pass", "Continue failed-slot rework or FINAL_EXPORT"),
    ("FINAL_EXPORT", "preview/production_manifest.json exists", "COMPLETE"),
]

SLOT_RE = re.compile(r"^[A-Z]{1,5}\d{2}(?:S\d+)?$")


def has_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


# Keyword classification sees only the path inside the run output folder or the
# project, never folder names above it such as ~/亚马逊产品项目/ or a run identity.
_MATCH_ROOTS: tuple[Path, ...] = ()


def match_text(path: Path) -> str:
    for base in _MATCH_ROOTS:
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return str(path)


def normalize_active_path(root: Path, value: Any) -> tuple[str, Path | None, str | None]:
    root = root.expanduser().resolve()
    text = str(value).strip()
    if not text:
        return "", None, "active path is empty"

    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate.absolute()

    try:
        resolved.relative_to(root)
    except ValueError:
        return text, None, f"active path escapes project root: {text}"

    return text, resolved, None


def load_active_run(root: Path) -> dict[str, Any]:
    path = root / ACTIVE_RUN_FILE
    if not path.exists():
        return {
            "path": None,
            "run_identity": "legacy-unscoped",
            "active_paths": [],
            "include_root_files": True,
            "active_roots": [],
            "errors": [],
            "scoped": False,
            "workflow_version": None,
            "workflow_version_present": False,
            "run_output_root": None,
            "run_output_root_path": None,
            "created_at": None,
        }

    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        data = {}
        errors.append(f"invalid active_run.json: {exc}")

    if not isinstance(data, dict):
        data = {}
        errors.append("active_run.json root must be an object")

    run_identity = str(data.get("run_identity", "")).strip()
    if not run_identity:
        errors.append("active_run.json must define run_identity")
    workflow_version_present = "workflow_version" in data
    raw_workflow_version = data.get("workflow_version")
    workflow_version = None
    if workflow_version_present:
        if not isinstance(raw_workflow_version, str) or not raw_workflow_version.strip():
            errors.append("active_run.json workflow_version must be a non-empty string")
        else:
            workflow_version = raw_workflow_version.strip()
            if workflow_version_tuple(workflow_version) is None:
                errors.append(
                    "active_run.json workflow_version must use X.Y.Z or X.Y.Z-beta.N format"
                )

    include_root_files = bool(data.get("include_root_files", True))
    raw_active_paths = data.get("active_paths", [])
    if raw_active_paths is None:
        raw_active_paths = []
    if not isinstance(raw_active_paths, list):
        raw_active_paths = []
        errors.append("active_run.json active_paths must be a list")

    active_paths: list[str] = []
    active_roots: list[Path] = []
    for value in raw_active_paths:
        text, resolved, error = normalize_active_path(root, value)
        if text:
            active_paths.append(text)
        if error:
            errors.append(error)
            continue
        assert resolved is not None
        if not resolved.exists():
            errors.append(f"active path does not exist: {text}")
            continue
        active_roots.append(resolved)

    run_output_root: str | None = None
    run_output_root_path: Path | None = None
    if data.get("run_output_root") is not None:
        text, resolved, error = normalize_active_path(root, data.get("run_output_root"))
        run_output_root = text or None
        if error:
            errors.append(f"run_output_root: {error}")
        elif resolved is not None and resolved.is_dir():
            run_output_root_path = resolved

    return {
        "path": path,
        "run_identity": run_identity or "missing",
        "active_paths": active_paths,
        "include_root_files": include_root_files,
        "active_roots": active_roots,
        "errors": errors,
        "run_output_root": run_output_root,
        "run_output_root_path": run_output_root_path,
        "created_at": data.get("created_at"),
        "scoped": True,
        "workflow_version": workflow_version,
        "workflow_version_present": workflow_version_present,
    }


def workflow_version_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.\d+)?", value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def visual_preference_required(
    active_run: dict[str, Any], found: dict[str, list[Path]]
) -> bool:
    if present(found, "visual reference pool") or present(
        found, "visual preference profile"
    ):
        return True
    version_present = active_run.get("workflow_version_present")
    if version_present is None:
        version_present = active_run.get("workflow_version") is not None
    if not version_present:
        return False
    raw_version = active_run.get("workflow_version")
    version = workflow_version_tuple(raw_version)
    if version is None:
        return True
    return version >= VISUAL_PREFERENCE_REQUIRED_SINCE


def collect_paths(
    root: Path,
    active_run: dict[str, Any] | None = None,
    max_items: int = 8000,
) -> tuple[list[Path], list[Path]]:
    dirs: list[Path] = []
    files: list[Path] = []
    count = 0
    seen_dirs: set[Path] = set()
    seen_files: set[Path] = set()

    def add_dir(path: Path) -> bool:
        nonlocal count
        if path in seen_dirs:
            return count < max_items
        dirs.append(path)
        seen_dirs.add(path)
        count += 1
        return count < max_items

    def add_file(path: Path) -> bool:
        nonlocal count
        if path in seen_files:
            return count < max_items
        files.append(path)
        seen_files.add(path)
        count += 1
        return count < max_items

    def walk_scope(scope: Path) -> bool:
        if scope.is_file():
            return add_file(scope)
        if not scope.is_dir():
            return count < max_items
        if not add_dir(scope):
            return False
        for dirpath, dirnames, filenames in os.walk(scope):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in SKIP_DIRS and not name.startswith(".")
            ]
            current = Path(dirpath)
            if current != scope and not add_dir(current):
                return False
            for filename in filenames:
                if not add_file(current / filename):
                    return False
        return True

    if active_run and active_run.get("scoped"):
        if active_run.get("include_root_files", True):
            for child in root.iterdir():
                if child.is_file() and not child.name.startswith("."):
                    if not add_file(child):
                        return dirs, files
        for scope in active_run.get("active_roots", []):
            if not walk_scope(scope):
                return dirs, files
        return dirs, files

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        current = Path(dirpath)

        for dirname in dirnames:
            dirs.append(current / dirname)
            count += 1
            if count >= max_items:
                return dirs, files

        for filename in filenames:
            files.append(current / filename)
            count += 1
            if count >= max_items:
                return dirs, files

    return dirs, files


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def rel_list(root: Path, paths: list[Path], limit: int = 20) -> list[str]:
    values = [rel(root, path) for path in paths[:limit]]
    if len(paths) > limit:
        values.append(f"... plus {len(paths) - limit} more")
    return values


def is_generated_path(path: Path) -> bool:
    return has_any(match_text(path), GENERATED_PATH_MARKERS)


def is_quick_sample_path(path: Path) -> bool:
    return has_any(match_text(path), ["quick_samples", "quick sample", "快速样张"])


def find_product_photo_dirs(dirs: list[Path], files: list[Path]) -> list[Path]:
    dir_keywords = [
        "产品图",
        "实拍",
        "拍摄图",
        "产品照片",
        "product photo",
        "product_photo",
        "product image",
        "product_image",
        "source_photo",
        "source photos",
        "reference_input",
        "source_input",
        "image_input",
        "photo_input",
        "素材图",
        "源图",
        "实物",
        "原图",
    ]
    excluded = ["竞品", "competitor", *GENERATED_PATH_MARKERS]

    direct = [
        path
        for path in dirs
        if has_any(path.name, dir_keywords) and not has_any(match_text(path), excluded)
    ]

    image_parent_dirs: set[Path] = set()
    file_keywords = ["_source", "source_", "-source", "_input", "input_", "实拍", "拍摄", "img_", "dsc"]
    parent_keywords = ["source", "input", "photo", "image", "产品", "product", "实拍", "拍摄", "实物", "原图"]
    for path in files:
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if is_generated_path(path) or has_any(match_text(path), ["竞品", "competitor"]):
            continue
        if has_any(path.name, file_keywords) or has_any(path.parent.name, parent_keywords):
            image_parent_dirs.add(path.parent)

    return sorted(set(direct) | image_parent_dirs)


def text_files_named(files: list[Path], keywords: list[str]) -> list[Path]:
    return [
        path
        for path in files
        if path.suffix.lower() in TEXT_EXTENSIONS and has_any(match_text(path), keywords)
    ]


def image_files_named(files: list[Path], keywords: list[str]) -> list[Path]:
    return [
        path
        for path in files
        if path.suffix.lower() in IMAGE_EXTENSIONS and has_any(match_text(path), keywords)
    ]


def exact_files(files: list[Path], names: list[str]) -> list[Path]:
    lowered = {name.lower() for name in names}
    return [path for path in files if path.name.lower() in lowered]


def final_manifest_files(files: list[Path]) -> list[Path]:
    return exact_files(files, ["production_manifest.json"])


def partial_manifest_files(files: list[Path]) -> list[Path]:
    return exact_files(files, ["partial_production_manifest.json"])


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def report_status(paths: list[Path]) -> str:
    if not paths:
        return "MISSING"

    def sort_key(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    for path in sorted(paths, key=sort_key, reverse=True):
        text = read_text(path)
        upper = text.upper()
        if not upper.strip():
            continue
        declared = declared_status(text, allow_pass_with_notes=True)
        if declared is not None:
            return declared
        if re.search(r"\b(FAIL|FAILED|REJECT|REJECTED|REVISE|BLOCKED)\b", upper):
            return "FAIL"
        if "PASS_WITH_NOTES" in upper or "PASS WITH NOTES" in upper:
            return "PASS_WITH_NOTES"
        if re.search(r"\bPASS\b", upper):
            return "PASS"
    return "UNKNOWN"


def confirmation_status(paths: list[Path]) -> str:
    if not paths:
        return "MISSING"

    def sort_key(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    for path in sorted(paths, key=sort_key, reverse=True):
        text = read_text(path)
        upper = text.upper()
        if not upper.strip():
            continue

        declared = declared_status(text, allow_pass_with_notes=False)
        if declared is not None:
            return "PASS" if declared in {"PASS", "PASS_WITH_NOTES"} else declared

        if re.search(r"\b(FAIL|FAILED|REJECT|REJECTED|REVISE)\b", upper):
            return "FAIL"
        if re.search(r"\b(PASS|APPROVED|CONFIRMED|NO_BLOCKING_MISSING_FACTS)\b", upper):
            return "PASS"
    return "UNKNOWN"


def declared_status(text: str, *, allow_pass_with_notes: bool) -> str | None:
    match = re.search(r"(?im)^\s*STATUS\s*[:：]\s*(.+?)\s*$", text)
    if not match:
        return None

    value = match.group(1).strip().upper().replace(" ", "_")
    if value in {
        "FAIL",
        "FAILED",
        "REJECT",
        "REJECTED",
        "REVISE",
        "BLOCKED",
        "NOT_APPROVED",
        "UNAPPROVED",
        "REWORK_REQUIRED",
        "INCOMPLETE",
    }:
        return "FAIL"
    if allow_pass_with_notes and value == "PASS_WITH_NOTES":
        return "PASS_WITH_NOTES"
    if value in {"PASS", "APPROVED", "CONFIRMED", "NO_BLOCKING_MISSING_FACTS"}:
        return "PASS"
    return "UNKNOWN"


def load_json_file(paths: list[Path]) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    if not paths:
        return None, None, "file is missing"

    def sort_key(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    path = sorted(paths, key=sort_key, reverse=True)[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return path, None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return path, None, "JSON root must be an object"
    return path, data, None


def validate_production_scope(paths: list[Path]) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {"valid": False, "path": path, "errors": errors, "data": data}

    assert data is not None
    main = data.get("main")
    aplus = data.get("aplus")
    if not isinstance(main, dict):
        main = {"enabled": False}
    if not isinstance(aplus, dict):
        aplus = {"enabled": False}

    main_enabled = bool(main.get("enabled"))
    aplus_enabled = bool(aplus.get("enabled"))
    if not main_enabled and not aplus_enabled:
        errors.append("at least one of main.enabled or aplus.enabled must be true")

    if main_enabled:
        ratios = main.get("ratios")
        if not isinstance(ratios, list) or not ratios:
            errors.append("main.ratios must contain 1:1, 4:5, or both")
        else:
            allowed = {"1:1", "4:5"}
            normalized_ratios = [str(value) for value in ratios]
            invalid = [value for value in normalized_ratios if value not in allowed]
            if invalid:
                errors.append(f"unsupported main.ratios: {', '.join(invalid)}")
            if len(set(normalized_ratios)) != len(normalized_ratios):
                errors.append("main.ratios must not contain duplicates")

            selected_ratios = set(normalized_ratios) & allowed
            if selected_ratios == allowed:
                if "count" in main:
                    errors.append("main.count is ambiguous for dual ratios; use count_by_ratio")
                count_by_ratio = main.get("count_by_ratio")
                if not isinstance(count_by_ratio, dict):
                    errors.append(
                        "main.count_by_ratio must define positive counts for 1:1 and 4:5 "
                        "when both ratios are requested"
                    )
                else:
                    for ratio in sorted(allowed):
                        count = count_by_ratio.get(ratio)
                        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                            errors.append(
                                f"main.count_by_ratio.{ratio} must be a positive integer"
                            )
                    extra = sorted(set(str(key) for key in count_by_ratio) - allowed)
                    if extra:
                        errors.append(
                            f"unsupported main.count_by_ratio keys: {', '.join(extra)}"
                        )
            elif len(selected_ratios) == 1:
                count = main.get("count")
                if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                    errors.append(
                        "main.count must be a positive integer when one ratio is requested"
                    )

    if aplus_enabled:
        aplus_type = str(aplus.get("type", "")).strip().lower()
        if aplus_type not in {"basic", "premium"}:
            errors.append("aplus.type must be Basic or Premium")

        if "count" in aplus:
            errors.append(
                "aplus.count is ambiguous; use aplus.image_count for Basic or "
                "aplus.module_count / aplus.desktop_image_count / aplus.mobile_image_count for Premium"
            )

        if aplus_type == "basic":
            image_count = aplus.get("image_count")
            if not isinstance(image_count, int) or image_count <= 0:
                errors.append("aplus.image_count must be a positive integer for Basic A+")
            elif image_count > 5:
                errors.append("Basic A+ supports at most 5 standalone images (Amazon's Basic A+ module limit)")

        if aplus_type == "premium":
            module_count = aplus.get("module_count")
            desktop_image_count = aplus.get("desktop_image_count")
            mobile_image_count = aplus.get("mobile_image_count", 0)
            carousel_status = str(
                aplus.get("carousel_assignment_status", "")
            ).strip().upper()
            if not isinstance(module_count, int) or module_count <= 0:
                errors.append("aplus.module_count must be a positive integer for Premium A+")
            elif module_count > 7:
                errors.append("Premium A+ supports at most 7 modules")
            if not isinstance(desktop_image_count, int) or desktop_image_count <= 0:
                errors.append("aplus.desktop_image_count must be a positive integer for Premium A+")
            if not isinstance(mobile_image_count, int) or mobile_image_count < 0:
                errors.append("aplus.mobile_image_count must be a non-negative integer for Premium A+")
            if carousel_status and carousel_status not in {
                CAROUSEL_DEFERRED,
                CAROUSEL_RESOLVED,
            }:
                errors.append(
                    "aplus.carousel_assignment_status must be "
                    "DEFERRED_TO_LAYOUT_MATRIX or RESOLVED"
                )

            if carousel_status == CAROUSEL_DEFERRED:
                deferred_modules = aplus.get("carousel_modules", [])
                if deferred_modules not in (None, []):
                    errors.append(
                        "deferred Premium A+ scope must omit carousel_modules "
                        "until the layout matrix"
                    )
                if (
                    isinstance(module_count, int)
                    and module_count > 0
                    and isinstance(desktop_image_count, int)
                    and desktop_image_count > 0
                ):
                    if desktop_image_count < module_count:
                        errors.append(
                            "deferred Premium A+ desktop_image_count must be "
                            "at least module_count"
                        )
                    elif desktop_image_count > module_count * 5:
                        errors.append(
                            "deferred Premium A+ desktop_image_count exceeds "
                            "five slides per module"
                        )
                if (
                    isinstance(mobile_image_count, int)
                    and isinstance(desktop_image_count, int)
                    and mobile_image_count not in {0, desktop_image_count}
                ):
                    errors.append(
                        "deferred Premium A+ mobile_image_count must be 0 or "
                        "equal desktop_image_count"
                    )
            else:
                if carousel_status == CAROUSEL_RESOLVED and "carousel_modules" not in aplus:
                    errors.append(
                        "resolved Premium A+ scope must include carousel_modules"
                    )
                value = aplus.get("carousel_modules", [])
                if not isinstance(value, list):
                    errors.append("aplus.carousel_modules must be a list")
                elif isinstance(module_count, int):
                    seen_module_ids: set[int] = set()
                    valid_carousels: list[tuple[int, int]] = []
                    for index, module in enumerate(value, start=1):
                        if not isinstance(module, dict):
                            errors.append(f"aplus.carousel_modules[{index}] must be an object")
                            continue
                        module_id = module.get("module_id")
                        slides = module.get("slides")
                        if not isinstance(module_id, int) or module_id < 1 or module_id > module_count:
                            errors.append(f"aplus.carousel_modules[{index}].module_id must be 1..module_count")
                        elif module_id in seen_module_ids:
                            errors.append(
                                f"aplus.carousel_modules[{index}].module_id is duplicate: {module_id}"
                            )
                        else:
                            seen_module_ids.add(module_id)
                        if not isinstance(slides, int) or slides < 1 or slides > 5:
                            errors.append(f"aplus.carousel_modules[{index}].slides must be 1..5")
                        elif isinstance(module_id, int) and 1 <= module_id <= module_count:
                            valid_carousels.append((module_id, slides))

                    if len(valid_carousels) == len(value):
                        expected_images = module_count + sum(
                            slides - 1 for _, slides in valid_carousels
                        )
                        if (
                            isinstance(desktop_image_count, int)
                            and desktop_image_count > 0
                            and desktop_image_count != expected_images
                        ):
                            errors.append(
                                "aplus.desktop_image_count must equal module_count plus extra carousel slides "
                                f"({expected_images} expected)"
                            )
                        if (
                            isinstance(mobile_image_count, int)
                            and mobile_image_count > 0
                            and mobile_image_count != expected_images
                        ):
                            errors.append(
                                "aplus.mobile_image_count must be 0 or match the requested desktop/carousel "
                                f"asset count ({expected_images} expected)"
                            )

    return {"valid": not errors, "path": path, "errors": errors, "data": data}


def premium_carousel_assignment_is_deferred(scope: dict[str, Any]) -> bool:
    data = scope.get("data")
    if not isinstance(data, dict):
        return False
    aplus = data.get("aplus")
    if not isinstance(aplus, dict):
        return False
    return (
        bool(aplus.get("enabled"))
        and str(aplus.get("type", "")).strip().lower() == "premium"
        and str(aplus.get("carousel_assignment_status", "")).strip().upper()
        == CAROUSEL_DEFERRED
    )


def resolve_strategy_source(strategy_path: Path, source: str) -> Path:
    candidate = Path(source).expanduser()
    if not candidate.is_absolute():
        candidate = strategy_path.parent / candidate
    return candidate.resolve()


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


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        dimensions = verified_png_dimensions(data)
        return dimensions if dimensions is not None else (None, None)
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


def finite_elapsed_ms(value: Any, *, require_positive: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if (
        not math.isfinite(numeric)
        or numeric < 0
        or (require_positive and numeric == 0)
        or numeric > MAX_ELAPSED_MS
    ):
        return None
    return numeric


def validate_reference_strategy(paths: list[Path]) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {
            "valid": False,
            "path": path,
            "errors": errors,
            "strategy": None,
            "data": data,
        }

    assert data is not None
    strategy = str(data.get("strategy", "")).strip().upper()
    if strategy not in {"DIRECT_SOURCE", "MINIMAL_LIBRARY"}:
        errors.append("strategy must be DIRECT_SOURCE or MINIMAL_LIBRARY")
    selected_sources = data.get("selected_sources")
    if not isinstance(selected_sources, list) or not selected_sources:
        errors.append("selected_sources must contain at least one real product photo")
    elif path is not None:
        source_hashes = data.get("source_hashes", {})
        if source_hashes is None:
            source_hashes = {}
        if not isinstance(source_hashes, dict):
            errors.append("source_hashes must be an object when provided")
            source_hashes = {}

        project_root = path.parent.resolve()
        seen_sources: set[str] = set()
        for index, source in enumerate(selected_sources, start=1):
            if not isinstance(source, str) or not source.strip():
                errors.append(f"selected_sources[{index}] must be a non-empty string path")
                continue

            source_key = source.strip()
            resolved = resolve_strategy_source(path, source_key)
            try:
                resolved.relative_to(project_root)
            except ValueError:
                errors.append(f"selected_sources[{index}] escapes project root: {source_key}")
                continue

            resolved_key = str(resolved)
            if resolved_key in seen_sources:
                errors.append(f"selected_sources[{index}] duplicates another selected source")
                continue
            seen_sources.add(resolved_key)

            if not resolved.exists():
                errors.append(f"selected_sources[{index}] does not exist: {source_key}")
                continue
            if not resolved.is_file():
                errors.append(f"selected_sources[{index}] is not a file: {source_key}")
                continue
            if resolved.suffix.lower() not in IMAGE_EXTENSIONS:
                errors.append(
                    f"selected_sources[{index}] must be an image file"
                    f" ({', '.join(sorted(IMAGE_EXTENSIONS))}): {source_key}"
                )
                continue

            expected_hash = source_hashes.get(source_key) or source_hashes.get(resolved_key)
            if expected_hash is not None:
                expected_hash = str(expected_hash).strip().lower()
                actual_hash = file_sha256(resolved)
                if expected_hash != actual_hash:
                    errors.append(f"selected_sources[{index}] hash mismatch: {source_key}")

    return {
        "valid": not errors,
        "path": path,
        "errors": errors,
        "strategy": strategy or None,
        "data": data,
    }


def validate_reference_fidelity_lock(
    paths: list[Path],
    root: Path,
    run_identity: str,
    reference_strategy: dict[str, Any],
) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {"valid": False, "path": path, "errors": errors, "data": data}

    assert data is not None
    if data.get("version") != 1:
        errors.append("reference_fidelity_lock.json version must be 1")
    lock_run_identity = str(data.get("run_identity", "")).strip()
    if lock_run_identity != run_identity:
        errors.append("reference_fidelity_lock.json run_identity does not match active_run.json")
    selected_sources = data.get("selected_sources")
    strategy_data = reference_strategy.get("data")
    strategy_sources = (
        strategy_data.get("selected_sources", [])
        if isinstance(strategy_data, dict)
        else []
    )
    if selected_sources != strategy_sources:
        errors.append("reference_fidelity_lock.json selected_sources must exactly match reference_strategy.json")
    locks = data.get("locks")
    if not isinstance(locks, list) or not locks:
        errors.append("reference_fidelity_lock.json locks must contain at least one structural lock")
        locks = []
    allowed_sources = {str(item) for item in strategy_sources}
    covered_sources: set[str] = set()
    for index, lock in enumerate(locks):
        prefix = f"reference_fidelity_lock.json locks[{index}]"
        if not isinstance(lock, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("feature", "source_path", "source_sha256", "must_preserve", "forbidden_drift"):
            if not str(lock.get(field, "")).strip():
                errors.append(f"{prefix}.{field} is required")
        source_value = str(lock.get("source_path", "")).strip()
        if source_value and source_value not in allowed_sources:
            errors.append(f"{prefix}.source_path is not selected by reference_strategy.json")
            continue
        if source_value:
            covered_sources.add(source_value)
            source = (root / source_value).resolve()
            try:
                source.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{prefix}.source_path escapes project root")
                continue
            if not source.is_file():
                errors.append(f"{prefix}.source_path does not exist")
            elif str(lock.get("source_sha256", "")).lower() != file_sha256(source):
                errors.append(f"{prefix}.source_sha256 hash mismatch")
    missing_coverage = sorted(allowed_sources - covered_sources)
    if missing_coverage:
        errors.append(
            "reference_fidelity_lock.json coverage is missing selected source(s): "
            + ", ".join(missing_coverage)
        )
    return {"valid": not errors, "path": path, "errors": errors, "data": data}


def nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def hostname_matches(hostname: str, allowed_domains: set[str]) -> bool:
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in allowed_domains
    )


def canonical_project_url(value: str) -> tuple[str | None, str | None, str | None]:
    try:
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
    except ValueError as exc:
        return None, None, f"invalid project URL: {exc}"
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None, hostname or None, "project URL must use http(s) and include a hostname"
    path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/") or "/"
    query_items = []
    for key, item_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, item_value))
    query = urlencode(sorted(query_items))
    canonical = f"https://{hostname}{path}"
    if query:
        canonical += f"?{query}"
    return canonical, hostname, None


def module_card_contract_required(
    pool_data: dict[str, Any], workflow_version: Any = None
) -> bool:
    """Require module cards for new runs and any not-yet-rated pool.

    Completed 0.6.10 preference bundles remain readable. An unrated legacy pool
    must migrate before it is shown to the user, which prevents the failed
    single-thumbnail interaction from being completed and approved later.
    """
    version = workflow_version_tuple(workflow_version)
    if version is not None and version >= MODULE_CARD_REQUIRED_SINCE:
        return True
    if pool_data.get("rater_contract_version") is not None:
        return True
    return str(pool_data.get("status", "")).strip().upper() != "RATED"


def validate_module_reference_cards(
    pool_data: dict[str, Any],
    validation_root: Path,
    *,
    required: bool,
) -> list[str]:
    """Validate the hash-bound multi-module evidence shown on rating cards."""
    if not required:
        return []

    errors: list[str] = []
    if pool_data.get("rater_contract_version") != 1:
        errors.append(
            "visual_reference_pool.json rater_contract_version must be 1 for module scoring cards"
        )
    samples = pool_data.get("samples")
    if not isinstance(samples, list):
        return errors
    if str(pool_data.get("status", "")).strip().upper() == "RATED":
        submission = pool_data.get("rating_submission")
        if not isinstance(submission, dict):
            errors.append(
                "visual_reference_pool.json rating_submission must record the module rater payload"
            )
        else:
            if submission.get("rater_contract_version") != 1:
                errors.append(
                    "visual_reference_pool.json rating_submission.rater_contract_version must be 1"
                )
            if (
                str(submission.get("interaction_mode", "")).strip().upper()
                != "MODULE_CARD_BUTTONS"
            ):
                errors.append(
                    "visual_reference_pool.json rating_submission.interaction_mode must be MODULE_CARD_BUTTONS"
                )
            submission_pool_hash = submission.get("reference_pool_sha256")
            if not isinstance(submission_pool_hash, str) or not re.fullmatch(
                r"[0-9a-f]{64}", submission_pool_hash.strip().lower()
            ):
                errors.append(
                    "visual_reference_pool.json rating_submission.reference_pool_sha256 must be a SHA-256 hash"
                )
            expected_sample_ids = [
                str(sample.get("id", "")).strip()
                for sample in samples
                if isinstance(sample, dict)
            ]
            if submission.get("sample_ids") != expected_sample_ids:
                errors.append(
                    "visual_reference_pool.json rating_submission.sample_ids must match the rated cards in order"
                )
            if any(
                not isinstance(sample, dict)
                or isinstance(sample.get(axis), bool)
                or sample.get(axis) not in {-1, 0, 1}
                for sample in samples
                for axis in ("visual", "layout")
            ):
                errors.append(
                    "visual_reference_pool.json module rater submission must score both axes for every card"
                )

    root = validation_root.expanduser().resolve()
    global_paths: set[str] = set()
    global_hashes: set[str] = set()
    for sample_index, sample in enumerate(samples):
        prefix = f"visual_reference_pool.json samples[{sample_index}]"
        if not isinstance(sample, dict):
            continue
        card_project_url = str(sample.get("project_url", "")).strip()
        card_canonical_url, _, card_url_error = canonical_project_url(card_project_url)
        if card_url_error:
            errors.append(f"{prefix}.project_url {card_url_error}")
        module_card = sample.get("module_card")
        if not isinstance(module_card, dict):
            errors.append(f"{prefix}.module_card must be an object")
            continue
        if str(module_card.get("mode", "")).strip().upper() != "MODULE_COLLAGE":
            errors.append(f"{prefix}.module_card.mode must be MODULE_COLLAGE")
        evidence = module_card.get("evidence")
        if not isinstance(evidence, list) or not 4 <= len(evidence) <= 6:
            errors.append(
                f"{prefix}.module_card requires 4-6 unique module evidence images"
            )
            continue

        card_paths: set[str] = set()
        card_hashes: set[str] = set()
        covered_roles: set[str] = set()
        for evidence_index, item in enumerate(evidence):
            item_prefix = f"{prefix}.module_card.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_prefix} must be an object")
                continue
            role = str(item.get("module_role", "")).strip().upper()
            if role not in MODULE_CARD_EVIDENCE_ROLES:
                errors.append(f"{item_prefix}.module_role is invalid")
            else:
                covered_roles.add(role)

            source_project_url = item.get("source_project_url")
            if not isinstance(source_project_url, str) or not source_project_url.strip():
                errors.append(f"{item_prefix}.source_project_url is required")
            else:
                evidence_canonical_url, _, evidence_url_error = canonical_project_url(
                    source_project_url.strip()
                )
                if evidence_url_error:
                    errors.append(
                        f"{item_prefix}.source_project_url {evidence_url_error}"
                    )
                elif (
                    card_canonical_url is None
                    or evidence_canonical_url != card_canonical_url
                ):
                    errors.append(
                        f"{item_prefix}.source_project_url must match the card project_url"
                    )

            path_value = item.get("path")
            path_text = path_value.strip() if isinstance(path_value, str) else ""
            if not path_text:
                errors.append(f"{item_prefix}.path is required")
                continue
            try:
                image_path = (root / path_text).resolve()
                relative_path = image_path.relative_to(root).as_posix()
            except (OSError, RuntimeError, ValueError):
                errors.append(f"{item_prefix}.path escapes project root or is invalid")
                continue
            if relative_path in card_paths:
                errors.append(f"{item_prefix}.path duplicates another panel in this card")
            card_paths.add(relative_path)
            if relative_path in global_paths:
                errors.append(f"{item_prefix}.path is reused by another rating card")
            global_paths.add(relative_path)
            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                errors.append(f"{item_prefix}.path must be a supported image")
                continue
            if not image_path.is_file():
                errors.append(f"{item_prefix}.path does not exist")
                continue

            expected_hash = item.get("sha256")
            normalized_hash = (
                expected_hash.strip().lower() if isinstance(expected_hash, str) else ""
            )
            if not re.fullmatch(r"[0-9a-f]{64}", normalized_hash):
                errors.append(f"{item_prefix}.sha256 must be a SHA-256 hash")
                continue
            actual_hash = file_sha256(image_path)
            if normalized_hash != actual_hash:
                errors.append(f"{item_prefix}.sha256 hash mismatch")
            if normalized_hash in card_hashes:
                errors.append(f"{item_prefix}.sha256 duplicates another panel in this card")
            card_hashes.add(normalized_hash)
            if normalized_hash in global_hashes:
                errors.append(f"{item_prefix}.sha256 is reused by another rating card")
            global_hashes.add(normalized_hash)

        missing_roles = sorted(MODULE_CARD_REQUIRED_ROLES - covered_roles)
        if missing_roles:
            errors.append(
                f"{prefix}.module_card is missing required module roles: "
                + ", ".join(missing_roles)
            )
    return errors


def visual_module_fingerprint(
    image_path: Path,
) -> tuple[int, int, tuple[int, ...]] | None:
    try:
        from PIL import Image, ImageOps
    except ModuleNotFoundError:
        return None
    try:
        with Image.open(image_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            width, height = image.size
            reduced = image.resize((32, 20), Image.Resampling.LANCZOS)
            pixel_data = (
                reduced.get_flattened_data()
                if hasattr(reduced, "get_flattened_data")
                else reduced.getdata()
            )
            pixels = tuple(channel for pixel in pixel_data for channel in pixel)
    except (OSError, ValueError):
        return None
    return width, height, pixels


def visual_fingerprint_distance(
    left: tuple[int, ...], right: tuple[int, ...]
) -> float:
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(left)


def validate_visual_module_evidence(
    pool_data: dict[str, Any], validation_root: Path, *, required: bool
) -> list[str]:
    """Reject unreadable thumbnails and perceptual duplicates in every entry path."""
    if not required:
        return []
    errors: list[str] = []
    samples = pool_data.get("samples")
    if not isinstance(samples, list):
        return errors
    resolved_root = validation_root.expanduser().resolve()
    for sample_index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            continue
        module_card = sample.get("module_card")
        evidence = module_card.get("evidence") if isinstance(module_card, dict) else None
        if not isinstance(evidence, list):
            continue
        fingerprints: list[tuple[int, tuple[int, ...]]] = []
        for evidence_index, item in enumerate(evidence):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            prefix = (
                f"visual_reference_pool.json samples[{sample_index}].module_card."
                f"evidence[{evidence_index}]"
            )
            image_path = (resolved_root / item["path"]).resolve()
            try:
                image_path.relative_to(resolved_root)
            except ValueError:
                continue
            if not image_path.is_file():
                continue
            fingerprint_data = visual_module_fingerprint(image_path)
            if fingerprint_data is None:
                errors.append(
                    f"{prefix}.path cannot be visually decoded; use the bundled Pillow runtime"
                )
                continue
            width, height, fingerprint = fingerprint_data
            if width < MIN_MODULE_WIDTH or height < MIN_MODULE_HEIGHT:
                errors.append(
                    f"{prefix}.path is too small for rating; minimum is "
                    f"{MIN_MODULE_WIDTH}x{MIN_MODULE_HEIGHT}"
                )
            aspect = max(width / height, height / width)
            if aspect > MAX_MODULE_ASPECT_RATIO:
                errors.append(f"{prefix}.path is too narrow to remain readable in the card")
            for previous_index, previous in fingerprints:
                if (
                    visual_fingerprint_distance(previous, fingerprint)
                    <= PERCEPTUAL_DUPLICATE_DISTANCE
                ):
                    errors.append(
                        f"{prefix}.path perceptually duplicates evidence[{previous_index}]"
                    )
                    break
            fingerprints.append((evidence_index, fingerprint))
    return errors


def validate_rating_submission_snapshot(
    pool_path: Path | None, pool_data: dict[str, Any], *, required: bool
) -> list[str]:
    """Bind a RATED result to the exact PENDING_RATING pool used by the rater."""
    if (
        not required
        or str(pool_data.get("status", "")).strip().upper() != "RATED"
        or pool_path is None
    ):
        return []
    errors: list[str] = []
    submission = pool_data.get("rating_submission")
    if not isinstance(submission, dict):
        return errors
    snapshot_path = pool_path.with_name("visual_reference_pool.pending.json")
    if not snapshot_path.is_file():
        return [
            "visual_reference_pool.pending.json is required to verify rating_submission"
        ]
    expected_hash = str(submission.get("reference_pool_sha256", "")).strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        if file_sha256(snapshot_path) != expected_hash:
            errors.append(
                "rating_submission.reference_pool_sha256 does not match visual_reference_pool.pending.json"
            )
    try:
        snapshot_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"visual_reference_pool.pending.json cannot be read: {exc}")
        return errors
    if not isinstance(snapshot_data, dict):
        return errors + ["visual_reference_pool.pending.json must be an object"]
    expected_pending = json.loads(json.dumps(pool_data))
    expected_pending["status"] = "PENDING_RATING"
    expected_pending.pop("rating_submission", None)
    pending_samples = expected_pending.get("samples")
    if isinstance(pending_samples, list):
        for sample in pending_samples:
            if isinstance(sample, dict):
                sample["visual"] = None
                sample["layout"] = None
    if snapshot_data != expected_pending:
        errors.append(
            "visual_reference_pool.pending.json must match the rated pool before ratings were applied"
        )
    return errors


def validate_pairwise_control_values(
    control_values: Any, validation_root: Path
) -> tuple[dict[str, Any], list[str]]:
    """Validate the frozen inputs required before pairwise image generation."""
    errors: list[str] = []
    context: dict[str, Any] = {
        "controls_hash": None,
        "product_path": None,
        "product_relative": None,
        "product_hash": "",
        "slot_id": "",
        "target_size": None,
    }
    prefix = "visual_preference_profile.json pairwise_round.control_values"
    if not isinstance(control_values, dict):
        return context, [f"{prefix} must be an object"]

    product_hash = control_values.get("product_reference_sha256")
    copy_hash = control_values.get("copy_sha256")
    for hash_field, hash_value in (
        ("product_reference_sha256", product_hash),
        ("copy_sha256", copy_hash),
    ):
        if not isinstance(hash_value, str) or not re.fullmatch(
            r"[0-9a-f]{64}", hash_value.strip().lower()
        ):
            errors.append(f"{prefix}.{hash_field} must be a SHA-256 hash")
    controlled_product_hash = (
        product_hash.strip().lower() if isinstance(product_hash, str) else ""
    )
    context["product_hash"] = controlled_product_hash

    product_reference_value = control_values.get("product_reference_path")
    if not isinstance(product_reference_value, str) or not product_reference_value.strip():
        errors.append(f"{prefix}.product_reference_path is required")
    else:
        product_reference_text = product_reference_value.strip()
        try:
            controlled_product_path = (
                validation_root / product_reference_text
            ).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{prefix}.product_reference_path is invalid: {exc}")
        else:
            try:
                controlled_product_relative = controlled_product_path.relative_to(
                    validation_root
                ).as_posix()
            except ValueError:
                errors.append(f"{prefix}.product_reference_path escapes project root")
            else:
                context["product_path"] = controlled_product_path
                context["product_relative"] = controlled_product_relative
                try:
                    product_exists = controlled_product_path.is_file()
                except OSError as exc:
                    errors.append(
                        f"{prefix}.product_reference_path cannot be inspected: {exc}"
                    )
                    product_exists = False
                if not product_exists:
                    errors.append(f"{prefix}.product_reference_path is missing")
                elif re.fullmatch(r"[0-9a-f]{64}", controlled_product_hash):
                    try:
                        actual_product_hash = file_sha256(controlled_product_path)
                    except OSError as exc:
                        errors.append(
                            f"{prefix}.product_reference_path cannot be hashed: {exc}"
                        )
                    else:
                        if actual_product_hash != controlled_product_hash:
                            errors.append(
                                f"{prefix}.product_reference_sha256 hash mismatch"
                            )

    copy_text = control_values.get("copy_text")
    if not isinstance(copy_text, str) or not copy_text.strip():
        errors.append(f"{prefix}.copy_text must be a non-empty string")
    else:
        try:
            copy_bytes = copy_text.encode("utf-8")
        except UnicodeEncodeError:
            errors.append(f"{prefix}.copy_text must be valid UTF-8 text")
        else:
            if (
                isinstance(copy_hash, str)
                and re.fullmatch(r"[0-9a-f]{64}", copy_hash.strip().lower())
                and hashlib.sha256(copy_bytes).hexdigest()
                != copy_hash.strip().lower()
            ):
                errors.append(f"{prefix}.copy_sha256 hash mismatch")

    slot_value = control_values.get("slot_id")
    if not isinstance(slot_value, str) or not slot_value.strip():
        errors.append(f"{prefix}.slot_id is required")
    else:
        context["slot_id"] = slot_value.strip()

    target_size = control_values.get("target_size")
    if (
        not isinstance(target_size, list)
        or len(target_size) != 2
        or not all(
            isinstance(value, int) and not isinstance(value, bool) and value > 0
            for value in target_size
        )
    ):
        errors.append(f"{prefix}.target_size must contain two positive integers")
    else:
        context["target_size"] = (target_size[0], target_size[1])

    try:
        context["controls_hash"] = hashlib.sha256(
            json.dumps(
                control_values,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    except (TypeError, ValueError):
        errors.append(f"{prefix} must be JSON-serializable")

    return context, errors


def validate_visual_preference_bundle(
    reference_pool_paths: list[Path],
    preference_profile_paths: list[Path],
    run_identity: str,
    root: Path | None = None,
    generation_ledger_paths: list[Path] | None = None,
    workflow_version: Any = None,
) -> dict[str, Any]:
    errors: list[str] = []
    pool_path, pool_data, pool_load_error = load_json_file(reference_pool_paths)
    if workflow_version in {SKILL_VERSION, "0.7.0", "0.7.0-beta.3"} or (
        isinstance(pool_data, dict) and pool_data.get("version") == 2
    ):
        helper_path = Path(__file__).resolve().parent / "reference_discovery.py"
        if helper_path.is_file():
            spec = importlib.util.spec_from_file_location(
                "amazon_stable_reference_discovery", helper_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load stable discovery helper: {helper_path}")
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            result = helper.validate_bundle(
                reference_pool_paths, preference_profile_paths, run_identity, root=root
            )
        else:
            profile_path, profile_data, _ = load_json_file(preference_profile_paths)
            result = {
                "valid": False, "pool_path": pool_path, "profile_path": profile_path,
                "pool_data": pool_data, "profile_data": profile_data,
                "errors": ["stable reference_discovery.py is missing"],
                "rated_sample_ids": [], "pairwise_required": False,
                "pairwise_generation_allowed": False,
            }
        if workflow_version in {SKILL_VERSION, "0.7.0", "0.7.0-beta.3"} and (
            not isinstance(pool_data, dict) or pool_data.get("version") != 2
        ):
            result["valid"] = False
            result["errors"].append("new stable visual_reference_pool.json version must be 2")
        # The discovery flow only searches/replaces references; it cannot authorize image calls.
        result["pairwise_required"] = False
        result["pairwise_generation_allowed"] = False
        result["discovery_contract_version"] = 2
        return result
    profile_path, profile_data, profile_load_error = load_json_file(
        preference_profile_paths
    )
    if pool_load_error:
        errors.append(f"visual_reference_pool.json {pool_load_error}")
    if profile_load_error:
        errors.append(f"visual_preference_profile.json {profile_load_error}")
    validation_root = (
        root.expanduser().resolve()
        if root is not None
        else pool_path.parent.resolve()
        if pool_path is not None
        else profile_path.parent.resolve()
        if profile_path is not None
        else Path.cwd().resolve()
    )
    if pool_data is not None:
        module_contract_required = module_card_contract_required(
            pool_data, workflow_version
        )
        errors.extend(
            validate_module_reference_cards(
                pool_data,
                validation_root,
                required=module_contract_required,
            )
        )
        errors.extend(
            validate_visual_module_evidence(
                pool_data,
                validation_root,
                required=module_contract_required,
            )
        )
        errors.extend(
            validate_rating_submission_snapshot(
                pool_path,
                pool_data,
                required=module_contract_required,
            )
        )
    if pool_data is None or profile_data is None:
        return {
            "valid": False,
            "pool_path": pool_path,
            "profile_path": profile_path,
            "errors": errors,
            "pool_data": pool_data,
            "profile_data": profile_data,
            "rated_sample_ids": [],
            "pairwise_required": False,
            "pairwise_generation_allowed": False,
        }
    if pool_data.get("version") != 1:
        errors.append("visual_reference_pool.json version must be 1")
    if str(pool_data.get("run_identity", "")).strip() != run_identity:
        errors.append(
            "visual_reference_pool.json run_identity does not match active_run.json"
        )
    if str(pool_data.get("status", "")).strip().upper() != "RATED":
        errors.append("visual_reference_pool.json status must be RATED")
    if str(pool_data.get("source_policy_version", "")).strip() != "1":
        errors.append("visual_reference_pool.json source_policy_version must be 1")

    selection_mode = str(pool_data.get("selection_mode", "")).strip().upper()
    if selection_mode not in {"STANDARD", "SPARSE_CATEGORY"}:
        errors.append(
            "visual_reference_pool.json selection_mode must be STANDARD or SPARSE_CATEGORY"
        )
    sparse_category_reason = pool_data.get("sparse_category_reason")
    if selection_mode == "SPARSE_CATEGORY" and (
        not isinstance(sparse_category_reason, str)
        or not sparse_category_reason.strip()
    ):
        errors.append(
            "visual_reference_pool.json sparse_category_reason is required for SPARSE_CATEGORY"
        )
    samples = pool_data.get("samples")
    minimum_samples = 6 if selection_mode == "SPARSE_CATEGORY" else 8
    if not isinstance(samples, list) or not minimum_samples <= len(samples) <= 12:
        errors.append(
            "visual_reference_pool.json samples must contain "
            f"{minimum_samples}-12 cards for {selection_mode or 'the selected mode'}"
        )
        samples = []

    sample_ids: set[str] = set()
    rated_sample_ids: set[str] = set()
    positive_visual_ids: set[str] = set()
    positive_layout_ids: set[str] = set()
    negative_visual_ids: set[str] = set()
    negative_layout_ids: set[str] = set()
    project_urls: set[str] = set()
    covered_roles: set[str] = set()
    covered_tiers: set[str] = set()
    product_relevant_tier_count = 0
    contrast_tier_count = 0
    cross_axis_conflict = False
    core_source_count = 0
    allowed_sources = (
        VISUAL_REFERENCE_CORE_SOURCES | VISUAL_REFERENCE_SUPPLEMENT_SOURCES
    )
    for index, sample in enumerate(samples):
        prefix = f"visual_reference_pool.json samples[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{prefix} must be an object")
            continue
        sample_id = str(sample.get("id", "")).strip()
        if not sample_id:
            errors.append(f"{prefix}.id is required")
        elif sample_id in sample_ids:
            errors.append(f"{prefix}.id is duplicate: {sample_id}")
        else:
            sample_ids.add(sample_id)

        source_key = str(sample.get("source_key", "")).strip().upper()
        if source_key not in allowed_sources:
            errors.append(f"{prefix}.source_key is not an approved reference source")
        elif source_key in VISUAL_REFERENCE_CORE_SOURCES:
            core_source_count += 1
        if not str(sample.get("project", "")).strip():
            errors.append(f"{prefix}.project is required")
        project_url = str(sample.get("project_url", "")).strip()
        if not re.match(r"^https?://", project_url, flags=re.IGNORECASE):
            errors.append(f"{prefix}.project_url must be a traceable http(s) URL")
        else:
            canonical_url, hostname, url_error = canonical_project_url(project_url)
            if url_error:
                errors.append(f"{prefix}.project_url {url_error}")
            elif canonical_url in project_urls:
                errors.append(
                    f"{prefix}.project_url duplicates another project after URL normalization"
                )
            else:
                assert canonical_url is not None
                project_urls.add(canonical_url)
            if hostname and hostname_matches(
                hostname, VISUAL_REFERENCE_FORBIDDEN_DOMAINS
            ):
                errors.append(
                    f"{prefix}.project_url uses a discovery/UI source forbidden in the final pool"
                )
        _, hostname, _ = canonical_project_url(project_url)
        if hostname and source_key in VISUAL_REFERENCE_SOURCE_DOMAINS:
            if not hostname_matches(
                hostname, VISUAL_REFERENCE_SOURCE_DOMAINS[source_key]
            ):
                errors.append(
                    f"{prefix}.project_url domain does not match source_key {source_key}"
                )
        role = str(sample.get("role", "")).strip().upper()
        if role not in VISUAL_REFERENCE_ROLES:
            errors.append(f"{prefix}.role is invalid")
        else:
            covered_roles.add(role)
        reference_tier = str(sample.get("reference_tier", "")).strip().upper()
        if reference_tier not in VISUAL_REFERENCE_TIERS:
            errors.append(f"{prefix}.reference_tier is invalid")
        else:
            covered_tiers.add(reference_tier)
            if reference_tier in {"SAME_CATEGORY", "ADJACENT_PREMIUM"}:
                product_relevant_tier_count += 1
            if reference_tier == "CONTRAST":
                contrast_tier_count += 1

        quality_score = sample.get("quality_score")
        if (
            isinstance(quality_score, bool)
            or not isinstance(quality_score, int)
            or not 20 <= quality_score <= 25
        ):
            errors.append(f"{prefix}.quality_score must be an integer from 20 to 25")
        quality_flags = sample.get("quality_flags")
        if not isinstance(quality_flags, dict):
            errors.append(f"{prefix}.quality_flags must be an object")
        else:
            for flag in sorted(VISUAL_REFERENCE_QUALITY_FLAGS):
                if quality_flags.get(flag) is not True:
                    errors.append(f"{prefix}.quality_flags.{flag} must be true")

        axis_rated: dict[str, bool] = {}
        axis_values: dict[str, int | None] = {}
        for axis in ("visual", "layout"):
            value = sample.get(axis)
            if value is None:
                axis_rated[axis] = False
                axis_values[axis] = None
            elif (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value not in {-1, 0, 1}
            ):
                errors.append(f"{prefix}.{axis} must be -1, 0, 1, or null")
                axis_rated[axis] = False
                axis_values[axis] = None
            else:
                axis_rated[axis] = True
                axis_values[axis] = value
                if sample_id and value == 1:
                    (
                        positive_visual_ids
                        if axis == "visual"
                        else positive_layout_ids
                    ).add(sample_id)
                if sample_id and value == -1:
                    (
                        negative_visual_ids
                        if axis == "visual"
                        else negative_layout_ids
                    ).add(sample_id)
        if all(axis_rated.values()) and sample_id:
            rated_sample_ids.add(sample_id)
            if (axis_values["visual"], axis_values["layout"]) in {
                (1, -1),
                (-1, 1),
            }:
                cross_axis_conflict = True

    if samples:
        required_core_count = (len(samples) * 4 + 4) // 5
        if core_source_count < required_core_count:
            errors.append(
                "visual_reference_pool.json must use core fixed sources for at least 80% of cards"
            )
    if len(rated_sample_ids) < 6:
        errors.append(
            "visual_reference_pool.json needs at least 6 samples rated on both visual and layout"
        )
    for required_role in ("VISUAL_STYLE", "LAYOUT"):
        if required_role not in covered_roles:
            errors.append(
                f"visual_reference_pool.json needs at least one {required_role} card"
            )
    if samples:
        minimum_tiers = 2 if selection_mode == "SPARSE_CATEGORY" else 3
        if len(covered_tiers) < minimum_tiers:
            errors.append(
                "visual_reference_pool.json reference_tier diversity is too narrow: "
                f"at least {minimum_tiers} tiers are required"
            )
        if product_relevant_tier_count * 2 < len(samples):
            errors.append(
                "visual_reference_pool.json needs at least 50% SAME_CATEGORY or ADJACENT_PREMIUM cards"
            )
        if contrast_tier_count * 4 > len(samples):
            errors.append(
                "visual_reference_pool.json CONTRAST cards may not exceed 25% of the pool"
            )

    if profile_data.get("version") != 1:
        errors.append("visual_preference_profile.json version must be 1")
    if str(profile_data.get("run_identity", "")).strip() != run_identity:
        errors.append(
            "visual_preference_profile.json run_identity does not match active_run.json"
        )
    if str(profile_data.get("status", "")).strip().upper() != "APPROVED":
        errors.append("visual_preference_profile.json status must be APPROVED")
    if pool_path is not None:
        expected_pool_hash = file_sha256(pool_path)
        if (
            str(profile_data.get("reference_pool_sha256", "")).strip().lower()
            != expected_pool_hash
        ):
            errors.append(
                "visual_preference_profile.json reference_pool_sha256 hash mismatch"
            )

    for system_name in ("visual_system", "layout_system"):
        system = profile_data.get(system_name)
        if not isinstance(system, dict):
            errors.append(f"visual_preference_profile.json {system_name} must be an object")
            continue
        if not nonempty_string_list(system.get("keep")):
            errors.append(
                f"visual_preference_profile.json {system_name}.keep "
                "must be a non-empty string list"
            )
        if not string_list(system.get("exclude")):
            errors.append(
                f"visual_preference_profile.json {system_name}.exclude "
                "must be a string list; use [] when that axis has no negative evidence"
            )
        negative_ids = (
            negative_visual_ids if system_name == "visual_system" else negative_layout_ids
        )
        if not negative_ids and isinstance(system.get("exclude"), list) and system.get(
            "exclude"
        ):
            errors.append(
                f"visual_preference_profile.json {system_name}.exclude must be [] "
                "because that axis has no -1 rating evidence"
            )
        if negative_ids and isinstance(system.get("exclude"), list) and not system.get(
            "exclude"
        ):
            errors.append(
                f"visual_preference_profile.json {system_name}.exclude must be non-empty "
                "because that axis contains -1 rating evidence"
            )

    hybrid_recipe = profile_data.get("hybrid_recipe")
    if not isinstance(hybrid_recipe, dict):
        errors.append("visual_preference_profile.json hybrid_recipe must be an object")
    else:
        anchor_requirements = {
            "visual_anchor_sample_ids": positive_visual_ids,
            "layout_anchor_sample_ids": positive_layout_ids,
        }
        for anchor_key, positive_ids in anchor_requirements.items():
            anchors = hybrid_recipe.get(anchor_key)
            if not positive_ids:
                if anchors != []:
                    errors.append(
                        f"visual_preference_profile.json hybrid_recipe.{anchor_key} "
                        "must be [] because that axis has no cards rated 1; "
                        "resolve the direction through controlled pairwise evidence"
                    )
                continue
            if not nonempty_string_list(anchors):
                errors.append(
                    f"visual_preference_profile.json hybrid_recipe.{anchor_key} "
                    "must be a non-empty string list"
                )
                continue
            unknown_anchors = sorted(set(anchors) - positive_ids)
            if unknown_anchors:
                errors.append(
                    f"visual_preference_profile.json hybrid_recipe.{anchor_key} "
                    "must reference sample ids rated 1 on that axis: "
                    + ", ".join(unknown_anchors)
                )
        if not nonempty_string_list(hybrid_recipe.get("rules")):
            errors.append(
                "visual_preference_profile.json hybrid_recipe.rules must be a non-empty string list"
            )

    if not string_list(profile_data.get("rejected_patterns")):
        errors.append(
            "visual_preference_profile.json rejected_patterns must be a string list; "
            "use [] when the ratings contain no negative evidence"
        )
    elif (
        not negative_visual_ids
        and not negative_layout_ids
        and profile_data.get("rejected_patterns")
    ):
        errors.append(
            "visual_preference_profile.json rejected_patterns must be [] because the pool has no -1 ratings"
        )
    elif (
        (negative_visual_ids or negative_layout_ids)
        and not profile_data.get("rejected_patterns")
    ):
        errors.append(
            "visual_preference_profile.json rejected_patterns must be non-empty because the pool contains -1 ratings"
        )
    pairwise_foundation_valid = not errors
    pairwise_round = profile_data.get("pairwise_round")
    pairwise_required = False
    pairwise_generation_allowed = False
    pairwise_status = ""
    if not isinstance(pairwise_round, dict):
        errors.append("visual_preference_profile.json pairwise_round must be an object")
    else:
        pairwise_status = str(pairwise_round.get("status", "")).strip().upper()
        if pairwise_status not in {"APPROVED", "PENDING", "NOT_REQUIRED"}:
            errors.append(
                "visual_preference_profile.json pairwise_round.status must be "
                "APPROVED, PENDING, or NOT_REQUIRED"
            )
        reason = pairwise_round.get("reason")
        reason_valid = isinstance(reason, str) and bool(reason.strip())
        if not reason_valid:
            errors.append(
                "visual_preference_profile.json pairwise_round.reason is required"
            )
        pairwise_required = (
            len(positive_visual_ids) < 2
            or len(positive_layout_ids) < 2
            or not (positive_visual_ids & positive_layout_ids)
            or cross_axis_conflict
        )
        if pairwise_required and pairwise_status == "NOT_REQUIRED":
            errors.append(
                "visual_preference_profile.json pairwise_round must be PENDING or "
                "APPROVED when an axis has fewer than two positive cards, positive "
                "anchors do not overlap, or a card has cross-axis conflict"
            )
        comparisons = pairwise_round.get("comparisons")
        candidates = pairwise_round.get("candidates")
        control_values = pairwise_round.get("control_values")
        controls = pairwise_round.get("controls")
        controls_declared_valid = bool(
            isinstance(controls, list)
            and len(controls) == len(PAIRWISE_CONTROLS)
            and all(isinstance(item, str) for item in controls)
            and {item.strip() for item in controls} == PAIRWISE_CONTROLS
        )
        if not controls_declared_valid:
            errors.append(
                "visual_preference_profile.json pairwise_round.controls must contain "
                "same_product, same_copy, same_slot, and same_canvas"
            )

        control_context: dict[str, Any] = {
            "controls_hash": None,
            "product_path": None,
            "product_relative": None,
            "product_hash": "",
            "slot_id": "",
            "target_size": None,
        }
        pairwise_controls_valid = False
        if pairwise_status in {"APPROVED", "PENDING"}:
            control_context, control_errors = validate_pairwise_control_values(
                control_values, validation_root
            )
            errors.extend(control_errors)
            pairwise_controls_valid = not control_errors

        if pairwise_status == "PENDING":
            candidates_empty = candidates == []
            comparisons_empty = comparisons == []
            if not candidates_empty:
                errors.append(
                    "visual_preference_profile.json pairwise_round.candidates must be [] "
                    "while status is PENDING; publish generated evidence atomically with APPROVED"
                )
            if not comparisons_empty:
                errors.append(
                    "visual_preference_profile.json pairwise_round.comparisons must be [] "
                    "while status is PENDING"
                )
            pairwise_generation_allowed = bool(
                pairwise_foundation_valid
                and reason_valid
                and controls_declared_valid
                and pairwise_controls_valid
                and candidates_empty
                and comparisons_empty
            )
            errors.append(
                "visual_preference_profile.json pairwise_round is PENDING; generate the "
                "controlled candidates, record the user comparison, then set APPROVED"
            )
        elif pairwise_status == "APPROVED":
            controls_hash = control_context["controls_hash"]
            controlled_product_relative = control_context["product_relative"]
            controlled_product_hash = control_context["product_hash"]
            controlled_slot_id = control_context["slot_id"]
            controlled_target_size = control_context["target_size"]

            candidate_ids: set[str] = set()
            generation_ids: set[str] = set()
            output_paths: set[str] = set()
            output_hashes: set[str] = set()
            prompt_hashes: set[str] = set()
            if not isinstance(candidates, list) or len(candidates) < 2:
                errors.append(
                    "visual_preference_profile.json pairwise_round.candidates must contain "
                    "at least two generated candidates when status is APPROVED"
                )
                candidates = []
            ledger_input_paths = generation_ledger_paths
            if ledger_input_paths is None:
                inferred_ledger = validation_root / "generation_ledger.jsonl"
                ledger_input_paths = [inferred_ledger] if inferred_ledger.is_file() else []
            _, pairwise_ledger_records, ledger_errors = read_jsonl(ledger_input_paths)
            if ledger_errors:
                errors.extend(f"pairwise evidence: {error}" for error in ledger_errors)
            for index, candidate in enumerate(candidates):
                prefix = (
                    "visual_preference_profile.json "
                    f"pairwise_round.candidates[{index}]"
                )
                if not isinstance(candidate, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                candidate_value = candidate.get("candidate_id")
                candidate_id = (
                    candidate_value.strip()
                    if isinstance(candidate_value, str)
                    else ""
                )
                if not candidate_id:
                    errors.append(f"{prefix}.candidate_id is required")
                elif candidate_id.upper() == "REJECT":
                    errors.append(f"{prefix}.candidate_id may not use reserved value REJECT")
                elif candidate_id in candidate_ids:
                    errors.append(f"{prefix}.candidate_id is duplicate")
                else:
                    candidate_ids.add(candidate_id)

                generation_value = candidate.get("generation_id")
                generation_id = (
                    generation_value.strip()
                    if isinstance(generation_value, str)
                    else ""
                )
                if not generation_id:
                    errors.append(f"{prefix}.generation_id is required")
                elif generation_id in generation_ids:
                    errors.append(f"{prefix}.generation_id is duplicate")
                else:
                    generation_ids.add(generation_id)

                output_value = candidate.get("output_path")
                output_text = (
                    output_value.strip() if isinstance(output_value, str) else ""
                )
                output_path: Path | None = None
                canonical_output_path: str | None = None
                if not output_text:
                    errors.append(f"{prefix}.output_path is required")
                else:
                    try:
                        candidate_output_path = (
                            validation_root / output_text
                        ).resolve()
                    except (OSError, RuntimeError, ValueError) as exc:
                        errors.append(f"{prefix}.output_path is invalid: {exc}")
                    else:
                        try:
                            canonical_output_path = candidate_output_path.relative_to(
                                validation_root
                            ).as_posix()
                        except ValueError:
                            errors.append(f"{prefix}.output_path escapes project root")
                        else:
                            output_path = candidate_output_path
                            if canonical_output_path in output_paths:
                                errors.append(f"{prefix}.output_path is duplicate")
                            else:
                                output_paths.add(canonical_output_path)
                            try:
                                output_exists = output_path.is_file()
                            except OSError as exc:
                                errors.append(
                                    f"{prefix}.output_path cannot be inspected: {exc}"
                                )
                                output_exists = False
                            if not output_exists:
                                errors.append(f"{prefix}.output_path is missing")

                output_value = candidate.get("output_sha256")
                output_hash = (
                    output_value.strip().lower()
                    if isinstance(output_value, str)
                    else ""
                )
                if not re.fullmatch(r"[0-9a-f]{64}", output_hash):
                    errors.append(f"{prefix}.output_sha256 is invalid")
                else:
                    if output_hash in output_hashes:
                        errors.append(f"{prefix}.output_sha256 is duplicate")
                    else:
                        output_hashes.add(output_hash)
                    if output_path is not None:
                        try:
                            output_exists = output_path.is_file()
                        except OSError:
                            output_exists = False
                        if output_exists:
                            try:
                                actual_output_hash = file_sha256(output_path)
                            except OSError as exc:
                                errors.append(f"{prefix}.output_path cannot be hashed: {exc}")
                            else:
                                if actual_output_hash != output_hash:
                                    errors.append(f"{prefix}.output hash mismatch")

                prompt_value = candidate.get("prompt_sha256")
                prompt_hash = (
                    prompt_value.strip().lower()
                    if isinstance(prompt_value, str)
                    else ""
                )
                if not re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
                    errors.append(f"{prefix}.prompt_sha256 is invalid")
                elif prompt_hash in prompt_hashes:
                    errors.append(f"{prefix}.prompt_sha256 is duplicate")
                else:
                    prompt_hashes.add(prompt_hash)

                matching_records = [
                    record
                    for record in pairwise_ledger_records
                    if record.get("run_identity") == run_identity
                    and record.get("generation_id") == generation_id
                    and record.get("stage") == "VISUAL_PREFERENCE_PAIRWISE"
                    and record.get("status") == "SUCCEEDED"
                ]
                if not matching_records:
                    errors.append(
                        f"{prefix} has no successful VISUAL_PREFERENCE_PAIRWISE ledger evidence"
                    )
                else:
                    record = matching_records[-1]
                    if record.get("version") != 1:
                        errors.append(f"{prefix} ledger version must be 1")
                    if record.get("provider") != "image2":
                        errors.append(f"{prefix} ledger provider must be image2")
                    if record.get("slot_id") != controlled_slot_id:
                        errors.append(f"{prefix} ledger slot_id mismatch")
                    if record.get("route") not in {
                        "DIRECT_IMAGE_INPUT",
                        "VISUAL_CONTEXT_RELAY",
                    }:
                        errors.append(f"{prefix} ledger route is invalid")
                    if record.get("output_path") != canonical_output_path:
                        errors.append(f"{prefix} ledger output_path mismatch")
                    if record.get("output_sha256") != output_hash:
                        errors.append(f"{prefix} ledger output hash mismatch")
                    if record.get("prompt_sha256") != prompt_hash:
                        errors.append(f"{prefix} ledger prompt hash mismatch")
                    if record.get("pairwise_controls_sha256") != controls_hash:
                        errors.append(f"{prefix} ledger controls hash mismatch")
                    elapsed_ms = record.get("elapsed_ms")
                    elapsed_value = finite_elapsed_ms(elapsed_ms)
                    if elapsed_value is None:
                        errors.append(f"{prefix} ledger elapsed_ms is invalid")
                    started_at = parse_iso_timestamp(record.get("started_at"))
                    completed_at = parse_iso_timestamp(record.get("completed_at"))
                    if started_at is None or completed_at is None:
                        errors.append(f"{prefix} ledger timestamps are invalid")
                    elif started_at.tzinfo != completed_at.tzinfo:
                        errors.append(f"{prefix} ledger timestamps mix timezone modes")
                    else:
                        measured_ms = (
                            completed_at - started_at
                        ).total_seconds() * 1000
                        if measured_ms < 0:
                            errors.append(f"{prefix} ledger timestamps are reversed")
                        elif elapsed_value is not None and abs(
                            measured_ms - elapsed_value
                        ) > TIMING_TOLERANCE_MS:
                            errors.append(
                                f"{prefix} ledger elapsed_ms is inconsistent with timestamps"
                            )
                    try:
                        output_exists = bool(
                            output_path is not None and output_path.is_file()
                        )
                        actual_width, actual_height = (
                            image_dimensions(output_path)
                            if output_path is not None and output_exists
                            else (None, None)
                        )
                    except (OSError, RuntimeError, ValueError):
                        actual_width, actual_height = (None, None)
                    if (
                        actual_width is None
                        or actual_height is None
                        or record.get("width") != actual_width
                        or record.get("height") != actual_height
                    ):
                        errors.append(f"{prefix} ledger dimensions mismatch")
                    elif controlled_target_size != (actual_width, actual_height):
                        errors.append(
                            f"{prefix} output dimensions do not match control_values.target_size"
                        )
                    references = record.get("reference_inputs")
                    if not isinstance(references, list) or not references:
                        errors.append(f"{prefix} ledger reference_inputs are missing")
                    elif not any(
                        isinstance(reference, dict)
                        and reference.get("path") == controlled_product_relative
                        and reference.get("sha256") == controlled_product_hash
                        for reference in references
                    ):
                        errors.append(
                            f"{prefix} ledger does not bind the controlled product reference"
                        )

            if not isinstance(comparisons, list) or not comparisons:
                errors.append(
                    "visual_preference_profile.json pairwise_round.comparisons must contain "
                    "at least one recorded user comparison when status is APPROVED"
                )
            else:
                seen_pair_ids: set[str] = set()
                for index, comparison in enumerate(comparisons):
                    prefix = (
                        "visual_preference_profile.json "
                        f"pairwise_round.comparisons[{index}]"
                    )
                    if not isinstance(comparison, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    pair_id = str(comparison.get("pair_id", "")).strip()
                    if not pair_id:
                        errors.append(f"{prefix}.pair_id is required")
                    elif pair_id in seen_pair_ids:
                        errors.append(f"{prefix}.pair_id is duplicate")
                    else:
                        seen_pair_ids.add(pair_id)
                    compared_ids = comparison.get("candidate_ids")
                    if (
                        not isinstance(compared_ids, list)
                        or len(compared_ids) != 2
                        or not all(isinstance(value, str) for value in compared_ids)
                        or len(set(compared_ids)) != 2
                        or not all(value in candidate_ids for value in compared_ids)
                    ):
                        errors.append(
                            f"{prefix}.candidate_ids must name two distinct generated candidates"
                        )
                        allowed_choices: set[str] = {"REJECT"}
                    else:
                        allowed_choices = set(compared_ids) | {"REJECT"}
                    for field in ("visual_choice", "layout_choice"):
                        choice = str(comparison.get(field, "")).strip()
                        if choice not in allowed_choices:
                            errors.append(
                                f"{prefix}.{field} must choose a compared candidate or REJECT"
                            )
        elif pairwise_status == "NOT_REQUIRED":
            if control_values != {}:
                errors.append(
                    "visual_preference_profile.json pairwise_round.control_values must be {} "
                    "when status is NOT_REQUIRED"
                )
            if candidates != []:
                errors.append(
                    "visual_preference_profile.json pairwise_round.candidates must be [] "
                    "when status is NOT_REQUIRED"
                )
            if comparisons != []:
                errors.append(
                    "visual_preference_profile.json pairwise_round.comparisons must be [] "
                    "when status is NOT_REQUIRED"
                )

    return {
        "valid": not errors,
        "pool_path": pool_path,
        "profile_path": profile_path,
        "errors": errors,
        "pool_data": pool_data,
        "profile_data": profile_data,
        "rated_sample_ids": sorted(rated_sample_ids),
        "pairwise_required": pairwise_required,
        "pairwise_generation_allowed": pairwise_generation_allowed,
    }


def read_jsonl(paths: list[Path]) -> tuple[Path | None, list[dict[str, Any]], list[str]]:
    if not paths:
        return None, [], ["generation_ledger.jsonl is missing"]
    path = sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)[0]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return path, [], [f"generation_ledger.jsonl cannot be read: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite JSON number {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"generation_ledger.jsonl line {line_number} invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"generation_ledger.jsonl line {line_number} must be an object")
            continue
        records.append(record)
    return path, records, errors


def validate_style_sample_ledger(
    paths: list[Path],
    root: Path,
    run_identity: str,
    samples_by_branch: dict[str, list[Path]],
    visual_preference_profile_path: Path | None = None,
    require_profile_binding: bool = False,
) -> dict[str, Any]:
    path, records, errors = read_jsonl(paths)
    expected_profile_hash = (
        file_sha256(visual_preference_profile_path)
        if visual_preference_profile_path is not None
        and visual_preference_profile_path.is_file()
        else None
    )
    if require_profile_binding and expected_profile_hash is None:
        errors.append(
            "style sample ledger requires the current visual_preference_profile.json"
        )
    valid_branches: list[str] = []
    for branch in ("A", "B", "C"):
        samples = samples_by_branch.get(branch, [])
        if not samples:
            continue
        sample_valid = False
        branch_errors: list[str] = []
        for sample in samples:
            relative = sample.resolve().relative_to(root.resolve()).as_posix()
            matches = [
                record
                for record in records
                if record.get("output_path") == relative
                and record.get("run_identity") == run_identity
                and record.get("stage") == "STYLE_SAMPLES"
                and record.get("status") == "SUCCEEDED"
            ]
            if not matches:
                branch_errors.append(f"no successful ledger evidence for style {branch}: {relative}")
                continue
            record = matches[-1]
            record_errors: list[str] = []
            if record.get("version") != 1:
                record_errors.append(f"style {branch} ledger version must be 1")
            if record.get("provider") != "image2":
                record_errors.append(f"style {branch} ledger provider must be image2")
            if (
                require_profile_binding
                and record.get("visual_preference_profile_sha256")
                != expected_profile_hash
            ):
                record_errors.append(
                    f"style {branch} ledger visual_preference_profile_sha256 hash mismatch"
                )
            for field in ("generation_id", "slot_id"):
                if not str(record.get(field, "")).strip():
                    record_errors.append(f"style {branch} ledger {field} is missing")
            elapsed_ms = record.get("elapsed_ms")
            elapsed_value = finite_elapsed_ms(elapsed_ms)
            if elapsed_value is None:
                record_errors.append(f"style {branch} ledger elapsed_ms is missing or invalid")
            started_at = parse_iso_timestamp(record.get("started_at"))
            completed_at = parse_iso_timestamp(record.get("completed_at"))
            if started_at is None or completed_at is None:
                record_errors.append(f"style {branch} ledger timestamps are invalid")
            elif started_at.tzinfo != completed_at.tzinfo:
                record_errors.append(f"style {branch} ledger timestamps mix timezone modes")
            else:
                measured_ms = (completed_at - started_at).total_seconds() * 1000
                if measured_ms < 0:
                    record_errors.append(f"style {branch} ledger timestamps are reversed")
                elif elapsed_value is not None:
                    if abs(measured_ms - elapsed_value) > TIMING_TOLERANCE_MS:
                        record_errors.append(
                            f"style {branch} ledger elapsed_ms is inconsistent with timestamps"
                        )
            actual_width, actual_height = image_dimensions(sample)
            width = record.get("width")
            height = record.get("height")
            if (
                actual_width is None
                or actual_height is None
                or isinstance(width, bool)
                or isinstance(height, bool)
                or not isinstance(width, int)
                or not isinstance(height, int)
                or width <= 0
                or height <= 0
                or width != actual_width
                or height != actual_height
            ):
                record_errors.append(f"style {branch} ledger dimensions are invalid or mismatched")
            if record.get("route") not in {"DIRECT_IMAGE_INPUT", "VISUAL_CONTEXT_RELAY"}:
                record_errors.append(f"style {branch} ledger route is invalid")
            prompt_hash = str(record.get("prompt_sha256", ""))
            if not re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
                record_errors.append(f"style {branch} ledger prompt hash is invalid")
            if record.get("output_sha256") != file_sha256(sample):
                record_errors.append(f"style {branch} ledger output hash mismatch")
            references = record.get("reference_inputs")
            if not isinstance(references, list) or not references:
                record_errors.append(f"style {branch} ledger reference_inputs are missing")
            else:
                for reference in references:
                    if not isinstance(reference, dict):
                        record_errors.append(f"style {branch} ledger reference input is invalid")
                        continue
                    reference_path = (root / str(reference.get("path", ""))).resolve()
                    try:
                        reference_path.relative_to(root.resolve())
                    except ValueError:
                        record_errors.append(f"style {branch} ledger reference escapes project root")
                        continue
                    if not reference_path.is_file():
                        record_errors.append(f"style {branch} ledger reference is missing")
                    elif reference.get("sha256") != file_sha256(reference_path):
                        record_errors.append(f"style {branch} ledger reference hash mismatch")
            if not record_errors:
                sample_valid = True
                break
            branch_errors.extend(record_errors)
        if sample_valid:
            valid_branches.append(branch)
        else:
            errors.extend(branch_errors or [f"style {branch} has no valid image2 ledger evidence"])
    return {
        "valid": set(valid_branches) == {"A", "B", "C"} and not errors,
        "path": path,
        "errors": errors,
        "valid_branches": valid_branches,
    }


def validate_scope_plan_counts(root: Path, slots: list[Any]) -> list[str]:
    """Keep dual-ratio scope quantities binding all the way through the canonical plan."""
    scope_path = root / "production_scope.json"
    if not scope_path.is_file():
        return []
    scope = validate_production_scope([scope_path])
    data = scope.get("data") or {}
    main = data.get("main") if isinstance(data.get("main"), dict) else {}
    ratios = main.get("ratios", [])
    if not main.get("enabled") or not isinstance(ratios, list) or set(map(str, ratios)) != {"1:1", "4:5"}:
        return []
    if not scope["valid"]:
        return [f"production_scope.json {error}" for error in scope["errors"]]
    counts = {"1:1": 0, "4:5": 0}
    errors: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or str(slot.get("group", "")).upper() != "MAIN":
            continue
        size = slot.get("target_size")
        if not isinstance(size, list) or len(size) != 2 or not all(
            isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in size
        ):
            continue
        if size[0] == size[1]:
            counts["1:1"] += 1
        elif size[0] * 5 == size[1] * 4:
            counts["4:5"] += 1
        else:
            errors.append(f"MAIN slot {slot.get('slot_id')} must use a requested 1:1 or 4:5 target")
    for ratio, count in counts.items():
        expected = main["count_by_ratio"][ratio]
        if count != expected:
            errors.append(
                f"production plan MAIN {ratio} slots ({count}) must match "
                f"main.count_by_ratio.{ratio} ({expected})"
            )
    return errors


def validate_production_plan(
    paths: list[Path],
    run_identity: str,
    selected_style: str,
    visual_preference_profile_path: Path | None = None,
    require_profile_binding: bool = False,
) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {"valid": False, "path": path, "errors": errors, "data": data}
    assert data is not None
    if data.get("version") != 1:
        errors.append("production_plan.json version must be 1")
    if str(data.get("run_identity", "")).strip() != run_identity:
        errors.append("production_plan.json run_identity does not match active_run.json")
    if str(data.get("status", "")).strip().upper() != "APPROVED":
        errors.append("production_plan.json status must be APPROVED")
    if str(data.get("selected_style", "")).strip().upper() != selected_style:
        errors.append("production_plan.json selected_style does not match selected_style.md")
    expected_profile_hash = (
        file_sha256(visual_preference_profile_path)
        if visual_preference_profile_path is not None
        and visual_preference_profile_path.is_file()
        else None
    )
    if require_profile_binding and expected_profile_hash is None:
        errors.append(
            "production_plan.json requires the current visual_preference_profile.json"
        )
    elif (
        require_profile_binding
        and data.get("visual_preference_profile_sha256") != expected_profile_hash
    ):
        errors.append(
            "production_plan.json visual_preference_profile_sha256 hash mismatch"
        )
    slots = data.get("slots")
    if not isinstance(slots, list) or not slots:
        errors.append("production_plan.json slots must contain at least one slot")
        slots = []
    seen_slot_ids: set[str] = set()
    for index, slot in enumerate(slots):
        prefix = f"production_plan.json slots[{index}]"
        if not isinstance(slot, dict):
            errors.append(f"{prefix} must be an object")
            continue
        slot_id = str(slot.get("slot_id", "")).strip()
        if not slot_id:
            errors.append(f"{prefix}.slot_id is required")
        elif slot_id in seen_slot_ids:
            errors.append(f"{prefix}.slot_id is duplicated: {slot_id}")
        else:
            seen_slot_ids.add(slot_id)
        if not str(slot.get("output_path", "")).strip():
            errors.append(f"{prefix}.output_path is required")
        target_size = slot.get("target_size")
        if (
            not isinstance(target_size, list)
            or len(target_size) != 2
            or not all(
                isinstance(value, int) and not isinstance(value, bool) and value > 0
                for value in target_size
            )
        ):
            errors.append(f"{prefix}.target_size must contain two positive integers")
        embedded_copy = slot.get("image_embedded_copy")
        if not isinstance(embedded_copy, list):
            errors.append(f"{prefix}.image_embedded_copy must be a list")
        seconds = slot.get("estimated_seconds")
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or seconds < 0
        ):
            errors.append(f"{prefix}.estimated_seconds must be non-negative")
        if not isinstance(slot.get("independent"), bool):
            errors.append(f"{prefix}.independent must be an explicit boolean")
        if not isinstance(slot.get("parallel_gain"), bool):
            errors.append(f"{prefix}.parallel_gain must be an explicit boolean")
    if path is not None:
        errors.extend(validate_scope_plan_counts(path.parent, slots))
    return {"valid": not errors, "path": path, "errors": errors, "data": data}


def validate_preflight(
    paths: list[Path],
    root: Path | None = None,
    production_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {"valid": False, "path": path, "errors": errors, "status": None, "data": data}
    assert data is not None
    status = str(data.get("status", "")).strip().upper()
    if data.get("version") != 1:
        errors.append("preflight_qc.json version must be 1")
    if status not in {"PASS", "NEEDS_VISUAL_QC"}:
        errors.append("preflight_qc.json status must be PASS or NEEDS_VISUAL_QC")
    slots = data.get("slots")
    if not isinstance(slots, list) or not slots:
        errors.append("preflight_qc.json slots must be a non-empty list")
        slots = []
    plan_slots: dict[str, dict[str, Any]] = {}
    if isinstance(production_plan, dict):
        raw_plan_slots = production_plan.get("slots", [])
        if isinstance(raw_plan_slots, list):
            plan_slots = {
                str(slot.get("slot_id", "")).strip(): slot
                for slot in raw_plan_slots
                if isinstance(slot, dict) and str(slot.get("slot_id", "")).strip()
            }
    report_slot_ids: set[str] = set()
    needs_visual_qc = False
    for index, slot in enumerate(slots):
        prefix = f"preflight_qc.json slots[{index}]"
        if not isinstance(slot, dict):
            errors.append(f"{prefix} must be an object")
            continue
        slot_id = str(slot.get("slot_id", "")).strip()
        if not slot_id:
            errors.append(f"{prefix}.slot_id is required")
        elif slot_id in report_slot_ids:
            errors.append(f"{prefix}.slot_id is duplicated: {slot_id}")
        else:
            report_slot_ids.add(slot_id)
        if slot.get("exists") is not True:
            errors.append(f"{prefix}.exists must be true")
        if not re.fullmatch(r"[0-9a-f]{64}", str(slot.get("sha256", ""))):
            errors.append(f"{prefix}.sha256 is invalid")
        dimensions = slot.get("dimensions")
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != 2
            or not all(isinstance(value, int) and value > 0 for value in dimensions)
        ):
            errors.append(f"{prefix}.dimensions must contain two positive integers")
        dimension_status = str(slot.get("dimension_status", "")).upper()
        if dimension_status not in {"PASS", *RESIZABLE_DIMENSION_STATUSES}:
            errors.append(f"{prefix}.dimension_status is not acceptable")
        if dimension_status in RESIZABLE_DIMENSION_STATUSES:
            needs_visual_qc = True
        ocr_status = str(slot.get("ocr_status", "")).upper()
        if ocr_status not in {"NOT_REQUIRED", "PASS", "OCR_UNAVAILABLE", "OCR_ERROR"}:
            errors.append(f"{prefix}.ocr_status is invalid or failed")
        if ocr_status in {"OCR_UNAVAILABLE", "OCR_ERROR"}:
            needs_visual_qc = True
            if slot.get("requires_visual_qc") is not True:
                errors.append(f"{prefix} {ocr_status} must set requires_visual_qc")
        if slot.get("requires_visual_qc") is True:
            needs_visual_qc = True
        plan_slot = plan_slots.get(slot_id)
        if plan_slots and plan_slot is None:
            errors.append(f"{prefix}.slot_id is not present in production_plan.json")
        if plan_slot is not None:
            expected_inspection = str(
                plan_slot.get("raw_output_path") or plan_slot.get("output_path") or ""
            ).strip()
            inspection_value = str(slot.get("inspection_path", "")).strip()
            if inspection_value != expected_inspection:
                errors.append(
                    f"{prefix}.inspection_path does not match production_plan.json: "
                    f"expected {expected_inspection}"
                )
            embedded_copy = plan_slot.get("image_embedded_copy", [])
            if not isinstance(embedded_copy, list):
                embedded_copy = []
            expected_copy = [
                str(value).strip()
                for value in embedded_copy
                if str(value).strip()
            ]
            if expected_copy and ocr_status == "NOT_REQUIRED":
                errors.append(
                    f"{prefix}.ocr_status cannot be NOT_REQUIRED when production_plan.json "
                    "declares image_embedded_copy"
                )
            if root is not None and inspection_value:
                inspection_path = (root / inspection_value).resolve()
                try:
                    inspection_path.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"{prefix}.inspection_path escapes project root")
                else:
                    if not inspection_path.is_file():
                        errors.append(f"{prefix}.inspection_path does not exist")
                    else:
                        if slot.get("sha256") != file_sha256(inspection_path):
                            errors.append(f"{prefix}.sha256 does not match the inspection file")
                        actual_dimensions = image_dimensions(inspection_path)
                        reported_dimensions = slot.get("dimensions")
                        reported_tuple = (
                            tuple(reported_dimensions)
                            if isinstance(reported_dimensions, list)
                            and len(reported_dimensions) == 2
                            else None
                        )
                        if actual_dimensions != reported_tuple:
                            errors.append(
                                f"{prefix}.dimensions do not match the inspection file"
                            )
                        target_size = plan_slot.get("target_size")
                        if (
                            actual_dimensions is not None
                            and isinstance(target_size, list)
                            and len(target_size) == 2
                            and all(
                                isinstance(value, int)
                                and not isinstance(value, bool)
                                and value > 0
                                for value in target_size
                            )
                        ):
                            target_tuple = (target_size[0], target_size[1])
                            if actual_dimensions == target_tuple:
                                expected_dimension_status = "PASS"
                                computed_ratio_error = 0.0
                            else:
                                actual_ratio = actual_dimensions[0] / actual_dimensions[1]
                                target_ratio = target_tuple[0] / target_tuple[1]
                                computed_ratio_error = abs(actual_ratio / target_ratio - 1.0) * 100
                                if (
                                    actual_dimensions[0] * target_tuple[1]
                                    == target_tuple[0] * actual_dimensions[1]
                                ):
                                    expected_dimension_status = "SAME_ASPECT_RESIZE_REQUIRED"
                                elif computed_ratio_error <= MAX_ASPECT_CORRECTION_PCT:
                                    expected_dimension_status = "SMALL_RATIO_CORRECTION_CANDIDATE"
                                else:
                                    expected_dimension_status = "FAIL"
                            if dimension_status != expected_dimension_status:
                                errors.append(
                                    f"{prefix}.dimension_status does not match actual dimensions "
                                    f"and production_plan.json target_size: expected "
                                    f"{expected_dimension_status}"
                                )
                            if expected_dimension_status == "SMALL_RATIO_CORRECTION_CANDIDATE":
                                reported_error = slot.get("aspect_error_pct")
                                if (
                                    isinstance(reported_error, bool)
                                    or not isinstance(reported_error, (int, float))
                                    or abs(float(reported_error) - computed_ratio_error) > 0.000001
                                ):
                                    errors.append(
                                        f"{prefix}.aspect_error_pct does not match the recomputed ratio error"
                                    )
                                if slot.get("requires_visual_qc") is not True:
                                    errors.append(
                                        f"{prefix} SMALL_RATIO_CORRECTION_CANDIDATE must set "
                                        "requires_visual_qc"
                                    )
                            elif expected_dimension_status == "FAIL":
                                errors.append(
                                    f"{prefix} actual ratio exceeds the "
                                    f"{MAX_ASPECT_CORRECTION_PCT:g}% BOUNDED_RATIO_EXPORT limit"
                                )
        slot_errors = slot.get("errors", [])
        if not isinstance(slot_errors, list) or slot_errors:
            errors.append(f"{prefix}.errors must be an empty list")
    report_errors = data.get("errors", [])
    if not isinstance(report_errors, list) or report_errors:
        errors.append("preflight_qc.json errors must be an empty list")
    if status == "PASS" and needs_visual_qc:
        errors.append("preflight_qc.json must use NEEDS_VISUAL_QC when OCR or ratio review remains")
    if status == "NEEDS_VISUAL_QC" and not needs_visual_qc:
        errors.append("preflight_qc.json NEEDS_VISUAL_QC has no routed slot")
    missing_plan_slots = sorted(set(plan_slots) - report_slot_ids)
    if missing_plan_slots:
        errors.append(
            "preflight_qc.json is missing production_plan.json slot(s): "
            + ", ".join(missing_plan_slots)
        )
    return {
        "valid": not errors,
        "path": path,
        "errors": errors,
        "status": status or None,
        "data": data,
    }


def validate_post_generation_qc(
    found: dict[str, list[Path]],
    root: Path,
    run_identity: str,
    production_plan: dict[str, Any] | None,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    missing_artifacts: list[str] = []
    project_root = root.resolve()
    plan_slots = (
        production_plan.get("slots", [])
        if isinstance(production_plan, dict)
        else []
    )
    expected_slots = {
        str(slot.get("slot_id", "")).strip().upper()
        for slot in plan_slots
        if isinstance(slot, dict) and str(slot.get("slot_id", "")).strip()
    }
    batch_slots = {
        "MAIN": {
            str(slot.get("slot_id", "")).strip().upper()
            for slot in plan_slots
            if isinstance(slot, dict)
            and str(slot.get("slot_id", "")).strip()
            and str(slot.get("group", "")).strip().upper() == "MAIN"
        },
        "APLUS": {
            str(slot.get("slot_id", "")).strip().upper()
            for slot in plan_slots
            if isinstance(slot, dict)
            and str(slot.get("slot_id", "")).strip()
            and str(slot.get("group", "")).strip().upper().startswith("APLUS")
        },
    }
    preflight_path = preflight.get("path")
    preflight_hash = (
        file_sha256(preflight_path)
        if isinstance(preflight_path, Path) and preflight_path.is_file()
        else None
    )

    def normalized_slot_list(value: Any, label: str) -> list[str]:
        if not isinstance(value, list):
            errors.append(f"{label} must be a list")
            return []
        normalized = [str(item).strip().upper() for item in value]
        if any(not item for item in normalized):
            errors.append(f"{label} must contain non-empty slot ids")
        if len(set(normalized)) != len(normalized):
            errors.append(f"{label} contains duplicate slot ids")
        return normalized

    profile_keys = {
        "QC_PRODUCT_STRUCTURE": "QC product structure",
        "QC_COPY_STYLE": "QC copy style",
        "QC_TECHNICAL": "QC technical",
    }
    profile_meta: dict[str, dict[str, Any]] = {}
    for profile_id, artifact_key in profile_keys.items():
        profile_path, profile_data, load_error = load_json_file(
            found.get(artifact_key, [])
        )
        filename = QC_PROFILE_FILES[profile_id]
        if load_error:
            missing_artifacts.append(f"preview/{filename}")
            errors.append(f"{filename}: {load_error}")
            continue
        assert profile_path is not None
        assert profile_data is not None
        prefix = filename
        if profile_data.get("version") != 1:
            errors.append(f"{prefix} version must be 1")
        if str(profile_data.get("run_identity", "")).strip() != run_identity:
            errors.append(f"{prefix} run_identity must match active_run.json")
        if str(profile_data.get("profile_id", "")).strip().upper() != profile_id:
            errors.append(f"{prefix} profile_id must be {profile_id}")
        if profile_data.get("preflight_sha256") != preflight_hash:
            errors.append(f"{prefix} preflight_sha256 must match current preflight_qc.json")
        reviewed = normalized_slot_list(
            profile_data.get("reviewed_slot_ids"),
            f"{prefix}.reviewed_slot_ids",
        )
        if set(reviewed) != expected_slots:
            errors.append(
                f"{prefix}.reviewed_slot_ids must exactly cover the production plan"
            )
        failed = normalized_slot_list(
            profile_data.get("failed_slot_ids"),
            f"{prefix}.failed_slot_ids",
        )
        if not set(failed).issubset(expected_slots):
            errors.append(
                f"{prefix}.failed_slot_ids contains a slot outside production_plan.json"
            )
        findings = profile_data.get("blocking_findings")
        finding_slots: list[str] = []
        if not isinstance(findings, list):
            errors.append(f"{prefix}.blocking_findings must be a list")
            findings = []
        for finding_index, finding in enumerate(findings, start=1):
            finding_prefix = f"{prefix}.blocking_findings[{finding_index}]"
            if not isinstance(finding, dict):
                errors.append(f"{finding_prefix} must be an object")
                continue
            finding_slot = str(finding.get("slot_id", "")).strip().upper()
            if not finding_slot or finding_slot not in expected_slots:
                errors.append(
                    f"{finding_prefix}.slot_id must exist in production_plan.json"
                )
            else:
                finding_slots.append(finding_slot)
            if not str(finding.get("finding", "")).strip():
                errors.append(f"{finding_prefix}.finding is required")
        if len(set(finding_slots)) != len(finding_slots):
            errors.append(f"{prefix}.blocking_findings contains duplicate slot ids")
        if set(failed) != set(finding_slots):
            errors.append(
                f"{prefix}.failed_slot_ids must match blocking_findings slot ids"
            )
        status = str(profile_data.get("status", "")).strip().upper()
        if failed and status != "FAIL":
            errors.append(f"{prefix} status must be FAIL when failed_slot_ids is non-empty")
        if not failed and status not in {"PASS", "PASS_WITH_NOTES"}:
            errors.append(f"{prefix} status must pass when no failed slots exist")
        profile_meta[profile_id] = {
            "path": profile_path,
            "sha256": file_sha256(profile_path),
            "failed_slot_ids": set(failed),
        }

    all_profile_ids = set(QC_PROFILE_FILES)
    profile_failures = {
        slot_id
        for meta in profile_meta.values()
        for slot_id in meta["failed_slot_ids"]
    }
    failed_slot_ids: set[str] = set()
    verdict_paths: dict[str, Path] = {}
    for batch, slots in batch_slots.items():
        if not slots:
            continue
        artifact_key = "MAIN QC verdict" if batch == "MAIN" else "APLUS QC verdict"
        verdict_path, verdict_data, load_error = load_json_file(
            found.get(artifact_key, [])
        )
        filename = QC_VERDICT_FILES[batch]
        if load_error:
            missing_artifacts.append(f"preview/{filename}")
            errors.append(f"{filename}: {load_error}")
            continue
        assert verdict_path is not None
        assert verdict_data is not None
        verdict_paths[batch] = verdict_path
        prefix = filename
        if verdict_data.get("version") != 1:
            errors.append(f"{prefix} version must be 1")
        if str(verdict_data.get("run_identity", "")).strip() != run_identity:
            errors.append(f"{prefix} run_identity must match active_run.json")
        if str(verdict_data.get("batch", "")).strip().upper() != batch:
            errors.append(f"{prefix} batch must be {batch}")
        if verdict_data.get("preflight_sha256") != preflight_hash:
            errors.append(f"{prefix} preflight_sha256 must match current preflight_qc.json")
        reviewed = normalized_slot_list(
            verdict_data.get("slot_ids"),
            f"{prefix}.slot_ids",
        )
        if set(reviewed) != slots:
            errors.append(f"{prefix}.slot_ids must exactly cover the {batch} batch")
        failed = normalized_slot_list(
            verdict_data.get("failed_slot_ids"),
            f"{prefix}.failed_slot_ids",
        )
        expected_failed = profile_failures.intersection(slots)
        if set(failed) != expected_failed:
            errors.append(
                f"{prefix}.failed_slot_ids must exactly merge the three QC profiles"
            )
        failed_slot_ids.update(failed)
        status = str(verdict_data.get("status", "")).strip().upper()
        if failed and status != "FAIL":
            errors.append(f"{prefix} status must be FAIL when failed_slot_ids is non-empty")
        if not failed and status not in {"PASS", "PASS_WITH_NOTES"}:
            errors.append(f"{prefix} status must pass when no failed slots exist")

        report_refs = verdict_data.get("profile_reports")
        referenced_profiles: set[str] = set()
        if not isinstance(report_refs, list):
            errors.append(f"{prefix}.profile_reports must be a list")
            report_refs = []
        for ref_index, report_ref in enumerate(report_refs, start=1):
            ref_prefix = f"{prefix}.profile_reports[{ref_index}]"
            if not isinstance(report_ref, dict):
                errors.append(f"{ref_prefix} must be an object")
                continue
            profile_id = str(report_ref.get("profile_id", "")).strip().upper()
            if profile_id not in all_profile_ids:
                errors.append(f"{ref_prefix}.profile_id is invalid")
                continue
            if profile_id in referenced_profiles:
                errors.append(f"{ref_prefix}.profile_id is duplicated")
            referenced_profiles.add(profile_id)
            meta = profile_meta.get(profile_id)
            expected_path = project_root / "preview" / QC_PROFILE_FILES[profile_id]
            reported_path = Path(str(report_ref.get("path", ""))).expanduser()
            if not reported_path.is_absolute():
                reported_path = project_root / reported_path
            if reported_path.resolve() != expected_path.resolve():
                errors.append(f"{ref_prefix}.path must reference {expected_path.name}")
            if meta is None or report_ref.get("sha256") != meta["sha256"]:
                errors.append(f"{ref_prefix}.sha256 must match the QC profile file")
        if referenced_profiles != all_profile_ids:
            errors.append(f"{prefix}.profile_reports must reference all three QC profiles")

        merged_findings = verdict_data.get("blocking_findings")
        merged_slots: set[str] = set()
        if not isinstance(merged_findings, list):
            errors.append(f"{prefix}.blocking_findings must be a list")
            merged_findings = []
        for finding_index, finding in enumerate(merged_findings, start=1):
            finding_prefix = f"{prefix}.blocking_findings[{finding_index}]"
            if not isinstance(finding, dict):
                errors.append(f"{finding_prefix} must be an object")
                continue
            slot_id = str(finding.get("slot_id", "")).strip().upper()
            profile_ids = {
                str(value).strip().upper()
                for value in finding.get("profile_ids", [])
                if str(value).strip()
            } if isinstance(finding.get("profile_ids"), list) else set()
            source_profiles = {
                profile_id
                for profile_id, meta in profile_meta.items()
                if slot_id in meta["failed_slot_ids"]
            }
            if slot_id not in expected_failed:
                errors.append(f"{finding_prefix}.slot_id is not a failed {batch} slot")
            else:
                merged_slots.add(slot_id)
            if profile_ids != source_profiles:
                errors.append(
                    f"{finding_prefix}.profile_ids must identify every blocking source profile"
                )
            findings_list = finding.get("findings")
            if (
                not isinstance(findings_list, list)
                or not findings_list
                or any(not str(value).strip() for value in findings_list)
            ):
                errors.append(f"{finding_prefix}.findings must be a non-empty list")
        if len(merged_slots) != len(merged_findings):
            errors.append(
                f"{prefix}.blocking_findings must contain one record per failed slot"
            )
        if merged_slots != expected_failed:
            errors.append(
                f"{prefix}.blocking_findings must merge every failed slot exactly once"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "missing_artifacts": sorted(set(missing_artifacts)),
        "failed_slot_ids": sorted(failed_slot_ids),
        "profile_count": len(profile_meta),
        "verdict_paths": verdict_paths,
    }


def expected_scheduler_recommendation(
    records: list[dict[str, Any]],
    run_identity: str,
) -> int:
    current_records = [
        record
        for record in records
        if record.get("run_identity") == run_identity
        and record.get("provider") == "image2"
    ]
    transport_errors = 0
    for record in reversed(current_records):
        status = str(record.get("status", "")).strip().upper()
        error_type = str(record.get("error_type", "")).strip().upper()
        if status in {"FAILED", "ERROR", "BLOCKED"} and (
            error_type in {"AUTH", "NETWORK", "RATE_LIMIT", "TIMEOUT", "TRANSPORT"}
            or record.get("transport_error") is True
        ):
            transport_errors += 1
            continue
        break
    return 1 if transport_errors >= 2 else 2 if transport_errors == 1 else 3


def validate_scheduler_state(
    paths: list[Path],
    root: Path,
    run_identity: str,
    ledger_paths: list[Path],
    production_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {
            "valid": False,
            "path": path,
            "errors": errors,
            "recommended_child_workers": None,
        }
    assert data is not None
    if data.get("version") != 1:
        errors.append("scheduler_state.json version must be 1")
    if data.get("policy") != "PHASE_BOUNDARY_SCHEDULER":
        errors.append("scheduler_state.json policy must be PHASE_BOUNDARY_SCHEDULER")
    if data.get("phase") != "IMAGE_GENERATION":
        errors.append("scheduler_state.json phase must be IMAGE_GENERATION")
    if str(data.get("run_identity", "")).strip() != run_identity:
        errors.append("scheduler_state.json run_identity does not match active_run.json")
    workers = data.get("recommended_child_workers")
    if not isinstance(workers, int) or not 1 <= workers <= 3:
        errors.append("scheduler_state.json recommended_child_workers must be 1..3")
    hard_max = data.get("hard_max_child_workers", 3)
    if hard_max != 3:
        errors.append("scheduler_state.json hard_max_child_workers must be 3")
    ledger_path = ledger_paths[0] if ledger_paths else None
    if ledger_path is None or not ledger_path.is_file():
        errors.append("scheduler_state.json cannot be verified without generation_ledger.jsonl")
    else:
        _, records, ledger_errors = read_jsonl([ledger_path])
        errors.extend(ledger_errors)
        current_count = sum(
            1 for record in records if record.get("run_identity") == run_identity
        )
        evidence_count = data.get("evidence_record_count")
        if (
            isinstance(evidence_count, bool)
            or not isinstance(evidence_count, int)
            or evidence_count < 0
            or evidence_count > current_count
        ):
            errors.append(
                "scheduler_state.json evidence_record_count must be a non-negative phase-boundary snapshot"
            )
        evidence_hash = data.get("evidence_ledger_sha256")
        if evidence_count and not re.fullmatch(r"[0-9a-f]{64}", str(evidence_hash or "")):
            errors.append(
                "scheduler_state.json evidence_ledger_sha256 is required for a non-empty snapshot"
            )
        expected_workers = expected_scheduler_recommendation(records, run_identity)
        if workers != expected_workers:
            errors.append(
                "scheduler_state.json recommendation does not match current transport-error recovery state: "
                f"expected {expected_workers}"
            )
    return {
        "valid": not errors,
        "path": path,
        "errors": errors,
        "recommended_child_workers": workers if isinstance(workers, int) else None,
        "data": data,
    }


def nested_values_present(value: Any) -> bool:
    if isinstance(value, dict):
        return any(nested_values_present(item) for item in value.values())
    if isinstance(value, list):
        return any(nested_values_present(item) for item in value)
    return value not in {None, "", False, 0}


def validate_final_manifest(paths: list[Path]) -> dict[str, Any]:
    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    if load_error:
        errors.append(load_error)
        return {"valid": False, "path": path, "errors": errors, "data": data}

    assert data is not None
    if str(data.get("status", "")).strip().upper() != "PASS":
        errors.append("production_manifest.json status must be PASS")

    for key, value in data.items():
        if (key == "missing" or key.startswith("missing_")) and nested_values_present(value):
            errors.append(f"production_manifest.json contains missing outputs in {key}")
    if nested_values_present(data.get("image2_rework_required")):
        errors.append("production_manifest.json still contains image2 rework")

    outputs = data.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("production_manifest.json outputs must contain at least one output record")
    elif path is not None:
        for index, output in enumerate(outputs, start=1):
            if not isinstance(output, dict):
                errors.append(f"production_manifest.json outputs[{index}] must be an object")
                continue
            output_path_value = output.get("path")
            expected_hash = str(output.get("sha256", "")).strip().lower()
            if not output_path_value:
                errors.append(f"production_manifest.json outputs[{index}].path is required")
                continue
            output_path = Path(str(output_path_value)).expanduser()
            if not output_path.is_absolute():
                output_path = path.parent.parent / output_path
            output_path = output_path.resolve()
            if not output_path.is_file():
                errors.append(f"production_manifest.json outputs[{index}] does not exist")
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                errors.append(f"production_manifest.json outputs[{index}].sha256 is invalid")
            elif file_sha256(output_path) != expected_hash:
                errors.append(f"production_manifest.json outputs[{index}] hash mismatch")

    return {"valid": not errors, "path": path, "errors": errors, "data": data}


def validate_agent_task_registry(
    paths: list[Path],
    root: Path,
    run_identity: str,
) -> dict[str, Any]:
    if not paths:
        return {
            "exists": False,
            "valid": True,
            "complete": True,
            "path": None,
            "errors": [],
            "pending_tasks": [],
            "failed_tasks": [],
            "task_count": 0,
        }

    path, data, load_error = load_json_file(paths)
    errors: list[str] = []
    pending_tasks: list[str] = []
    failed_tasks: list[str] = []
    if load_error:
        errors.append(f"agent_task_registry.json {load_error}")
        return {
            "exists": True,
            "valid": False,
            "complete": False,
            "path": path,
            "errors": errors,
            "pending_tasks": pending_tasks,
            "failed_tasks": failed_tasks,
            "task_count": 0,
        }

    assert data is not None
    if data.get("version") != 1:
        errors.append("agent_task_registry.json version must be 1")

    registry_identity = str(data.get("run_identity", "")).strip()
    if not registry_identity:
        errors.append("agent_task_registry.json must define run_identity")
    elif registry_identity != run_identity:
        errors.append(
            "agent_task_registry.json run_identity does not match active_run.json"
        )
    if run_identity != "legacy-unscoped":
        max_parallel_workers = data.get("max_parallel_workers")
        if max_parallel_workers != 3:
            errors.append(
                "agent_task_registry.json max_parallel_workers must declare the hard maximum 3"
            )

    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("agent_task_registry.json tasks must contain at least one dispatched task")
        tasks = []

    seen_task_ids: set[str] = set()
    seen_promoted_output_owners: dict[Path, str] = {}
    seen_report_path_owners: dict[Path, str] = {}
    seen_image_slot_owners: dict[str, str] = {}
    seen_allowed_write_owners: list[tuple[Path, str]] = []
    project_root = root.resolve()
    for index, task in enumerate(tasks, start=1):
        prefix = f"agent_task_registry.json tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix} must be an object")
            continue

        task_id = str(task.get("task_id", "")).strip()
        if not task_id:
            errors.append(f"{prefix}.task_id is required")
            task_id = f"tasks[{index}]"
        elif task_id in seen_task_ids:
            errors.append(f"{prefix}.task_id duplicates another task: {task_id}")
        seen_task_ids.add(task_id)

        role = str(task.get("role", "")).strip().upper()
        if role not in AGENT_TASK_ROLES:
            errors.append(
                f"{prefix}.role must be one of {', '.join(sorted(AGENT_TASK_ROLES))}"
            )
        thin_image_task = role == "IMAGE_WORKER"
        if run_identity != "legacy-unscoped" and not thin_image_task:
            estimated_seconds = task.get("estimated_seconds")
            if not isinstance(estimated_seconds, (int, float)) or estimated_seconds < 120:
                errors.append(
                    f"{prefix}.estimated_seconds must be at least 120 for delegated work"
                )
            if task.get("independent") is not True:
                errors.append(f"{prefix}.independent must be true for delegated work")
            if task.get("parallel_gain") is not True:
                errors.append(f"{prefix}.parallel_gain must be true for delegated work")
        if role == "IMAGE_WORKER":
            slot_id = str(task.get("slot_id", "")).strip().upper()
            if not slot_id:
                errors.append(f"{prefix}.slot_id is required for IMAGE_WORKER")
            else:
                existing_slot_owner = seen_image_slot_owners.get(slot_id)
                if existing_slot_owner is not None:
                    errors.append(
                        f"{prefix}.slot_id is already claimed by {existing_slot_owner}"
                    )
                else:
                    seen_image_slot_owners[slot_id] = task_id
        stage_value = str(task.get("stage", "")).strip().upper()
        if not stage_value:
            errors.append(f"{prefix}.stage is required")
        if not thin_image_task and not isinstance(task.get("depends_on"), list):
            errors.append(f"{prefix}.depends_on must be a list")
        allowed_write_paths = task.get("allowed_write_paths")
        resolved_allowed_paths: list[Path] = []
        if not isinstance(allowed_write_paths, list) or not allowed_write_paths:
            errors.append(f"{prefix}.allowed_write_paths must contain at least one path")
        else:
            for allowed_index, allowed_value in enumerate(allowed_write_paths, start=1):
                if not isinstance(allowed_value, str) or not allowed_value.strip():
                    errors.append(
                        f"{prefix}.allowed_write_paths[{allowed_index}] must be a non-empty path"
                    )
                    continue
                allowed_path = Path(allowed_value.strip()).expanduser()
                if not allowed_path.is_absolute():
                    allowed_path = project_root / allowed_path
                try:
                    allowed_path = allowed_path.resolve()
                    allowed_path.relative_to(project_root)
                except (OSError, ValueError):
                    errors.append(
                        f"{prefix}.allowed_write_paths[{allowed_index}] escapes project root"
                    )
                    continue
                for existing_path, existing_owner in seen_allowed_write_owners:
                    if existing_owner == task_id:
                        continue
                    paths_overlap = False
                    try:
                        allowed_path.relative_to(existing_path)
                        paths_overlap = True
                    except ValueError:
                        try:
                            existing_path.relative_to(allowed_path)
                            paths_overlap = True
                        except ValueError:
                            pass
                    if paths_overlap:
                        errors.append(
                            f"{prefix}.allowed_write_paths[{allowed_index}] overlaps path claimed by {existing_owner}"
                        )
                seen_allowed_write_owners.append((allowed_path, task_id))
                resolved_allowed_paths.append(allowed_path)

        status = str(task.get("status", "")).strip().upper()
        if status not in AGENT_TASK_STATUSES:
            errors.append(
                f"{prefix}.status must be one of {', '.join(sorted(AGENT_TASK_STATUSES))}"
            )
            continue

        generation_receipt = task.get("generation_receipt")
        if thin_image_task:
            if "required_report_path" in task:
                errors.append(
                    f"{prefix}.required_report_path is forbidden for THIN_IMAGE_WORKER"
                )
            if "promoted_output_paths" in task:
                errors.append(
                    f"{prefix}.promoted_output_paths is forbidden for DIRECT_UNIQUE_RAW_WRITE"
                )
            if len(resolved_allowed_paths) != 1:
                errors.append(
                    f"{prefix}.allowed_write_paths must contain exactly one raw image file"
                )
            elif (
                resolved_allowed_paths[0].suffix.lower() not in IMAGE_EXTENSIONS
                or not resolved_allowed_paths[0].is_relative_to(
                    project_root / "raw_generated"
                )
            ):
                errors.append(
                    f"{prefix}.allowed_write_paths must be one image inside raw_generated"
                )

            if generation_receipt is None:
                if status in {"VERIFIED", "FAILED"}:
                    errors.append(
                        f"{prefix} status {status} requires MINIMAL_GENERATION_RECEIPT"
                    )
                elif status in AGENT_TASK_PENDING_STATUSES:
                    pending_tasks.append(task_id)
                continue

            if not isinstance(generation_receipt, dict):
                errors.append(f"{prefix}.generation_receipt must be an object")
                continue

            receipt_task_id = str(generation_receipt.get("task_id", "")).strip()
            receipt_slot_id = str(generation_receipt.get("slot_id", "")).strip().upper()
            receipt_status = str(generation_receipt.get("status", "")).strip().upper()
            elapsed_ms = generation_receipt.get("elapsed_ms")
            if receipt_task_id != task_id:
                errors.append(
                    f"{prefix}.generation_receipt task_id must match registry task_id"
                )
            if receipt_slot_id != str(task.get("slot_id", "")).strip().upper():
                errors.append(
                    f"{prefix}.generation_receipt slot_id must match registry slot_id"
                )
            if finite_elapsed_ms(elapsed_ms, require_positive=True) is None:
                errors.append(
                    f"{prefix}.generation_receipt elapsed_ms must be positive"
                )

            if receipt_status in AGENT_REPORT_SUCCESS_STATUSES:
                if status != "VERIFIED":
                    errors.append(
                        f"{prefix} successful generation_receipt requires status VERIFIED"
                    )
                receipt_output_value = str(
                    generation_receipt.get("output_path", "")
                ).strip()
                if not receipt_output_value:
                    errors.append(
                        f"{prefix}.generation_receipt output_path is required"
                    )
                else:
                    receipt_output = Path(receipt_output_value).expanduser()
                    if not receipt_output.is_absolute():
                        receipt_output = project_root / receipt_output
                    try:
                        receipt_output = receipt_output.resolve()
                        receipt_output.relative_to(project_root)
                    except (OSError, ValueError):
                        errors.append(
                            f"{prefix}.generation_receipt output_path escapes project root"
                        )
                    else:
                        if not receipt_output.is_file():
                            errors.append(
                                f"{prefix}.generation_receipt output_path does not exist"
                            )
                        if receipt_output.suffix.lower() not in IMAGE_EXTENSIONS:
                            errors.append(
                                f"{prefix}.generation_receipt output_path must be an image"
                            )
                        if not receipt_output.is_relative_to(
                            project_root / "raw_generated"
                        ):
                            errors.append(
                                f"{prefix}.generation_receipt output_path must be inside raw_generated"
                            )
                        if resolved_allowed_paths and receipt_output not in resolved_allowed_paths:
                            errors.append(
                                f"{prefix}.generation_receipt output_path must match its unique allowed_write_paths file"
                            )
                        existing_owner = seen_promoted_output_owners.get(receipt_output)
                        if existing_owner is not None:
                            errors.append(
                                f"{prefix}.generation_receipt output_path is already claimed by {existing_owner}"
                            )
                        else:
                            seen_promoted_output_owners[receipt_output] = task_id
            elif receipt_status == "FAILED":
                if status != "FAILED":
                    errors.append(
                        f"{prefix} failed generation_receipt requires status FAILED"
                    )
                error_type = str(
                    generation_receipt.get("error_type", "")
                ).strip().upper()
                if error_type not in IMAGE2_FAILURE_ERROR_TYPES:
                    errors.append(
                        f"{prefix}.generation_receipt error_type must be standardized"
                    )
                if not str(generation_receipt.get("error_message", "")).strip():
                    errors.append(
                        f"{prefix}.generation_receipt error_message is required"
                    )
                failed_tasks.append(task_id)
            else:
                errors.append(
                    f"{prefix}.generation_receipt status must be successful or FAILED"
                )
            continue

        report_value = str(task.get("required_report_path", "")).strip()
        report_exists = False
        resolved_report_path: Path | None = None
        if not report_value:
            errors.append(f"{prefix}.required_report_path is required")
        else:
            report_path = Path(report_value).expanduser()
            if not report_path.is_absolute():
                report_path = project_root / report_path
            try:
                report_path = report_path.resolve()
                report_path.relative_to(project_root)
            except (OSError, ValueError):
                errors.append(f"{prefix}.required_report_path escapes project root")
            else:
                resolved_report_path = report_path
                report_exists = report_path.is_file()
                existing_report_owner = seen_report_path_owners.get(report_path)
                if existing_report_owner is not None:
                    errors.append(
                        f"{prefix}.required_report_path is already claimed by {existing_report_owner}"
                    )
                else:
                    seen_report_path_owners[report_path] = task_id

        if status in {"REPORTED", "VERIFIED"} and report_value and not report_exists:
            errors.append(f"{prefix} required report does not exist: {report_value}")

        if status == "VERIFIED" and report_exists and resolved_report_path is not None:
            try:
                report_data = json.loads(resolved_report_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{prefix} required report must be valid JSON: {exc}")
                report_data = None
            if not isinstance(report_data, dict):
                if report_data is not None:
                    errors.append(f"{prefix} required report root must be an object")
            else:
                report_task_id = str(report_data.get("task_id", "")).strip()
                if report_task_id != task_id:
                    errors.append(
                        f"{prefix} required report task_id must match registry task_id"
                    )
                report_status = str(report_data.get("status", "")).strip().upper()
                if report_status not in AGENT_REPORT_SUCCESS_STATUSES:
                    errors.append(
                        f"{prefix} required report status must be successful"
                    )
                checks = report_data.get("checks")
                if not isinstance(checks, list) or not checks:
                    errors.append(f"{prefix} required report checks must be a non-empty list")

                promoted_values = task.get("promoted_output_paths", [])
                if promoted_values is None:
                    promoted_values = []
                if not isinstance(promoted_values, list):
                    errors.append(f"{prefix}.promoted_output_paths must be a list when provided")
                    promoted_values = []
                resolved_promoted_paths: list[Path] = []
                for promoted_index, promoted_value in enumerate(promoted_values, start=1):
                    promoted_path = Path(str(promoted_value)).expanduser()
                    if not promoted_path.is_absolute():
                        promoted_path = project_root / promoted_path
                    try:
                        promoted_path = promoted_path.resolve()
                        promoted_path.relative_to(project_root)
                    except (OSError, ValueError):
                        errors.append(
                            f"{prefix}.promoted_output_paths[{promoted_index}] escapes project root"
                        )
                        continue
                    if not promoted_path.is_file():
                        errors.append(
                            f"{prefix}.promoted_output_paths[{promoted_index}] does not exist"
                        )
                        continue
                    lowered_promoted_parts = {part.lower() for part in promoted_path.parts}
                    if "workers" in lowered_promoted_parts and "outputs" in lowered_promoted_parts:
                        errors.append(
                            f"{prefix}.promoted_output_paths[{promoted_index}] must be outside worker staging"
                        )
                        continue
                    existing_owner = seen_promoted_output_owners.get(promoted_path)
                    if existing_owner is not None:
                        errors.append(
                            f"{prefix}.promoted_output_paths[{promoted_index}] is already claimed by {existing_owner}"
                        )
                        continue
                    seen_promoted_output_owners[promoted_path] = task_id
                    resolved_promoted_paths.append(promoted_path)

                actual_values = report_data.get("actual_output_paths")
                if not isinstance(actual_values, list) or not actual_values:
                    errors.append(
                        f"{prefix} required report actual_output_paths must be a non-empty list"
                    )
                    actual_values = []
                for output_index, output_value in enumerate(actual_values, start=1):
                    if not isinstance(output_value, str) or not output_value.strip():
                        errors.append(
                            f"{prefix} required report actual_output_paths[{output_index}] must be a path"
                        )
                        continue

                    output_path = Path(output_value.strip()).expanduser()
                    if not output_path.is_absolute():
                        output_path = project_root / output_path
                    try:
                        output_path = output_path.resolve()
                        output_path.relative_to(project_root)
                    except (OSError, ValueError):
                        errors.append(
                            f"{prefix} required report actual_output_paths[{output_index}] escapes project root"
                        )
                        continue

                    path_is_allowed = output_path == resolved_report_path
                    if not path_is_allowed:
                        for allowed_path in resolved_allowed_paths:
                            try:
                                output_path.relative_to(allowed_path)
                            except ValueError:
                                continue
                            path_is_allowed = True
                            break
                    if not path_is_allowed:
                        errors.append(
                            f"{prefix} required report actual_output_paths[{output_index}] is outside allowed_write_paths"
                        )

                    promoted_match = any(
                        promoted_path.name == output_path.name
                        for promoted_path in resolved_promoted_paths
                    )
                    if not output_path.is_file() and not promoted_match:
                        errors.append(
                            f"{prefix} required report actual_output_paths[{output_index}] does not exist and has no promoted output"
                        )

        if status in AGENT_TASK_PENDING_STATUSES:
            pending_tasks.append(task_id)
        elif status == "FAILED":
            failed_tasks.append(task_id)

    complete = not errors and not pending_tasks and not failed_tasks
    return {
        "exists": True,
        "valid": not errors,
        "complete": complete,
        "path": path,
        "errors": errors,
        "pending_tasks": pending_tasks,
        "failed_tasks": failed_tasks,
        "task_count": len(tasks),
    }


def style_branch(path: Path) -> str | None:
    value = match_text(path).lower().replace("\\", "/")
    patterns = {
        "A": [r"(?:^|[/_\- ])style[_\- ]?a(?:[/_\- ]|$)", r"风格[_\- ]?a"],
        "B": [r"(?:^|[/_\- ])style[_\- ]?b(?:[/_\- ]|$)", r"风格[_\- ]?b"],
        "C": [r"(?:^|[/_\- ])style[_\- ]?c(?:[/_\- ]|$)", r"风格[_\- ]?c"],
    }
    for branch, branch_patterns in patterns.items():
        if any(re.search(pattern, value) for pattern in branch_patterns):
            return branch
    return None


def white_reference_candidates(files: list[Path]) -> list[Path]:
    return [
        path
        for path in files
        if path.suffix.lower() in IMAGE_EXTENSIONS
        and has_any(match_text(path), WHITE_REFERENCE_MARKERS)
        and not is_quick_sample_path(path)
    ]


def created_since_run_start(path: Path, active_run: dict[str, Any]) -> bool:
    try:
        started = datetime.fromisoformat(str(active_run.get("created_at")))
    except ValueError:
        return True
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=started.tzinfo)
    except OSError:
        return False
    return modified >= started


def scan_project(root: Path, active_run: dict[str, Any] | None = None) -> dict[str, list[Path]]:
    global _MATCH_ROOTS
    previous = _MATCH_ROOTS
    match_roots = [root, root.resolve()]
    run_output_root = (active_run or {}).get("run_output_root_path")
    if isinstance(run_output_root, Path):
        match_roots.insert(0, run_output_root)
    _MATCH_ROOTS = tuple(match_roots)
    try:
        return scan_project_paths(root, active_run)
    finally:
        _MATCH_ROOTS = previous


def inventory_source_dirs(root: Path, active_run: dict[str, Any] | None) -> list[Path]:
    """Photo folders bootstrap_run.py inventoried for the current run."""
    if not active_run or not active_run.get("scoped"):
        return []
    try:
        inventory = json.loads((root / "source_inventory.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(inventory, dict) or inventory.get("run_identity") != active_run.get("run_identity"):
        return []
    folders: set[Path] = set()
    for item in inventory.get("images", []):
        if isinstance(item, dict) and (root / str(item.get("path", ""))).is_file():
            # Resolved like the scanner's active roots, so both sources compare equal.
            folders.add((root / str(item["path"])).resolve().parent)
    return sorted(folders)


def scan_project_paths(root: Path, active_run: dict[str, Any] | None) -> dict[str, list[Path]]:
    dirs, files = collect_paths(root, active_run=active_run)
    # The run's bootstrap inventory is the canonical photo list; keywords remain
    # the fallback for legacy projects without one.
    product_photos = find_product_photo_dirs(dirs, files) or inventory_source_dirs(root, active_run)

    white_reference_images = white_reference_candidates(files)
    # A scoped run that cannot see three references may have written them outside
    # active_paths; report those instead of letting the next action regenerate them.
    out_of_scope_white_references: list[Path] = []
    if active_run and active_run.get("scoped") and len(white_reference_images) < 3:
        in_scope = {path.resolve() for path in white_reference_images}
        _, project_files = collect_paths(root)
        out_of_scope_white_references = [
            Path(rel(root, path))
            for path in white_reference_candidates(project_files)
            if path.resolve() not in in_scope and created_since_run_start(path, active_run)
        ]

    style_samples_by_branch: dict[str, list[Path]] = {"A": [], "B": [], "C": []}
    for path in files:
        if path.suffix.lower() not in IMAGE_EXTENSIONS or is_quick_sample_path(path):
            continue
        # Formal production is commonly stored under the selected style folder.
        # Never misclassify canonical raw production outputs as style samples.
        if "_raw" in path.name.lower() or has_any(match_text(path), ["raw_generated", "main_1x1", "main_portrait", "a_plus_"]):
            continue
        if not has_any(match_text(path), ["style", "风格", "samples", "小样"]):
            continue
        branch = style_branch(path)
        if branch:
            style_samples_by_branch[branch].append(path)

    raw_images = [
        path
        for path in files
        if path.suffix.lower() in IMAGE_EXTENSIONS
        and "_raw" in path.name.lower()
        and not is_quick_sample_path(path)
        and any(part.lower() == "raw_generated" for part in path.parent.parts)
        and not (
            "workers" in {part.lower() for part in path.parts}
            and "outputs" in {part.lower() for part in path.parts}
        )
        # Do not exclude selected-style folders: formal production outputs may
        # legitimately live at style_samples/style_A/raw_generated/.
        and slot_from_raw_filename(path) is not None
    ]

    main_raw = [path for path in raw_images if slot_from_raw_filename(path) and not slot_from_raw_filename(path).startswith("AP")]
    aplus_raw = [path for path in raw_images if slot_from_raw_filename(path) and slot_from_raw_filename(path).startswith("AP")]

    competitor_materials = [
        path for path in dirs if has_any(match_text(path), COMPETITOR_MARKERS)
    ] + [
        path
        for path in files
        if path.suffix.lower() in COMPETITOR_EVIDENCE_EXTENSIONS
        and has_any(match_text(path), COMPETITOR_MARKERS)
    ]

    return {
        OUT_OF_SCOPE_WHITE_REFERENCES: out_of_scope_white_references,
        "product photo folder": product_photos,
        "production scope": exact_files(files, ["production_scope.json"]),
        "reference strategy": exact_files(files, ["reference_strategy.json"]),
        "reference fidelity lock": exact_files(files, ["reference_fidelity_lock.json"]),
        "product truth": text_files_named(files, ["01_product_truth", "product_truth", "产品事实"]),
        "white-background reference images": sorted(set(white_reference_images)),
        "reference plan/guide": text_files_named(
            files,
            ["02_reference_plan", "90_reference_selection_guide", "reference_plan", "reference_selection_guide"],
        ),
        "reference QC": text_files_named(files, ["91_reference_qc_report", "reference_qc_report"]),
        "reference manual approval": text_files_named(
            files,
            ["95_manual_approval", "manual_approval", "reference_approved", "人工确认", "已确认参考"],
        ),
        "product local detail locks": text_files_named(
            files,
            ["03_product_detail_locks", "product_detail_locks", "local_detail_locks", "局部细节锁"],
        ),
        "competitor materials": competitor_materials,
        "competitor display logic": text_files_named(
            files,
            ["竞品卖点", "展示逻辑", "competitor_logic", "competitor_display_logic"],
        ),
        "self-product selling-point brief": text_files_named(
            files,
            ["我的产品信息", "卖点优先级", "product_selling", "product_brief"],
        ),
        "product facts gate": text_files_named(
            files,
            [
                "product_facts_gate",
                "critical_product_facts",
                "产品事实门槛",
                "产品事实问题",
                "关键产品事实",
            ],
        ),
        "product facts confirmation": text_files_named(
            files,
            [
                "product_facts_confirmation",
                "confirmed_product_facts",
                "产品事实确认",
                "产品参数确认",
            ],
        ),
        "big-brand design cases": text_files_named(
            files,
            ["大牌设计案例", "版式库", "big_brand", "brand_design_case", "design_case", "layout_library"],
        ),
        "visual reference pool": exact_files(files, ["visual_reference_pool.json"]),
        "visual preference profile": exact_files(
            files, ["visual_preference_profile.json"]
        ),
        "style recommendation": text_files_named(
            files,
            ["风格推荐", "三个风格", "三种设计风格", "style_recommendation"],
        ),
        "style sample A": sorted(style_samples_by_branch["A"]),
        "style sample B": sorted(style_samples_by_branch["B"]),
        "style sample C": sorted(style_samples_by_branch["C"]),
        "generation ledger": exact_files(files, ["generation_ledger.jsonl"]),
        "scheduler state": exact_files(files, ["scheduler_state.json"]),
        "selected style": text_files_named(files, ["selected_style", "style_choice", "风格选择", "选中风格"]),
        "production handoff": text_files_named(files, ["production_handoff"]),
        "production context pack": text_files_named(files, ["production_context_pack"]),
        "production plan": exact_files(files, ["production_plan.json"]),
        "layout matrix": text_files_named(
            files,
            ["完整出图版式规划矩阵", "版式规划矩阵", "layout_matrix", "production_layout"],
        ),
        "prompt docs": text_files_named(files, ["full_production_prompts", "production_prompts"]),
        "prompt QC": text_files_named(files, ["prompt_qc_report"]),
        "agent task registry": exact_files(files, ["agent_task_registry.json"]),
        "main worker packet": text_files_named(files, ["main_batch_worker_packet"]),
        "aplus worker packet": text_files_named(files, ["aplus_batch_worker_packet"]),
        "main worker report": text_files_named(files, ["main_batch_worker_report"]),
        "aplus worker report": text_files_named(files, ["aplus_batch_worker_report"]),
        "main QC agent report": text_files_named(files, ["main_batch_qc_agent_report"]),
        "aplus QC agent report": text_files_named(files, ["aplus_batch_qc_agent_report"]),
        "main batch image QC": text_files_named(files, ["main_batch_image_qc_report", "main_image_qc_report"]),
        "aplus batch image QC": text_files_named(files, ["aplus_batch_image_qc_report", "aplus_image_qc_report"]),
        "deterministic preflight": exact_files(files, ["preflight_qc.json"]),
        "QC product structure": exact_files(files, ["qc_product_structure.json"]),
        "QC copy style": exact_files(files, ["qc_copy_style.json"]),
        "QC technical": exact_files(files, ["qc_technical.json"]),
        "MAIN QC verdict": exact_files(files, ["main_batch_qc_verdict.json"]),
        "APLUS QC verdict": exact_files(files, ["aplus_batch_qc_verdict.json"]),
        "finished-image QC": [
            path
            for path in text_files_named(files, ["image_qc_report"])
            if not is_quick_sample_path(path)
            and not has_any(
                path.name,
                ["main_batch_image_qc_report", "aplus_batch_image_qc_report"],
            )
        ],
        "raw generated images": sorted(raw_images),
        "main raw generated images": sorted(main_raw),
        "aplus raw generated images": sorted(aplus_raw),
        "generation checkpoint": text_files_named(files, ["generation_checkpoint"]),
        "partial manifest": partial_manifest_files(files),
        "final manifest": final_manifest_files(files),
        "quick sample artifacts": [path for path in files if is_quick_sample_path(path)],
    }


def present(found: dict[str, list[Path]], key: str) -> bool:
    return bool(found.get(key))


def slot_from_raw_filename(path: Path) -> str | None:
    name = path.stem.lower()
    patterns = [
        (r"^main_(\d{2})_raw$", "M{n}"),
        (r"^main_portrait_(\d{2})_raw$", "MP{n}"),
        (r"^aplus_basic_(\d{2})_raw$", "APB{n}"),
        (r"^aplus_premium_desktop_(\d{2})(?:_?s(\d+))?_raw$", "APD{n}{slide}"),
        (r"^aplus_premium_mobile_(\d{2})(?:_?s(\d+))?_raw$", "APM{n}{slide}"),
    ]
    for pattern, template in patterns:
        match = re.match(pattern, name)
        if not match:
            continue
        number = match.group(1)
        slide_value = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        slide = f"S{slide_value}" if slide_value else ""
        return template.format(n=number, slide=slide)
    return None


def slot_from_output_filename(filename: str) -> str | None:
    name = Path(filename).stem.lower()
    patterns = [
        (r"^main_(\d{2})_1x1$", "M{n}"),
        (r"^main_portrait_(\d{2})_\d+x\d+$", "MP{n}"),
        (r"^aplus_basic_(\d{2})_\d+x\d+$", "APB{n}"),
        (r"^aplus_premium_desktop_(\d{2})(?:_?s(\d+))?_\d+x\d+$", "APD{n}{slide}"),
        (r"^aplus_premium_mobile_(\d{2})(?:_?s(\d+))?_\d+x\d+$", "APM{n}{slide}"),
    ]
    for pattern, template in patterns:
        match = re.match(pattern, name)
        if not match:
            continue
        number = match.group(1)
        slide_value = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        slide = f"S{slide_value}" if slide_value else ""
        return template.format(n=number, slide=slide)
    return None


def parse_expected_slots(layout_files: list[Path]) -> list[str]:
    slots: list[str] = []
    seen: set[str] = set()
    for path in layout_files:
        for line in read_text(path).splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip().strip("`") for cell in stripped.strip("|").split("|")]
            if not cells:
                continue
            slot = cells[0]
            if SLOT_RE.match(slot) and slot not in seen:
                slots.append(slot)
                seen.add(slot)
    return slots


def completed_slots_from_partial_manifests(manifest_files: list[Path]) -> list[str]:
    completed: list[str] = []
    seen: set[str] = set()
    keys = [
        "completed_main_images",
        "completed_premium_desktop",
        "completed_premium_mobile",
        "completed_basic_aplus",
        "completed_basic",
    ]
    for path in manifest_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for key in keys:
            for filename in data.get(key, []) or []:
                slot = slot_from_output_filename(str(filename))
                if slot and slot not in seen:
                    completed.append(slot)
                    seen.add(slot)
    return completed


def resume_hint_from_checkpoints(checkpoint_files: list[Path]) -> str | None:
    for path in sorted(checkpoint_files, reverse=True):
        text = read_text(path)
        resume_start = text.lower().find("suggested resume order")
        search_text = text[resume_start:] if resume_start >= 0 else text
        for match in re.finditer(r"`([A-Z]{1,5}\d{2}(?:S\d+)?)`", search_text):
            return match.group(1)
    return None


def slot_progress(found: dict[str, list[Path]]) -> dict[str, Any]:
    expected = parse_expected_slots(found.get("layout matrix", []))
    completed: list[str] = []
    completed_seen: set[str] = set()

    for path in sorted(found.get("raw generated images", [])):
        slot = slot_from_raw_filename(path)
        if slot and slot not in completed_seen:
            completed.append(slot)
            completed_seen.add(slot)

    # Explicit manifests may use custom filenames; the canonical plan is their identity map.
    for plan_path in found.get("production plan", []):
        _, plan, error = load_json_file([plan_path])
        if error or not isinstance(plan, dict) or not isinstance(plan.get("slots"), list):
            continue
        raw_root = (plan_path.parent / "raw_generated").resolve()
        for row in plan["slots"]:
            if not isinstance(row, dict):
                continue
            slot = str(row.get("slot_id", "")).strip()
            value = row.get("raw_output_path")
            if slot not in expected or not isinstance(value, str) or not value.strip():
                continue
            raw_path = Path(value)
            if raw_path.is_absolute():
                continue
            raw_path = (plan_path.parent / raw_path).resolve()
            if raw_path.parent != raw_root or raw_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if raw_path.is_file() and slot not in completed_seen:
                completed.append(slot)
                completed_seen.add(slot)

    for slot in completed_slots_from_partial_manifests(found.get("partial manifest", [])):
        if slot not in completed_seen:
            completed.append(slot)
            completed_seen.add(slot)

    blocked = [slot for slot in expected if slot not in completed_seen]
    resume_hint = resume_hint_from_checkpoints(found.get("generation checkpoint", []))
    if resume_hint in blocked:
        blocked = [resume_hint] + [slot for slot in blocked if slot != resume_hint]

    expected_main = [slot for slot in expected if not slot.startswith("AP")]
    expected_aplus = [slot for slot in expected if slot.startswith("AP")]
    remaining_main = [slot for slot in blocked if not slot.startswith("AP")]
    remaining_aplus = [slot for slot in blocked if slot.startswith("AP")]

    return {
        "expected_slots": expected,
        "expected_main_slots": expected_main,
        "expected_aplus_slots": expected_aplus,
        "completed_slots": completed,
        "blocked_slots": blocked,
        "remaining_main_slots": remaining_main,
        "remaining_aplus_slots": remaining_aplus,
        "next_slot": blocked[0] if blocked else None,
    }


def production_started(found: dict[str, list[Path]]) -> bool:
    return any(
        present(found, key)
        for key in [
            "layout matrix",
            "prompt docs",
            "prompt QC",
            "raw generated images",
            "main batch image QC",
            "aplus batch image QC",
            "finished-image QC",
            "final manifest",
        ]
    )


def context_pack_status(
    found: dict[str, list[Path]], selected_style: str, stage: str
) -> str:
    if not selected_style.strip():
        return (
            "waiting_for_style_choice"
            if stage in {"STYLE_SAMPLES", "STYLE_CHOICE"}
            else "not_applicable_before_style_choice"
        )
    has_handoff = present(found, "production handoff")
    has_context = present(found, "production context pack")
    if has_handoff and has_context:
        return "production_started" if production_started(found) else "ready"
    return "needs_context_pack_files"


def selected_style_from_files(found: dict[str, list[Path]]) -> str:
    paths = found.get("selected style", [])
    if not paths:
        return ""

    def sort_key(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    for path in sorted(paths, key=sort_key, reverse=True):
        text = read_text(path)
        upper = text.upper()
        status_match = re.search(r"(?im)^\s*(?:SELECTED STYLE|STYLE|风格|选中风格)\s*[:：]\s*([ABC])\b", text)
        if status_match:
            return status_match.group(1).upper()
        if re.search(r"\bSTYLE\s*A\b|风格\s*A", upper):
            return "A"
        if re.search(r"\bSTYLE\s*B\b|风格\s*B", upper):
            return "B"
        if re.search(r"\bSTYLE\s*C\b|风格\s*C", upper):
            return "C"
    return ""


def determine_stage(
    found: dict[str, list[Path]],
    selected_style: str,
    progress: dict[str, Any],
    scope: dict[str, Any],
    reference_strategy: dict[str, Any],
    reference_fidelity_lock: dict[str, Any],
    visual_preference: dict[str, Any],
    require_visual_preference: bool,
    style_sample_ledger: dict[str, Any],
    production_plan: dict[str, Any],
    scheduler_state: dict[str, Any],
    preflight: dict[str, Any],
    post_generation_qc: dict[str, Any],
    agent_task_registry: dict[str, Any],
) -> tuple[str, str, list[str], str, str]:
    if not present(found, "product photo folder"):
        return (
            "INIT",
            "Project initialization",
            ["real product photo folder"],
            "Real product photos are not yet located.",
            "Ask for or locate the real product photo folder, then refresh the state.",
        )

    if not scope["valid"]:
        missing = ["valid production_scope.json"]
        missing.extend(scope["errors"])
        return (
            "SCOPE_CONFIRMATION",
            "Production scope confirmation",
            missing,
            "Actual main-image/A+ counts or formats are missing or invalid.",
            "Ask all missing deliverable counts, ratios, A+ type, Premium module count, and desktop/mobile image counts in one message; then atomically write production_scope.json. Use DEFERRED_TO_LAYOUT_MATRIX when page-display logic is not ready.",
        )

    if not reference_strategy["valid"]:
        missing = ["valid reference_strategy.json"]
        missing.extend(reference_strategy["errors"])
        return (
            "REFERENCE_ASSESSMENT",
            "Reference strategy assessment",
            missing,
            "The real product photos have not been classified as DIRECT_SOURCE or MINIMAL_LIBRARY.",
            "Visually assess source quality and write reference_strategy.json with the selected real source paths.",
        )

    if not reference_fidelity_lock["valid"]:
        return (
            "REFERENCE_FIDELITY_LOCK",
            "Pre-generation reference fidelity lock",
            ["valid reference_fidelity_lock.json", *reference_fidelity_lock["errors"]],
            "The chosen source paths are known, but their structural must-preserve and forbidden-drift constraints are not hash-bound yet.",
            "Write reference_fidelity_lock.json from the selected source files before any white-background image generation.",
        )

    white_reference_count = len(found.get("white-background reference images", []))
    if white_reference_count < 3:
        missing = [f"at least 3 white-background reference images generated from photographed source images ({white_reference_count}/3 found)"]
        next_action = "Generate at least three white-background references with DIRECT_IMAGE_INPUT; use VISUAL_CONTEXT_RELAY only as fallback, then run reference QC."
        outside = found.get(OUT_OF_SCOPE_WHITE_REFERENCES, [])
        if outside:
            listed = ", ".join(path.as_posix() for path in outside[:3])
            missing.append(
                f"{len(outside)} white-background reference image(s) created since this run started "
                f"are outside active_run.json active_paths: {listed}"
            )
            next_action = (
                "Do not regenerate them: move them under run_output_root or register their folder with "
                "bootstrap_run.py --add-active-path <folder>, then refresh the state."
            )
        return (
            "REFERENCE_LIBRARY_BUILD",
            "White-background reference library",
            missing,
            "The workflow must create a white-background reference library from the product photos before product facts, competitor research, style samples, or formal production.",
            next_action,
        )

    reference_qc_status = report_status(found.get("reference QC", []))
    if reference_qc_status not in {"PASS", "PASS_WITH_NOTES"}:
        if reference_qc_status == "FAIL":
            reason = "Reference QC failed; only failed white-background references or local details should be revised."
            action = "Revise the failed white-background references, rerun QC, and stop after two failed rounds."
        else:
            reason = "White-background reference images exist, but passing automated QC is missing."
            action = "Run automated reference QC and record PASS or PASS_WITH_NOTES."
        return (
            "REFERENCE_QC",
            "Reference QC",
            ["91_reference_qc_report.md with PASS or PASS_WITH_NOTES"],
            reason,
            action,
        )

    approval_status = confirmation_status(found.get("reference manual approval", []))
    if approval_status != "PASS":
        reason = (
            "The reference approval file explicitly rejects or blocks the current library."
            if approval_status == "FAIL"
            else "The generated white-background reference set still needs explicit user approval."
        )
        return (
            "REFERENCE_APPROVAL",
            "Reference manual approval",
            ["95_manual_approval.md with Status: APPROVED"],
            reason,
            "Show the approved candidates and ask the user to approve or give correction notes.",
        )

    missing_truth: list[str] = []
    if not present(found, "product truth"):
        missing_truth.append("01_product_truth.md")
    if not present(found, "product local detail locks"):
        missing_truth.append("03_product_detail_locks.md")
    if missing_truth:
        return (
            "PRODUCT_DETAIL_LOCKS",
            "Product truth and local detail locks",
            missing_truth,
            "Product truth or high-risk local details are not yet locked.",
            "Create product truth and local detail locks from real source photos and confirmed user facts.",
        )

    if not present(found, "competitor display logic"):
        missing = ["competitor display-logic brief"]
        if not present(found, "competitor materials"):
            missing.append("competitor image/A+ material folder")
        return (
            "COMPETITOR_RESEARCH",
            "Product-specific competitor research",
            missing,
            "This product still needs its own competitor display-logic analysis.",
            "Run amazon-competitor-creative-research for the current product.",
        )

    if not present(found, "self-product selling-point brief"):
        return (
            "PRODUCT_BRIEF",
            "Self-product selling-point priority",
            ["self-product selling-point priority brief"],
            "The current product facts and selling-point priorities are not normalized.",
            "Run amazon-product-selling-point-brief without inventing missing facts.",
        )

    facts_status = confirmation_status(found.get("product facts confirmation", []))
    if facts_status != "PASS":
        missing: list[str] = []
        if not present(found, "product facts gate"):
            missing.append("dynamic product_facts_gate.md")
        missing.append("product_facts_confirmation.md with CONFIRMED, APPROVED, PASS, or NO_BLOCKING_MISSING_FACTS")
        if facts_status == "FAIL":
            reason = "Product facts confirmation is blocked or rejected."
            action = "Resolve the blocked product facts, revise the product brief if needed, and write a passing product_facts_confirmation.md."
        elif not present(found, "product facts gate"):
            reason = "The self-product brief exists, but category-specific critical product facts have not been gated."
            action = "Create product_facts_gate.md from the current product category, competitor logic, and product brief; ask only category-critical missing facts."
        else:
            reason = "The dynamic product facts gate exists, but user/source confirmation is still missing."
            action = "Ask the user to fill or approve product_facts_gate.md, then write product_facts_confirmation.md before big-brand research or style work."
        return (
            "PRODUCT_FACTS_GATE",
            "Dynamic product facts confirmation",
            missing,
            reason,
            action,
        )

    if not present(found, "big-brand design cases"):
        return (
            "BIG_BRAND_RESEARCH",
            "Current big-brand design case research",
            ["current product-specific big-brand design case library"],
            "Current design-leading references are missing for this product.",
            (
                "Search visual and layout purposes separately, retrieve applicable curated favorites, "
                "and add a small useful shortlist of fresh traceable cases without a numerical quota."
                if visual_preference.get("discovery_contract_version") == 2
                else "Research 5-10 strong current category-relevant cases before style recommendation."
            ),
        )

    if require_visual_preference and not visual_preference["valid"]:
        if visual_preference.get("discovery_contract_version") == 2:
            pool = visual_preference.get("pool_data") or {}
            research_required = pool.get("status") == "RESEARCH_REQUIRED" or not pool.get("samples")
            if research_required:
                action = (
                    "Search by visual/layout purpose, reuse qualified favorites and add new cases. "
                    "Honor whole-batch or partial replacement, preserve the retained sample ids, "
                    "change the search plan and show simple like/neutral/dislike controls. "
                    "Do not ask for per-image reasons or generate comparison images."
                )
            elif pool.get("status") == "PENDING_RATING":
                action = (
                    "Show the purpose-specific like/neutral/dislike rater and whole-batch/partial "
                    "replacement buttons. The user supplies no required written reasons."
                )
            else:
                action = (
                    "Validate the submitted simple ratings and derive the approved preference profile. "
                    "If either purpose lacks a liked anchor, search again; do not generate comparison images."
                )
            return (
                "VISUAL_PREFERENCE_CALIBRATION", "Purpose-based reference discovery",
                ["valid stable visual_reference_pool.json v2", "approved visual_preference_profile.json",
                 *visual_preference["errors"]],
                "Reference discovery, replacement or simple ratings are still pending.", action,
            )
        return (
            "VISUAL_PREFERENCE_CALIBRATION",
            "Two-axis visual preference calibration",
            [
                "valid visual_reference_pool.json",
                "approved visual_preference_profile.json",
                *visual_preference["errors"],
            ],
            "The design references have not yet produced a traceable, approved visual system and layout system.",
            "Curate 8-12 qualified selling-design cards from the fixed source policy (or 6-12 with a documented SPARSE_CATEGORY reason), collect separate visual/layout ratings, run a controlled pairwise round only if needed, and approve the hash-bound hybrid recipe.",
        )

    if not present(found, "style recommendation"):
        return (
            "STYLE_RECOMMENDATION",
            "Three Style Specs",
            ["three product-driven style recommendations"],
            "The project has not defined three comparable style directions.",
            "Run amazon-creative-style-sampler in recommendation mode; do not generate images yet.",
        )

    missing_branches = [
        branch
        for branch in ["A", "B", "C"]
        if not present(found, f"style sample {branch}")
    ]
    if missing_branches:
        return (
            "STYLE_SAMPLES",
            "Style representative samples",
            [f"one representative sample for style {branch}" for branch in missing_branches],
            "The three styles are not yet represented by one comparable image each.",
            "Generate the same representative slot once for each missing style branch; append one successful image2 record per output to generation_ledger.jsonl.",
        )

    if not style_sample_ledger["valid"]:
        return (
            "STYLE_SAMPLES",
            "Style sample image2 provenance",
            ["valid generation_ledger.jsonl evidence for style A, B, and C", *style_sample_ledger["errors"]],
            "Style-named files exist, but file presence alone does not prove image2 generation or exact reference use.",
            "Record or repair image2 provenance for each A/B/C sample; do not ask for style choice until output and reference hashes match.",
        )

    if not selected_style.strip():
        return (
            "STYLE_CHOICE",
            "Style choice",
            ["selected style A, B, or C"],
            "All three representative samples exist, but the user has not selected the production style.",
            "Ask the user to choose one style. Do not start formal production until a style is selected.",
        )

    if not present(found, "production handoff") or not present(found, "production context pack"):
        missing: list[str] = []
        if not present(found, "production handoff"):
            missing.append("production_handoff.md")
        if not present(found, "production context pack"):
            missing.append("production_context_pack.md")
        return (
            "CONTEXT_PACK_PREP",
            "Compact production context preparation",
            missing,
            "The selected style is known, but the compact production context files are incomplete.",
            "Write compact context files from production_scope.json, refresh state, and continue automatically in the same task.",
        )

    if not production_plan["valid"]:
        return (
            "PRODUCTION_PLAN",
            "Canonical production plan",
            ["valid approved production_plan.json", *production_plan["errors"]],
            "Derived layout, prompts, worker packets, registry scaffolding, and preflight specifications need one canonical source.",
            "Write production_plan.json once, then run derive_production_artifacts.py; do not hand-maintain duplicate slot facts.",
        )

    if not present(found, "layout matrix"):
        return (
            "LAYOUT_MATRIX",
            "Selected-style layout matrix",
            ["full production layout matrix"],
            "Formal production cannot write prompts before the complete slot matrix.",
            "Create the complete layout matrix from production_scope.json.",
        )

    if premium_carousel_assignment_is_deferred(scope):
        return (
            "LAYOUT_MATRIX",
            "Premium A+ carousel assignment",
            ["resolved Premium A+ carousel assignment in production_scope.json"],
            "The page-display matrix exists, but Premium A+ carousel placement is still deferred.",
            "Decide carousel modules and slide counts from the page-display logic, then set "
            "carousel_assignment_status to RESOLVED before prompt writing.",
        )

    if not present(found, "prompt docs"):
        return (
            "PROMPT_WRITING",
            "Prompt writing",
            ["full_production_prompts.md"],
            "Production prompts are missing.",
            "Write prompts from the approved matrix and selected references.",
        )

    prompt_qc_status = report_status(found.get("prompt QC", []))
    if prompt_qc_status not in {"PASS", "PASS_WITH_NOTES"}:
        reason = (
            "Prompt QC failed; fix the source matrix, prompt, or reference selection before generation."
            if prompt_qc_status == "FAIL"
            else "Prompts exist, but passing prompt QC is missing."
        )
        return (
            "PROMPT_QC",
            "Prompt QC",
            ["prompts/prompt_qc_report.md with PASS or PASS_WITH_NOTES"],
            reason,
            "Run prompt QC and revise only the failed matrix/prompt/reference-selection items.",
        )

    if not scheduler_state["valid"]:
        return (
            "SCHEDULER_SETUP",
            "Phase-boundary image2 scheduler",
            ["valid PHASE_BOUNDARY_SCHEDULER state", *scheduler_state["errors"]],
            "Prompt QC passed, but formal generation has no phase-boundary three-lane authorization.",
            "Run adaptive_scheduler.py once before generation. Keep three lanes unless an actual transport error requires temporary recovery; successful image latency does not trigger recomputation.",
        )
    scheduled_workers = scheduler_state["recommended_child_workers"]

    if agent_task_registry["exists"] and not agent_task_registry["valid"]:
        return (
            "AGENT_TASK_VERIFICATION",
            "Agent task dispatch contract",
            list(agent_task_registry["errors"]),
            "The live task registry violates delegation gain, independence, path, identity, or report constraints.",
            "Fix or cancel invalid task entries before more formal generation; tasks below 120 seconds stay controller-direct.",
        )

    expected_main = progress["expected_main_slots"]
    expected_aplus = progress["expected_aplus_slots"]
    remaining_main = progress["remaining_main_slots"]
    remaining_aplus = progress["remaining_aplus_slots"]

    if not expected_main and not expected_aplus:
        return (
            "LAYOUT_MATRIX",
            "Layout matrix slot validation",
            ["canonical slot rows such as M01, M02, APB01, APD01, or APM01"],
            "The layout matrix exists but no production slots can be parsed.",
            "Fix the matrix slot IDs before any image generation.",
        )

    unified_remaining = remaining_main + remaining_aplus
    if unified_remaining:
        completed_count = (
            len(expected_main)
            + len(expected_aplus)
            - len(unified_remaining)
        )
        return (
            "IMAGE_GENERATION" if completed_count == 0 else "IMAGE_GENERATION_PARTIAL",
            "Three-lane raw generation queue",
            unified_remaining,
            "Prompt QC passed. NO_SMOKE_GATES keeps every independent MAIN and A+ slot ready; finished-image QC waits until all raw outputs exist.",
            f"Keep {scheduled_workers} thin IMAGE_WORKER lane(s) filled from one unified queue and refill on completion. Each worker only calls image2 and returns a MINIMAL_GENERATION_RECEIPT.",
        )

    if not preflight["valid"]:
        return (
            "DETERMINISTIC_PREFLIGHT",
            "Deterministic whole-set preflight",
            ["preview/preflight_qc.json with PASS or NEEDS_VISUAL_QC", *preflight["errors"]],
            "All raw slots exist, so the generation phase is closed; cheap file, hash, dimension, ratio, and OCR checks now run once for the whole set.",
            f"Run preflight_qc.py once. Same-aspect raws and ratio errors <={MAX_ASPECT_CORRECTION_PCT:g}% become visual-review resize candidates; larger errors return the slot to image2. OCR_UNAVAILABLE routes to visual QC and never passes copy.",
        )

    if not post_generation_qc["valid"]:
        missing_qc = list(post_generation_qc["missing_artifacts"])
        missing_qc.extend(post_generation_qc["errors"])
        return (
            "IMAGE_QC",
            "Post-generation three-profile QC",
            missing_qc,
            "All raw images and deterministic preflight evidence exist, but the machine-readable three-profile QC gate is incomplete or inconsistent.",
            "Dispatch exactly three read-only QC profiles concurrently: product truth/structure, copy/style, and aspect/dimensions/technical. Then write hash-bound MAIN/A+ verdict JSON files that merge every blocking finding.",
        )

    if post_generation_qc["failed_slot_ids"]:
        return (
            "IMAGE_GENERATION_PARTIAL",
            "Failed-slot-only rework queue",
            post_generation_qc["failed_slot_ids"],
            "Post-generation QC found blocking defects; passing raw files stay locked and untouched.",
            "Queue only the failed slot ids for thin-worker image2 rework, then rerun preflight and the affected QC profiles.",
        )

    if not agent_task_registry["complete"]:
        missing = list(agent_task_registry["errors"])
        missing.extend(
            f"controller verification for agent task {task_id}"
            for task_id in agent_task_registry["pending_tasks"]
        )
        missing.extend(
            f"successful rework or explicit cancellation for failed agent task {task_id}"
            for task_id in agent_task_registry["failed_tasks"]
        )
        return (
            "AGENT_TASK_VERIFICATION",
            "Agent task report verification",
            missing,
            "A dispatched subagent task is still pending, failed, or missing a controller-verified report.",
            "For IMAGE_WORKER tasks, verify direct-raw MINIMAL_GENERATION_RECEIPT records; for non-image tasks, verify their scoped reports. Rework or cancel failed tasks explicitly.",
        )

    final_manifest = validate_final_manifest(found.get("final manifest", []))
    if not final_manifest["valid"]:
        return (
            "FINAL_EXPORT",
            "Final deterministic export",
            ["passing preview/production_manifest.json", *final_manifest["errors"]],
            "All requested batches passed QC, but the final export manifest is missing or invalid.",
            "Run deterministic export; write a partial manifest on failure and a PASS final manifest only after every output is verified.",
        )

    return (
        "COMPLETE",
        "Complete",
        [],
        "",
        "Review final outputs; ask before any optional visual-impact-only generation.",
    )


def completed_artifacts(found: dict[str, list[Path]]) -> list[str]:
    return [
        key
        for key, paths in found.items()
        if paths and key not in DIAGNOSTIC_FOUND_KEYS
    ]


def current_batch_from_stage(stage_label: str, next_action: str) -> str | None:
    text = f"{stage_label} {next_action}".upper()
    if "MAIN/APLUS" in text or "MAIN/A+" in text:
        return "MAIN_AND_APLUS"
    if "MAIN_BATCH" in text:
        return "MAIN_BATCH"
    if "APLUS_BATCH" in text:
        return "APLUS_BATCH"
    return None


def is_human_blocked(stage: str, found: dict[str, list[Path]]) -> bool:
    if stage in {
        "INIT",
        "SCOPE_CONFIRMATION",
        "REFERENCE_APPROVAL",
        "PRODUCT_FACTS_GATE",
        "VISUAL_PREFERENCE_CALIBRATION",
        "STYLE_CHOICE",
    }:
        return True
    if stage == "COMPETITOR_RESEARCH" and not present(found, "competitor materials"):
        return True
    return False


def build_state(
    root: Path,
    found: dict[str, list[Path]],
    selected_style: str,
    active_run: dict[str, Any],
) -> dict[str, Any]:
    selected_style = selected_style.strip().upper() or selected_style_from_files(found)
    progress = slot_progress(found)
    scope = validate_production_scope(found.get("production scope", []))
    reference_strategy = validate_reference_strategy(found.get("reference strategy", []))
    reference_fidelity_lock = validate_reference_fidelity_lock(
        found.get("reference fidelity lock", []),
        root,
        str(active_run.get("run_identity", "")),
        reference_strategy,
    )
    visual_preference = validate_visual_preference_bundle(
        found.get("visual reference pool", []),
        found.get("visual preference profile", []),
        str(active_run.get("run_identity", "")),
        root,
        found.get("generation ledger", []),
        active_run.get("workflow_version"),
    )
    require_visual_preference = visual_preference_required(active_run, found)
    style_sample_ledger = validate_style_sample_ledger(
        found.get("generation ledger", []),
        root,
        str(active_run.get("run_identity", "")),
        {
            branch: found.get(f"style sample {branch}", [])
            for branch in ("A", "B", "C")
        },
        visual_preference.get("profile_path"),
        require_visual_preference,
    )
    production_plan = validate_production_plan(
        found.get("production plan", []),
        str(active_run.get("run_identity", "")),
        selected_style,
        visual_preference.get("profile_path"),
        require_visual_preference,
    )
    scheduler_state = validate_scheduler_state(
        found.get("scheduler state", []),
        root,
        str(active_run.get("run_identity", "")),
        found.get("generation ledger", []),
        production_plan.get("data") if production_plan.get("valid") else None,
    )
    preflight = validate_preflight(
        found.get("deterministic preflight", []),
        root,
        production_plan.get("data") if production_plan.get("valid") else None,
    )
    post_generation_qc = validate_post_generation_qc(
        found,
        root,
        str(active_run.get("run_identity", "")),
        production_plan.get("data") if production_plan.get("valid") else None,
        preflight,
    )
    agent_task_registry = validate_agent_task_registry(
        found.get("agent task registry", []),
        root,
        str(active_run.get("run_identity", "")),
    )
    stage, stage_label, missing, stage_reason, next_action = determine_stage(
        found,
        selected_style,
        progress,
        scope,
        reference_strategy,
        reference_fidelity_lock,
        visual_preference,
        require_visual_preference,
        style_sample_ledger,
        production_plan,
        scheduler_state,
        preflight,
        post_generation_qc,
        agent_task_registry,
    )
    blocked = is_human_blocked(stage, found)
    if stage == "VISUAL_PREFERENCE_CALIBRATION" and visual_preference.get("discovery_contract_version") == 2:
        pool = visual_preference.get("pool_data") or {}
        # Search, replacement and profile derivation are controller work; only ratings wait for the user.
        blocked = pool.get("status") == "PENDING_RATING" and bool(pool.get("samples"))
    artifacts = {
        key: rel_list(root, paths, limit=6)
        for key, paths in found.items()
        if paths and key not in DIAGNOSTIC_FOUND_KEYS
    }
    context_pack_files = found.get("production handoff", []) + found.get("production context pack", [])
    formal_production_active = stage in {
        "CONTEXT_PACK_PREP",
        "PRODUCTION_PLAN",
        "LAYOUT_MATRIX",
        "PROMPT_WRITING",
        "PROMPT_QC",
        "SCHEDULER_SETUP",
        "IMAGE_GENERATION",
        "IMAGE_GENERATION_PARTIAL",
        "DETERMINISTIC_PREFLIGHT",
        "IMAGE_QC",
        "AGENT_TASK_VERIFICATION",
        "FINAL_EXPORT",
        "COMPLETE",
    }
    current_batch = current_batch_from_stage(stage_label, next_action)
    if current_batch is None and stage in {
        "IMAGE_GENERATION",
        "IMAGE_GENERATION_PARTIAL",
        "DETERMINISTIC_PREFLIGHT",
        "IMAGE_QC",
    }:
        has_main = bool(progress["expected_main_slots"])
        has_aplus = bool(progress["expected_aplus_slots"])
        current_batch = (
            "MAIN_AND_APLUS"
            if has_main and has_aplus
            else "MAIN_BATCH"
            if has_main
            else "APLUS_BATCH"
            if has_aplus
            else None
        )

    return {
        "state_version": STATE_VERSION,
        "skill_version": SKILL_VERSION,
        "mode": FULL_FLOW_MODE,
        "project_root": str(root),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "active_run": {
            "path": rel(root, active_run["path"]) if active_run.get("path") else None,
            "run_identity": active_run.get("run_identity"),
            "active_paths": active_run.get("active_paths", []),
            "include_root_files": active_run.get("include_root_files", True),
            "scoped": active_run.get("scoped", False),
            "workflow_version": active_run.get("workflow_version"),
            "errors": active_run.get("errors", []),
        },
        "stage": stage,
        "stage_label": stage_label,
        "stage_reason": stage_reason or None,
        "blocked": blocked,
        "blocked_reason": stage_reason if blocked else None,
        "missing": missing,
        "completed": completed_artifacts(found),
        "next_action": next_action,
        "selected_style": selected_style.strip() or None,
        "production_scope": {
            "valid": scope["valid"],
            "path": rel(root, scope["path"]) if scope["path"] else None,
            "errors": scope["errors"],
            "data": scope["data"],
        },
        "reference_strategy": {
            "valid": reference_strategy["valid"],
            "path": rel(root, reference_strategy["path"]) if reference_strategy["path"] else None,
            "strategy": reference_strategy["strategy"],
            "errors": reference_strategy["errors"],
        },
        "reference_fidelity_lock": {
            "valid": reference_fidelity_lock["valid"],
            "path": rel(root, reference_fidelity_lock["path"])
            if reference_fidelity_lock["path"]
            else None,
            "errors": reference_fidelity_lock["errors"],
        },
        "visual_preference": {
            "required": require_visual_preference,
            "valid": visual_preference["valid"],
            "pool_path": rel(root, visual_preference["pool_path"])
            if visual_preference["pool_path"]
            else None,
            "profile_path": rel(root, visual_preference["profile_path"])
            if visual_preference["profile_path"]
            else None,
            "rated_sample_ids": visual_preference["rated_sample_ids"],
            "pairwise_generation_allowed": visual_preference[
                "pairwise_generation_allowed"
            ],
            "errors": visual_preference["errors"],
        },
        "generation_ledger": {
            "valid_for_style_samples": style_sample_ledger["valid"],
            "path": rel(root, style_sample_ledger["path"])
            if style_sample_ledger["path"]
            else None,
            "valid_branches": style_sample_ledger["valid_branches"],
            "errors": style_sample_ledger["errors"],
        },
        "production_plan": {
            "valid": production_plan["valid"],
            "path": rel(root, production_plan["path"])
            if production_plan["path"]
            else None,
            "errors": production_plan["errors"],
        },
        "scheduler_state": {
            "valid": scheduler_state["valid"],
            "path": rel(root, scheduler_state["path"])
            if scheduler_state["path"]
            else None,
            "recommended_child_workers": scheduler_state["recommended_child_workers"],
            "hard_max_child_workers": 3,
            "errors": scheduler_state["errors"],
        },
        "deterministic_preflight": {
            "valid": preflight["valid"],
            "path": rel(root, preflight["path"]) if preflight["path"] else None,
            "status": preflight["status"],
            "errors": preflight["errors"],
        },
        "post_generation_qc": {
            "valid": post_generation_qc["valid"],
            "profile_count": post_generation_qc["profile_count"],
            "failed_slot_ids": post_generation_qc["failed_slot_ids"],
            "errors": post_generation_qc["errors"],
        },
        "agent_task_registry": {
            "exists": agent_task_registry["exists"],
            "valid": agent_task_registry["valid"],
            "complete": agent_task_registry["complete"],
            "path": rel(root, agent_task_registry["path"])
            if agent_task_registry["path"]
            else None,
            "errors": agent_task_registry["errors"],
            "pending_tasks": agent_task_registry["pending_tasks"],
            "failed_tasks": agent_task_registry["failed_tasks"],
            "task_count": agent_task_registry["task_count"],
        },
        "formal_production_active": formal_production_active,
        "context_pack_status": context_pack_status(found, selected_style, stage),
        "context_pack_files": rel_list(root, context_pack_files, limit=4),
        "current_batch": current_batch,
        "completed_slots": progress["completed_slots"],
        "pending_slots": progress["blocked_slots"],
        "next_slot": progress["next_slot"],
        "can_generate_images": stage in {
            "REFERENCE_LIBRARY_BUILD",
            "STYLE_SAMPLES",
            "IMAGE_GENERATION",
            "IMAGE_GENERATION_PARTIAL",
        }
        or (
            stage == "VISUAL_PREFERENCE_CALIBRATION"
            and visual_preference["pairwise_generation_allowed"]
        ),
        "generation_route": "DIRECT_IMAGE_INPUT",
        "fallback_generation_route": "VISUAL_CONTEXT_RELAY",
        "generation_gate_policy": "NO_SMOKE_GATES",
        "worker_documents": "ONLY_WHEN_ACTUAL_SUBAGENT_DISPATCH",
        "artifacts": artifacts,
    }


def compact_join(items: list[str], limit: int = 6) -> str:
    if not items:
        return "none"
    shown = items[:limit]
    suffix = f"; +{len(items) - limit} more" if len(items) > limit else ""
    return "; ".join(shown) + suffix


def production_scope_summary(scope: dict[str, Any]) -> str:
    if not scope.get("valid"):
        return "missing/invalid"
    data = scope.get("data") or {}
    parts: list[str] = []
    main = data.get("main") if isinstance(data.get("main"), dict) else {}
    aplus = data.get("aplus") if isinstance(data.get("aplus"), dict) else {}
    if main.get("enabled"):
        ratios = "/".join(str(item) for item in main.get("ratios", [])) or "?"
        if isinstance(main.get("count_by_ratio"), dict) and len(main.get("ratios", [])) == 2:
            counts = ", ".join(
                f"{ratio}: {main['count_by_ratio'].get(ratio, '?')}"
                for ratio in main["ratios"]
            )
            parts.append(f"MAIN ({counts})")
        else:
            parts.append(f"MAIN {main.get('count', '?')} ({ratios})")
    if aplus.get("enabled"):
        aplus_type = str(aplus.get("type", "?"))
        if aplus_type.lower() == "basic":
            parts.append(f"A+ Basic {aplus.get('image_count', '?')} images")
        elif aplus_type.lower() == "premium":
            parts.append(
                "A+ Premium "
                f"{aplus.get('module_count', '?')} modules / "
                f"{aplus.get('desktop_image_count', '?')} desktop / "
                f"{aplus.get('mobile_image_count', 0)} mobile"
            )
        else:
            parts.append(f"A+ {aplus_type}")
    return "; ".join(parts) or "missing/invalid"


def build_markdown(state: dict[str, Any]) -> str:
    status = "COMPLETE" if state["stage"] == "COMPLETE" else ("BLOCKED" if state["blocked"] else "RUNNABLE")
    total_slots = len(state["completed_slots"]) + len(state["pending_slots"])
    slot_progress_text = (
        f"{len(state['completed_slots'])}/{total_slots}; next {state['next_slot'] or 'none'}"
        if total_slots
        else "not started"
    )
    registry = state.get("agent_task_registry", {})
    if not registry.get("exists"):
        registry_text = "not used"
    elif registry.get("complete"):
        registry_text = f"{registry.get('task_count', 0)} verified/cancelled"
    else:
        registry_text = (
            f"{registry.get('task_count', 0)} total; "
            f"pending {len(registry.get('pending_tasks', []))}; "
            f"failed {len(registry.get('failed_tasks', []))}; "
            f"errors {len(registry.get('errors', []))}"
        )
    return f"""# Amazon AI Design Workflow State
- Skill version: `{state.get('skill_version', 'unknown')}`
- Mode: `{state['mode']}`
- Run identity: `{state.get('active_run', {}).get('run_identity') or 'none'}`
- Stage: `{state['stage']}` — {state['stage_label']}
- Status: `{status}`
- Scope: {production_scope_summary(state['production_scope'])}
- Reference route: `{state['reference_strategy']['strategy'] or 'not decided'}`
- Selected style: {state['selected_style'] or 'not selected'}
- Current batch: `{state['current_batch'] or 'none'}`
- Slot progress: {slot_progress_text}
- Agent tasks: {registry_text}
- Completed: {compact_join(state['completed'])}
- Missing: {compact_join(state['missing'])}
- Reason: {state['stage_reason'] or 'none'}
- Next action: {state['next_action']}
- Image generation allowed: {state['can_generate_images']}
- Context pack: `{state['context_pack_status']}`
- Updated: {state['updated_at']}
"""

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan an Amazon AI design project and write structured workflow state."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--selected-style", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print JSON state instead of Markdown.")
    parser.add_argument(
        "--legacy-copy",
        action="store_true",
        help="Also write the legacy Chinese compatibility state file.",
    )
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Project root does not exist or is not a directory: {root}")

    active_run = load_active_run(root)
    found = scan_project(root, active_run=active_run)
    state = build_state(root, found, args.selected_style, active_run)
    markdown = build_markdown(state)
    json_text = json.dumps(state, ensure_ascii=False, indent=2)

    if args.dry_run:
        print(json_text if args.json else markdown)
        return 0

    md_path = root / CANONICAL_STATE_FILE
    json_path = root / CANONICAL_JSON_FILE
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json_text + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")

    if args.legacy_copy:
        legacy_path = root / LEGACY_STATE_FILE
        legacy_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote {legacy_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
