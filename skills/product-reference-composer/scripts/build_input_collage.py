#!/usr/bin/env python3
"""Build a high-resolution source collage for image2 product reference boards."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from contact_fonts import filename_label, load_font


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "product"


def collect_images(input_dir: Path) -> list[Path]:
    files = [
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    ]
    return sorted(files, key=lambda p: p.name.lower())


def fit_image(path: Path, cell_w: int, cell_h: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = ImageOps.exif_transpose(image)
    return ImageOps.contain(image, (cell_w, cell_h), Image.Resampling.LANCZOS)


def build_collage(
    input_dir: Path,
    out_dir: Path,
    product_name: str,
    cols: int | None,
    cell_width: int,
    cell_height: int,
    label_height: int,
    max_photos: int | None,
    font_path: str | Path | None = None,
) -> tuple[Path, Path]:
    files = collect_images(input_dir)
    if not files:
        raise SystemExit(f"No supported images found in {input_dir}")
    if max_photos:
        files = files[:max_photos]

    if cols is None:
        cols = 2 if len(files) <= 12 else 3
    rows = math.ceil(len(files) / cols)

    width = cols * cell_width
    height = rows * (cell_height + label_height)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = load_font(36, bold=True, font_path=font_path)
    title_font = load_font(28, font_path=font_path)

    manifest = {
        "product_name": product_name,
        "source_dir": str(input_dir),
        "collage_size": [width, height],
        "columns": cols,
        "cell_size": [cell_width, cell_height],
        "photos": [],
    }

    for index, path in enumerate(files):
        row = index // cols
        col = index % cols
        x0 = col * cell_width
        y0 = row * (cell_height + label_height)

        image = fit_image(path, cell_width, cell_height)
        x = x0 + (cell_width - image.width) // 2
        y = y0 + (cell_height - image.height) // 2
        sheet.paste(image, (x, y))

        label_y = y0 + cell_height
        draw.rectangle(
            [x0, label_y, x0 + cell_width, label_y + label_height],
            fill=(245, 245, 245),
        )
        label = f"Photo {index + 1:02d}"
        visible_filename = filename_label(title_font, path.name, 60)
        draw.text((x0 + 30, label_y + 14), label, fill=(20, 20, 20), font=label_font)
        draw.text(
            (x0 + 220, label_y + 20),
            visible_filename,
            fill=(95, 95, 95),
            font=title_font,
        )

        manifest["photos"].append(
            {
                "index": index + 1,
                "label": label,
                "display_label": f"{label}: {visible_filename}" if visible_filename else label,
                "file": path.name,
                "original_path": str(path),
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    image_path = out_dir / "00_all_original_photos_input_for_image2.jpg"
    manifest_path = out_dir / "00_all_original_photos_manifest.json"
    sheet.save(image_path, quality=95)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return image_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, help="Folder containing product photos")
    parser.add_argument("--out-dir", required=True, help="Folder to write the collage and manifest")
    parser.add_argument("--product-name", default="product", help="Product name for manifest context")
    parser.add_argument("--cols", type=int, default=None, help="Number of collage columns")
    parser.add_argument("--cell-width", type=int, default=1706)
    parser.add_argument("--cell-height", type=int, default=1279)
    parser.add_argument("--label-height", type=int, default=70)
    parser.add_argument("--max-photos", type=int, default=None)
    parser.add_argument("--font", help="Optional font file for filename labels; unsupported text uses Photo IDs")
    args = parser.parse_args()

    image_path, manifest_path = build_collage(
        input_dir=Path(args.input_dir),
        out_dir=Path(args.out_dir),
        product_name=args.product_name,
        cols=args.cols,
        cell_width=args.cell_width,
        cell_height=args.cell_height,
        label_height=args.label_height,
        max_photos=args.max_photos,
        font_path=args.font,
    )
    print(image_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
