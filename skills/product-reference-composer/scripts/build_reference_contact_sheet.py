from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from contact_fonts import filename_label, load_font


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def is_reference_image(path: Path) -> bool:
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    name = path.name.lower()
    if "contact_sheet" in name or "input_for_image2" in name:
        return False
    return any(
        token in name
        for token in [
            "main-reference",
            "angle-reference",
            "structure-reference",
            "evidence-reference",
            "white-bg",
            "white_background",
        ]
    )


def build_contact_sheet(
    input_dir: Path, output: Path, cols: int = 2, font_path: str | Path | None = None
) -> None:
    files = sorted(path for path in input_dir.iterdir() if path.is_file() and is_reference_image(path))
    if not files:
        raise SystemExit(f"No reference images found in: {input_dir}")

    tile_w, tile_h = 560, 700
    image_max_h = 590
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (245, 245, 245))
    font = load_font(16, font_path=font_path)
    manifest = {
        "source_dir": str(input_dir),
        "contact_sheet": str(output),
        "sheet_size": list(sheet.size),
        "columns": cols,
        "references": [],
    }

    for index, path in enumerate(files):
        image = Image.open(path).convert("RGB")
        image.thumbnail((tile_w - 40, image_max_h), Image.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(image, ((tile_w - image.width) // 2, 20))
        draw = ImageDraw.Draw(tile)
        label = f"Reference {index + 1:02d}"
        visible_filename = filename_label(font, path.name, 60)
        display_label = f"{label}: {visible_filename}" if visible_filename else label
        draw.text((14, image_max_h + 40), display_label, fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
        manifest["references"].append({
            "index": index + 1,
            "label": label,
            "display_label": display_label,
            "file": path.name,
            "original_path": str(path),
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {manifest_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a contact sheet for white-background reference images.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cols", type=int, default=2)
    parser.add_argument("--font", help="Optional font file for filename labels; unsupported text uses Reference IDs")
    args = parser.parse_args()

    build_contact_sheet(Path(args.input_dir), Path(args.output), cols=max(1, args.cols), font_path=args.font)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
