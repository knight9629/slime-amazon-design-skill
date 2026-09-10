from __future__ import annotations

import argparse
import base64
import hashlib
import html
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageOps
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by CLI runtime selection
    raise SystemExit(
        "Pillow is required. Use the bundled Codex Python runtime or install Pillow."
    ) from exc

from design_workflow_state import (
    VISUAL_REFERENCE_CORE_SOURCES,
    VISUAL_REFERENCE_FORBIDDEN_DOMAINS,
    VISUAL_REFERENCE_QUALITY_FLAGS,
    VISUAL_REFERENCE_ROLES,
    VISUAL_REFERENCE_SOURCE_DOMAINS,
    VISUAL_REFERENCE_SUPPLEMENT_SOURCES,
    VISUAL_REFERENCE_TIERS,
    canonical_project_url,
    hostname_matches,
    validate_module_reference_cards,
    validate_visual_module_evidence,
)


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets/visual-reference-rater.template.html"
MAX_FRAGMENT_BYTES = 999_000
PENDING_SNAPSHOT_NAME = "visual_reference_pool.pending.json"
ROLE_LABELS = {
    "SELLING_LOGIC": "卖货逻辑",
    "VISUAL_STYLE": "画面风格",
    "LAYOUT": "排版结构",
    "TYPOGRAPHY_ICON": "字体图标",
    "CONTRAST": "对照方向",
}
TIER_LABELS = {
    "SAME_CATEGORY": "同类目",
    "ADJACENT_PREMIUM": "相邻高端品类",
    "EDITORIAL_BRAND": "编辑品牌",
    "CONTRAST": "刻意对照",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read visual reference pool: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("visual reference pool must be a JSON object")
    return data


def write_pending_pool_snapshot(
    pool_path: Path, pool_data: dict[str, Any]
) -> Path | None:
    if str(pool_data.get("status", "")).strip().upper() != "PENDING_RATING":
        return None
    snapshot_path = pool_path.with_name(PENDING_SNAPSHOT_NAME)
    temporary_path = snapshot_path.with_name(
        f".{snapshot_path.name}.{os.getpid()}.tmp"
    )
    temporary_path.write_bytes(pool_path.read_bytes())
    os.replace(temporary_path, snapshot_path)
    return snapshot_path


def safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def validate_pool_for_rating(pool_data: dict[str, Any]) -> list[str]:
    """Reject weak or untraceable pools before the user spends time rating them."""
    errors: list[str] = []
    if pool_data.get("version") != 1:
        errors.append("visual reference pool version must be 1")
    if not str(pool_data.get("run_identity", "")).strip():
        errors.append("visual reference pool run_identity is required")
    if str(pool_data.get("source_policy_version", "")).strip() != "1":
        errors.append("visual reference pool source_policy_version must be 1")
    if str(pool_data.get("status", "")).strip().upper() not in {
        "PENDING_RATING",
        "RATED",
    }:
        errors.append("visual reference pool status must be PENDING_RATING or RATED")

    selection_mode = str(pool_data.get("selection_mode", "")).strip().upper()
    if selection_mode not in {"STANDARD", "SPARSE_CATEGORY"}:
        errors.append("selection_mode must be STANDARD or SPARSE_CATEGORY")
    sparse_reason = pool_data.get("sparse_category_reason")
    if selection_mode == "SPARSE_CATEGORY" and (
        not isinstance(sparse_reason, str) or not sparse_reason.strip()
    ):
        errors.append("SPARSE_CATEGORY requires a non-empty string sparse_category_reason")

    samples = pool_data.get("samples")
    minimum_samples = 6 if selection_mode == "SPARSE_CATEGORY" else 8
    if not isinstance(samples, list) or not minimum_samples <= len(samples) <= 12:
        errors.append(
            f"visual reference pool must contain {minimum_samples}-12 cards for "
            f"{selection_mode or 'the selected mode'}"
        )
        return errors

    allowed_sources = (
        VISUAL_REFERENCE_CORE_SOURCES | VISUAL_REFERENCE_SUPPLEMENT_SOURCES
    )
    sample_ids: set[str] = set()
    project_urls: set[str] = set()
    covered_roles: set[str] = set()
    covered_tiers: set[str] = set()
    core_source_count = 0
    product_relevant_count = 0
    contrast_count = 0
    for index, sample in enumerate(samples):
        prefix = f"samples[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{prefix} must be an object")
            continue
        sample_id = str(sample.get("id", "")).strip()
        if not sample_id:
            errors.append(f"{prefix}.id is required")
        elif sample_id in sample_ids:
            errors.append(f"{prefix}.id is duplicate")
        sample_ids.add(sample_id)

        source_key = str(sample.get("source_key", "")).strip().upper()
        if source_key not in allowed_sources:
            errors.append(f"{prefix}.source_key is not an approved fixed source")
        elif source_key in VISUAL_REFERENCE_CORE_SOURCES:
            core_source_count += 1

        if not str(sample.get("project", "")).strip():
            errors.append(f"{prefix}.project is required")
        project_url = str(sample.get("project_url", "")).strip()
        canonical_url, hostname, url_error = canonical_project_url(project_url)
        if url_error:
            errors.append(f"{prefix}.project_url {url_error}")
        else:
            if canonical_url in project_urls:
                errors.append(f"{prefix}.project_url duplicates another project")
            if canonical_url is not None:
                project_urls.add(canonical_url)
            if hostname and hostname_matches(
                hostname, VISUAL_REFERENCE_FORBIDDEN_DOMAINS
            ):
                errors.append(f"{prefix}.project_url uses a forbidden discovery source")
            if source_key in VISUAL_REFERENCE_SOURCE_DOMAINS and hostname and not hostname_matches(
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
        tier = str(sample.get("reference_tier", "")).strip().upper()
        if tier not in VISUAL_REFERENCE_TIERS:
            errors.append(f"{prefix}.reference_tier is invalid")
        else:
            covered_tiers.add(tier)
            if tier in {"SAME_CATEGORY", "ADJACENT_PREMIUM"}:
                product_relevant_count += 1
            if tier == "CONTRAST":
                contrast_count += 1

        score = sample.get("quality_score")
        if isinstance(score, bool) or not isinstance(score, int) or not 20 <= score <= 25:
            errors.append(f"{prefix}.quality_score must be an integer from 20 to 25")
        flags = sample.get("quality_flags")
        if not isinstance(flags, dict):
            errors.append(f"{prefix}.quality_flags must be an object")
        else:
            for flag in sorted(VISUAL_REFERENCE_QUALITY_FLAGS):
                if flags.get(flag) is not True:
                    errors.append(f"{prefix}.quality_flags.{flag} must be true")
        for axis in ("visual", "layout"):
            value = sample.get(axis)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value not in {-1, 0, 1}
            ):
                errors.append(f"{prefix}.{axis} must be -1, 0, 1, or null")

    required_core_count = (len(samples) * 4 + 4) // 5
    if core_source_count < required_core_count:
        errors.append("at least 80% of cards must use core fixed sources")
    for required_role in ("VISUAL_STYLE", "LAYOUT"):
        if required_role not in covered_roles:
            errors.append(f"the pool requires at least one {required_role} card")
    minimum_tiers = 2 if selection_mode == "SPARSE_CATEGORY" else 3
    if len(covered_tiers) < minimum_tiers:
        errors.append(f"the pool must cover at least {minimum_tiers} reference tiers")
    if product_relevant_count * 2 < len(samples):
        errors.append("at least 50% of cards must be product-relevant tiers")
    if contrast_count * 4 > len(samples):
        errors.append("CONTRAST cards may not exceed 25% of the pool")
    return errors


def render_panel(image_path: Path, size: tuple[int, int], label: str) -> Image.Image:
    panel = Image.new("RGB", size, (242, 242, 242))
    with Image.open(image_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        fitted = ImageOps.contain(image, (size[0] - 14, size[1] - 14))
    x = (size[0] - fitted.width) // 2
    y = (size[1] - fitted.height) // 2
    panel.paste(fitted, (x, y))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(205, 205, 205), width=2)
    label_width = max(34, 9 + len(label) * 7)
    draw.rectangle((0, 0, label_width, 23), fill=(20, 20, 20))
    draw.text((7, 6), label, fill=(255, 255, 255))
    return panel


def render_collage(
    project_root: Path,
    evidence: list[dict[str, Any]],
    frame_size: tuple[int, int],
) -> Image.Image:
    frame_width, frame_height = frame_size
    columns = 2 if len(evidence) == 4 else 3
    rows = 2
    gap = max(6, frame_width // 150)
    cell_width = (frame_width - gap * (columns + 1)) // columns
    cell_height = (frame_height - gap * (rows + 1)) // rows
    frame = Image.new("RGB", frame_size, (235, 235, 235))
    for index, item in enumerate(evidence):
        row = index // columns
        column = index % columns
        panel = render_panel(
            project_root / item["path"],
            (cell_width, cell_height),
            str(index + 1),
        )
        x = gap + column * (cell_width + gap)
        y = gap + row * (cell_height + gap)
        frame.paste(panel, (x, y))
    return frame


def build_sprite(
    project_root: Path,
    samples: list[dict[str, Any]],
    frame_width: int,
    quality: int,
) -> bytes:
    frame_height = round(frame_width * 9 / 16)
    sprite = Image.new("RGB", (frame_width, frame_height * len(samples)), (235, 235, 235))
    for index, sample in enumerate(samples):
        collage = render_collage(
            project_root,
            sample["module_card"]["evidence"],
            (frame_width, frame_height),
        )
        sprite.paste(collage, (0, index * frame_height))
    buffer = BytesIO()
    sprite.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def sample_metadata(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for sample in samples:
        role = str(sample["role"]).strip().upper()
        tier = str(sample["reference_tier"]).strip().upper()
        result.append(
            {
                "id": str(sample["id"]).strip(),
                "sourceKey": str(sample["source_key"]).strip().upper(),
                "project": str(sample["project"]).strip(),
                "projectUrl": str(sample["project_url"]).strip(),
                "role": role,
                "roleLabel": ROLE_LABELS.get(role, role),
                "referenceTier": tier,
                "tierLabel": TIER_LABELS.get(tier, tier),
                "moduleRoles": [
                    str(item["module_role"]).strip().upper()
                    for item in sample["module_card"]["evidence"]
                ],
            }
        )
    return result


def render_fragment(
    pool_path: Path,
    pool_data: dict[str, Any],
    project_root: Path,
    title: str,
) -> str:
    samples = pool_data.get("samples")
    errors = validate_pool_for_rating(pool_data)
    errors.extend(validate_module_reference_cards(pool_data, project_root, required=True))
    errors.extend(
        validate_visual_module_evidence(pool_data, project_root, required=True)
    )
    if errors:
        raise ValueError("\n".join(errors))
    assert isinstance(samples, list)
    if not TEMPLATE_PATH.is_file():
        raise ValueError(f"missing rater template: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    pool_hash = hashlib.sha256(pool_path.read_bytes()).hexdigest()
    run_identity = str(pool_data.get("run_identity", "visual-reference"))
    root_suffix = hashlib.sha256(f"{run_identity}:{pool_hash}".encode("utf-8")).hexdigest()[:10]
    root_id = f"amazon-visual-reference-rater-{root_suffix}"
    test_id = f"{run_identity}-module-card-v1"
    metadata_json = safe_json(sample_metadata(samples))

    last_size = 0
    for frame_width in (1200, 1080, 960, 900, 840, 780, 720, 640):
        for quality in (82, 76, 70, 64, 58, 52, 46, 42):
            try:
                sprite = build_sprite(project_root, samples, frame_width, quality)
            except (OSError, ValueError) as exc:
                raise ValueError(f"module evidence could not be rendered: {exc}") from exc
            sprite_data = "data:image/jpeg;base64," + base64.b64encode(sprite).decode("ascii")
            fragment = (
                template.replace("__ROOT_ID__", root_id)
                .replace("__TITLE__", html.escape(title))
                .replace("__SAMPLE_COUNT__", str(len(samples)))
                .replace("__SAMPLE_META_JSON__", metadata_json)
                .replace("__SPRITE_DATA__", sprite_data)
                .replace("__POOL_SHA256__", pool_hash)
                .replace("__TEST_ID__", test_id)
            )
            last_size = len(fragment.encode("utf-8"))
            if last_size < MAX_FRAGMENT_BYTES:
                return fragment
    raise ValueError(
        f"inline rater is {last_size} bytes after compression; reduce module evidence size"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a self-contained inline module-card visual preference rater."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--pool", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default="Amazon 卖货设计偏好评分")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.expanduser().resolve()
    pool_path = args.pool.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    try:
        pool_path.relative_to(project_root)
    except ValueError:
        print("visual reference pool must be inside the project root", file=sys.stderr)
        return 2
    try:
        pool_data = load_json(pool_path)
        fragment = render_fragment(
            pool_path,
            pool_data,
            project_root,
            str(args.title).strip() or "Amazon 卖货设计偏好评分",
        )
        write_pending_pool_snapshot(pool_path, pool_data)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fragment, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
