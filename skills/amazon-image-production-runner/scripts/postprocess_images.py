from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
SLOT_ID_RE = re.compile(r"^[A-Z]{1,5}\d{2}(?:S\d+)?$")
SLOT_GROUP_DIRECTORIES = {
    "main": "main_1x1",
    "main_portrait": "main_portrait",
    "basic_aplus": "a_plus_basic",
    "premium_aplus_desktop": "a_plus_premium_desktop",
    "premium_aplus_mobile": "a_plus_premium_mobile",
}
SLOT_GROUP_FIXED_SIZES = {
    "basic_aplus": (960, 600),
    "premium_aplus_desktop": (1464, 600),
    "premium_aplus_mobile": (600, 450),
}
Image = None
ImageDraw = None
ImageFont = None
ImageOps = None


def require_pillow() -> None:
    global Image, ImageDraw, ImageFont, ImageOps
    if Image is not None:
        return

    from PIL import Image as pillow_image
    from PIL import ImageDraw as pillow_image_draw
    from PIL import ImageFont as pillow_image_font
    from PIL import ImageOps as pillow_image_ops

    Image = pillow_image
    ImageDraw = pillow_image_draw
    ImageFont = pillow_image_font
    ImageOps = pillow_image_ops


def parse_size(values: list[str]) -> tuple[int, int]:
    if len(values) != 2:
        raise argparse.ArgumentTypeError("size requires width and height")
    width, height = int(values[0]), int(values[1])
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")
    return width, height


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("count must be non-negative")
    return parsed


def find_raw_file(raw_dir: Path, stem: str) -> Path | None:
    for ext in IMAGE_EXTENSIONS:
        candidate = raw_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def aspect_matches(source_size: tuple[int, int], target_size: tuple[int, int]) -> bool:
    source_width, source_height = source_size
    target_width, target_height = target_size
    return source_width * target_height == target_width * source_height


def has_ratio(size: tuple[int, int], ratio: tuple[int, int]) -> bool:
    width, height = size
    ratio_width, ratio_height = ratio
    return width * ratio_height == height * ratio_width


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_record(path: Path, group: str) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
    return {
        "group": group,
        "path": str(path.resolve()),
        "width": width,
        "height": height,
        "sha256": file_sha256(path),
    }


def slot_file_name(value: object, field: str) -> tuple[str | None, str | None]:
    text = str(value).strip()
    if not text:
        return None, f"{field} must be a non-empty file name"
    candidate = Path(text)
    if candidate.is_absolute() or candidate.name != text or ".." in candidate.parts:
        return None, f"{field} must be a file name without directories: {text}"
    return text, None


def load_slot_manifest(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [], [f"invalid slot manifest: {exc}"]
    if not isinstance(data, dict):
        return [], ["slot manifest root must be an object"]
    if data.get("version") != 1:
        errors.append("slot manifest version must be 1")
    raw_slots = data.get("slots")
    if not isinstance(raw_slots, list) or not raw_slots:
        return [], [*errors, "slot manifest slots must be a non-empty list"]

    slots: list[dict[str, object]] = []
    seen_slot_ids: set[str] = set()
    seen_outputs: set[tuple[str, str]] = set()
    for index, raw_slot in enumerate(raw_slots, start=1):
        prefix = f"slots[{index}]"
        if not isinstance(raw_slot, dict):
            errors.append(f"{prefix} must be an object")
            continue

        slot_id = str(raw_slot.get("slot_id", "")).strip()
        if not SLOT_ID_RE.fullmatch(slot_id):
            errors.append(f"{prefix}.slot_id is invalid: {slot_id or '<empty>'}")
        elif slot_id in seen_slot_ids:
            errors.append(f"{prefix}.slot_id is duplicate: {slot_id}")
        else:
            seen_slot_ids.add(slot_id)

        group = str(raw_slot.get("group", "")).strip()
        if group not in SLOT_GROUP_DIRECTORIES:
            errors.append(f"{prefix}.group is unsupported: {group or '<empty>'}")

        raw_file, raw_error = slot_file_name(raw_slot.get("raw_file", ""), f"{prefix}.raw_file")
        output_file, output_error = slot_file_name(
            raw_slot.get("output_file", ""), f"{prefix}.output_file"
        )
        if raw_error:
            errors.append(raw_error)
        elif Path(raw_file).suffix.lower() not in IMAGE_EXTENSIONS:
            errors.append(f"{prefix}.raw_file must use a supported image extension")
        if output_error:
            errors.append(output_error)
        elif Path(output_file).suffix.lower() != ".png":
            errors.append(f"{prefix}.output_file must use .png")

        size = raw_slot.get("size")
        if (
            not isinstance(size, list)
            or len(size) != 2
            or any(not isinstance(value, int) or value <= 0 for value in size)
        ):
            errors.append(f"{prefix}.size must contain two positive integers")
        elif group in SLOT_GROUP_FIXED_SIZES and tuple(size) != SLOT_GROUP_FIXED_SIZES[group]:
            required = SLOT_GROUP_FIXED_SIZES[group]
            errors.append(f"{prefix}.{group} size must be {required[0]}x{required[1]}")
        elif group == "main" and not has_ratio((size[0], size[1]), (1, 1)):
            errors.append(f"{prefix}.main size must use a 1:1 ratio")
        elif group == "main_portrait" and not has_ratio((size[0], size[1]), (4, 5)):
            errors.append(f"{prefix}.main_portrait size must use a 4:5 ratio")
        if output_file and group in SLOT_GROUP_DIRECTORIES:
            output_key = (group, output_file)
            if output_key in seen_outputs:
                errors.append(f"{prefix}.output_file is duplicate within {group}: {output_file}")
            else:
                seen_outputs.add(output_key)

        if (
            SLOT_ID_RE.fullmatch(slot_id)
            and group in SLOT_GROUP_DIRECTORIES
            and raw_file
            and output_file
            and isinstance(size, list)
            and len(size) == 2
            and all(isinstance(value, int) and value > 0 for value in size)
        ):
            slots.append(
                {
                    "slot_id": slot_id,
                    "group": group,
                    "raw_file": raw_file,
                    "output_file": output_file,
                    "size": (size[0], size[1]),
                }
            )

    basic_slot_count = sum(1 for slot in slots if slot["group"] == "basic_aplus")
    if basic_slot_count > 7:
        errors.append("slot manifest basic_aplus supports at most 7 standalone images")

    return slots, errors


def process_slot_manifest(
    *, base_dir: Path, raw_dir: Path, preview_dir: Path, manifest_path: Path
) -> int:
    slots, validation_errors = load_slot_manifest(manifest_path)
    final_manifest_path = preview_dir / "production_manifest.json"
    partial_manifest_path = preview_dir / "partial_production_manifest.json"
    final_manifest_path.unlink(missing_ok=True)

    written: list[tuple[dict[str, object], Path]] = []
    missing: list[str] = []
    rework: dict[str, list[str]] = {}
    if not validation_errors:
        for slot in slots:
            group = str(slot["group"])
            raw_path = raw_dir / str(slot["raw_file"])
            if not raw_path.is_file():
                missing.append(str(slot["raw_file"]))
                continue
            output_path = (
                base_dir / SLOT_GROUP_DIRECTORIES[group] / str(slot["output_file"])
            )
            reason = resize_no_crop(raw_path, output_path, slot["size"])
            if reason:
                rework.setdefault(group, []).append(reason)
            else:
                written.append((slot, output_path))

    if validation_errors:
        status = "INVALID_SLOT_MANIFEST"
    elif rework:
        status = "REWORK_REQUIRED"
    elif missing:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    outputs: list[dict[str, object]] = []
    for slot, path in written:
        record = output_record(path, str(slot["group"]))
        record["slot_id"] = slot["slot_id"]
        outputs.append(record)
    manifest = {
        "status": status,
        "base_dir": str(base_dir),
        "raw_dir": str(raw_dir),
        "slot_manifest": str(manifest_path.resolve()),
        "outputs": outputs,
        "missing": missing,
        "image2_rework_required": rework,
        "validation_errors": validation_errors,
    }
    preview_dir.mkdir(parents=True, exist_ok=True)
    destination = final_manifest_path if status == "PASS" else partial_manifest_path
    destination.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if status == "PASS":
        partial_manifest_path.unlink(missing_ok=True)
    if status != "PASS":
        for error in validation_errors:
            print(f"Slot manifest error: {error}")
        for raw_file in missing:
            print(f"Missing raw file: {raw_file}")
        for reasons in rework.values():
            for reason in reasons:
                print(f"Slot requiring image2 rework: {reason}")
        return 2 if validation_errors else 1

    print(f"Wrote {len(outputs)} outputs from slot manifest.")
    return 0


def resize_no_crop(src: Path, dst: Path, size: tuple[int, int]) -> str | None:
    with Image.open(src) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        if not aspect_matches(image.size, size):
            return (
                f"{src.name}: {image.width}x{image.height} cannot become "
                f"{size[0]}x{size[1]} without crop/pad/stretch; requires image2 rework"
            )
        resized = image.resize(size, Image.Resampling.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        resized.save(dst, "PNG", optimize=True)
    return None


def label_font(size: int = 18) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def make_contact_sheet(
    files: Iterable[Path],
    output_path: Path,
    title: str,
    columns: int,
    thumb_size: tuple[int, int],
) -> None:
    files = list(files)
    if not files:
        return

    label_height = 34
    title_height = 44
    gap = 14
    rows = (len(files) + columns - 1) // columns
    width = columns * thumb_size[0] + (columns + 1) * gap
    height = title_height + rows * (thumb_size[1] + label_height) + (rows + 1) * gap

    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    font = label_font(18)
    draw.text((gap, 12), title, fill=(20, 20, 20), font=font)

    for index, file_path in enumerate(files):
        row = index // columns
        col = index % columns
        x = gap + col * (thumb_size[0] + gap)
        y = title_height + gap + row * (thumb_size[1] + label_height + gap)

        with Image.open(file_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            thumb = ImageOps.contain(image, thumb_size, method=Image.Resampling.LANCZOS)
        background = Image.new("RGB", thumb_size, (245, 245, 245))
        paste_x = (thumb_size[0] - thumb.width) // 2
        paste_y = (thumb_size[1] - thumb.height) // 2
        background.paste(thumb, (paste_x, paste_y))
        sheet.paste(background, (x, y))
        draw.text((x, y + thumb_size[1] + 8), file_path.name, fill=(35, 35, 35), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "PNG", optimize=True)


def process_group(
    raw_dir: Path,
    output_dir: Path,
    prefix: str,
    count: int,
    output_suffix: str,
    size: tuple[int, int],
) -> tuple[list[Path], list[str], list[str]]:
    written: list[Path] = []
    missing: list[str] = []
    rework_required: list[str] = []
    for index in range(1, count + 1):
        raw_stem = f"{prefix}_{index:02d}_raw"
        raw_path = find_raw_file(raw_dir, raw_stem)
        if raw_path is None:
            missing.append(raw_stem)
            continue

        output_path = output_dir / f"{prefix}_{index:02d}_{output_suffix}.png"
        rework_reason = resize_no_crop(raw_path, output_path, size)
        if rework_reason:
            rework_required.append(rework_reason)
        else:
            written.append(output_path)

    return written, missing, rework_required


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resize full Amazon image production outputs and create preview sheets."
    )
    parser.add_argument("--base-dir", required=True, type=Path, help="Selected style output folder.")
    parser.add_argument(
        "--slot-manifest",
        type=Path,
        help="Explicit slot manifest for carousel and non-sequential output names.",
    )
    parser.add_argument("--main-count", type=nonnegative_int, default=0, help="Expected main image count.")
    parser.add_argument(
        "--main-portrait-count",
        type=nonnegative_int,
        default=0,
        help="Expected portrait main image count. Uses raw stems main_portrait_01_raw, etc.",
    )
    parser.add_argument("--main-size", nargs=2, default=["2000", "2000"], help="Main output size.")
    parser.add_argument(
        "--main-portrait-size",
        nargs=2,
        default=["2000", "2500"],
        help="Portrait main output size. Keep this 4:5.",
    )
    parser.add_argument(
        "--basic-aplus-count",
        type=nonnegative_int,
        default=0,
        help="Expected Basic A+ image count. Uses raw stems aplus_basic_01_raw, etc.",
    )
    parser.add_argument(
        "--premium-aplus-desktop-count",
        type=nonnegative_int,
        default=0,
        help="Expected Premium A+ desktop image count. Uses raw stems aplus_premium_desktop_01_raw, etc.",
    )
    parser.add_argument(
        "--premium-aplus-mobile-count",
        type=nonnegative_int,
        default=0,
        help="Expected Premium A+ mobile image count. Uses raw stems aplus_premium_mobile_01_raw, etc.",
    )
    parser.add_argument(
        "--aplus-count",
        type=nonnegative_int,
        default=0,
        help="Legacy generic A+ image count. Prefer specific Basic/Premium arguments.",
    )
    parser.add_argument("--aplus-size", nargs=2, default=["960", "600"], help="Legacy generic A+ output size.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_dir = args.base_dir.resolve()
    raw_dir = base_dir / "raw_generated"
    main_dir = base_dir / "main_1x1"
    main_portrait_dir = base_dir / "main_portrait"
    aplus_dir = base_dir / "a_plus"
    basic_aplus_dir = base_dir / "a_plus_basic"
    premium_aplus_desktop_dir = base_dir / "a_plus_premium_desktop"
    premium_aplus_mobile_dir = base_dir / "a_plus_premium_mobile"
    preview_dir = base_dir / "preview"
    final_manifest_path = preview_dir / "production_manifest.json"
    partial_manifest_path = preview_dir / "partial_production_manifest.json"
    final_manifest_path.unlink(missing_ok=True)

    if args.basic_aplus_count > 7:
        print("Basic A+ supports at most 7 standalone images")
        return 2

    if not raw_dir.exists():
        print(f"Missing raw_generated folder: {raw_dir}")
        return 2

    require_pillow()

    count_values = [
        args.main_count,
        args.main_portrait_count,
        args.basic_aplus_count,
        args.premium_aplus_desktop_count,
        args.premium_aplus_mobile_count,
        args.aplus_count,
    ]
    if args.slot_manifest is not None:
        if any(count_values):
            print("--slot-manifest cannot be combined with count-based arguments")
            return 2
        return process_slot_manifest(
            base_dir=base_dir,
            raw_dir=raw_dir,
            preview_dir=preview_dir,
            manifest_path=args.slot_manifest.resolve(),
        )

    main_size = parse_size(args.main_size)
    main_portrait_size = parse_size(args.main_portrait_size)
    aplus_size = parse_size(args.aplus_size)
    if not has_ratio(main_size, (1, 1)):
        print(f"Invalid --main-size {main_size[0]}x{main_size[1]}: target must be 1:1")
        return 2
    if not has_ratio(main_portrait_size, (4, 5)):
        print(
            f"Invalid --main-portrait-size {main_portrait_size[0]}x{main_portrait_size[1]}: "
            "target must be 4:5"
        )
        return 2

    main_files, missing_main, rework_main = process_group(
        raw_dir, main_dir, "main", args.main_count, "1x1", main_size
    )
    main_portrait_files: list[Path] = []
    missing_main_portrait: list[str] = []
    rework_main_portrait: list[str] = []
    if args.main_portrait_count > 0:
        portrait_suffix = f"{main_portrait_size[0]}x{main_portrait_size[1]}"
        main_portrait_files, missing_main_portrait, rework_main_portrait = process_group(
            raw_dir,
            main_portrait_dir,
            "main_portrait",
            args.main_portrait_count,
            portrait_suffix,
            main_portrait_size,
        )
    aplus_suffix = f"{aplus_size[0]}x{aplus_size[1]}"
    aplus_files, missing_aplus, rework_aplus = process_group(
        raw_dir, aplus_dir, "aplus", args.aplus_count, aplus_suffix, aplus_size
    )
    basic_aplus_files, missing_basic_aplus, rework_basic_aplus = process_group(
        raw_dir,
        basic_aplus_dir,
        "aplus_basic",
        args.basic_aplus_count,
        "960x600",
        (960, 600),
    )
    premium_aplus_desktop_files, missing_premium_aplus_desktop, rework_premium_aplus_desktop = process_group(
        raw_dir,
        premium_aplus_desktop_dir,
        "aplus_premium_desktop",
        args.premium_aplus_desktop_count,
        "1464x600",
        (1464, 600),
    )
    premium_aplus_mobile_files, missing_premium_aplus_mobile, rework_premium_aplus_mobile = process_group(
        raw_dir,
        premium_aplus_mobile_dir,
        "aplus_premium_mobile",
        args.premium_aplus_mobile_count,
        "600x450",
        (600, 450),
    )

    make_contact_sheet(
        main_files,
        preview_dir / "main_contact_sheet.png",
        "Amazon Main Images",
        columns=4,
        thumb_size=(320, 320),
    )
    make_contact_sheet(
        main_portrait_files,
        preview_dir / "main_portrait_contact_sheet.png",
        "Amazon Main Images - Portrait",
        columns=4,
        thumb_size=(256, 320),
    )
    make_contact_sheet(
        aplus_files,
        preview_dir / "aplus_contact_sheet.png",
        "Amazon A+ Images - Legacy",
        columns=2,
        thumb_size=(360, 270),
    )
    make_contact_sheet(
        basic_aplus_files,
        preview_dir / "basic_aplus_contact_sheet.png",
        "Amazon Basic A+ Images",
        columns=2,
        thumb_size=(360, 225),
    )
    make_contact_sheet(
        premium_aplus_desktop_files,
        preview_dir / "premium_aplus_desktop_contact_sheet.png",
        "Amazon Premium A+ Desktop Images",
        columns=2,
        thumb_size=(366, 150),
    )
    make_contact_sheet(
        premium_aplus_mobile_files,
        preview_dir / "premium_aplus_mobile_contact_sheet.png",
        "Amazon Premium A+ Mobile Images",
        columns=3,
        thumb_size=(240, 180),
    )

    all_missing = (
        missing_main
        + missing_main_portrait
        + missing_aplus
        + missing_basic_aplus
        + missing_premium_aplus_desktop
        + missing_premium_aplus_mobile
    )
    all_rework = (
        rework_main
        + rework_main_portrait
        + rework_aplus
        + rework_basic_aplus
        + rework_premium_aplus_desktop
        + rework_premium_aplus_mobile
    )
    status = "REWORK_REQUIRED" if all_rework else ("INCOMPLETE" if all_missing else "PASS")
    grouped_outputs = [
        ("main", main_files),
        ("main_portrait", main_portrait_files),
        ("legacy_aplus", aplus_files),
        ("basic_aplus", basic_aplus_files),
        ("premium_aplus_desktop", premium_aplus_desktop_files),
        ("premium_aplus_mobile", premium_aplus_mobile_files),
    ]
    manifest = {
        "status": status,
        "base_dir": str(base_dir),
        "raw_dir": str(raw_dir),
        "outputs": [
            output_record(path, group)
            for group, paths in grouped_outputs
            for path in paths
        ],
        "missing": all_missing,
        "main_outputs": [str(path) for path in main_files],
        "main_portrait_outputs": [str(path) for path in main_portrait_files],
        "legacy_aplus_outputs": [str(path) for path in aplus_files],
        "basic_aplus_outputs": [str(path) for path in basic_aplus_files],
        "premium_aplus_desktop_outputs": [str(path) for path in premium_aplus_desktop_files],
        "premium_aplus_mobile_outputs": [str(path) for path in premium_aplus_mobile_files],
        "missing_main_raw_stems": missing_main,
        "missing_main_portrait_raw_stems": missing_main_portrait,
        "missing_legacy_aplus_raw_stems": missing_aplus,
        "missing_basic_aplus_raw_stems": missing_basic_aplus,
        "missing_premium_aplus_desktop_raw_stems": missing_premium_aplus_desktop,
        "missing_premium_aplus_mobile_raw_stems": missing_premium_aplus_mobile,
        "image2_rework_required": {
            "main": rework_main,
            "main_portrait": rework_main_portrait,
            "legacy_aplus": rework_aplus,
            "basic_aplus": rework_basic_aplus,
            "premium_aplus_desktop": rework_premium_aplus_desktop,
            "premium_aplus_mobile": rework_premium_aplus_mobile,
        },
    }
    preview_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = final_manifest_path if status == "PASS" else partial_manifest_path
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if status == "PASS":
        partial_manifest_path.unlink(missing_ok=True)

    print(
        f"Wrote {len(main_files)} square main images, "
        f"{len(main_portrait_files)} portrait main images, "
        f"{len(basic_aplus_files)} Basic A+ images, "
        f"{len(premium_aplus_desktop_files)} Premium A+ desktop images, "
        f"{len(premium_aplus_mobile_files)} Premium A+ mobile images, "
        f"and {len(aplus_files)} legacy A+ images."
    )
    if all_missing:
        print("Missing raw stems:")
        for stem in all_missing:
            print(f"  {stem}")
        return 1
    if all_rework:
        print("Slots requiring image2 rework:")
        for reason in all_rework:
            print(f"  {reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
