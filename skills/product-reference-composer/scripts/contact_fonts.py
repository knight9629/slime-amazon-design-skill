"""Portable contact-sheet fonts without an additional font package."""
from __future__ import annotations

from pathlib import Path

from PIL import ImageFont


CJK_FONT_PATHS = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
)


def supports_text(font: ImageFont.ImageFont, text: str) -> bool:
    """Reject unsupported Unicode glyphs instead of silently drawing tofu."""
    try:
        missing = font.getmask("\U0010ffff")
        missing_signature = (missing.size, bytes(missing))
        for char in set(text):
            if char.isascii() or char.isspace():
                continue
            mask = font.getmask(char)
            if (mask.size, bytes(mask)) == missing_signature:
                return False
    except (UnicodeError, OSError, ValueError):
        return False
    return True


def load_font(
    size: int, bold: bool = False, font_path: str | Path | None = None
) -> ImageFont.ImageFont:
    if font_path is not None:
        return ImageFont.truetype(str(font_path), size)
    for path in CJK_FONT_PATHS:
        try:
            font = ImageFont.truetype(path, size)
            if supports_text(font, "中文"):
                return font
        except (OSError, ValueError):
            continue
    # Pillow >=10.1 accepts size; older supported Pillow releases use their
    # bundled ASCII bitmap font. Filenames are retained in the JSON manifest.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def filename_label(font: ImageFont.ImageFont, filename: str, limit: int) -> str:
    text = filename[:limit]
    return text if supports_text(font, text) else ""
