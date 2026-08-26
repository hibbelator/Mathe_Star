"""Generate the Android bitmap assets without storing binaries in Git.

The output is deterministic and uses only Python's standard library. Run this
before ``flet build apk``; generated PNG files remain intentionally untracked.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Callable
from pathlib import Path

Color = tuple[int, int, int, int]
PixelFunction = Callable[[int, int], Color]
ASSET_DIR = Path(__file__).parents[1] / "assets"
BLUE: Color = (83, 109, 254, 255)
WHITE: Color = (255, 255, 255, 255)
INK: Color = (23, 34, 59, 255)
YELLOW: Color = (255, 213, 79, 255)
TRANSPARENT: Color = (0, 0, 0, 0)


def _chunk(kind: bytes, value: bytes) -> bytes:
    return (
        struct.pack(">I", len(value))
        + kind
        + value
        + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)
    )


def _write_png(path: Path, width: int, height: int, pixel: PixelFunction) -> None:
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(pixel(x, y))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + _chunk(b"IEND", b"")
    )


def _inside_rounded_box(x: float, y: float, box: tuple[int, int, int, int], radius: int) -> bool:
    x0, y0, x1, y1 = box
    dx, dy = max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)
    return dx * dx + dy * dy <= radius * radius


def _calculator(x: float, y: float, background: Color) -> Color:
    color = background
    if _inside_rounded_box(x, y, (190, 120, 834, 904), 90):
        color = WHITE
    if _inside_rounded_box(x, y, (270, 220, 754, 400), 30):
        color = INK
    for center_y in (530, 710):
        for center_x in (320, 512, 704):
            if (x - center_x) ** 2 + (y - center_y) ** 2 < 65**2:
                color = YELLOW
    return color


def generate() -> None:
    """Create normal, adaptive-foreground and splash PNG files."""

    ASSET_DIR.mkdir(exist_ok=True)
    _write_png(ASSET_DIR / "icon.png", 1024, 1024, lambda x, y: _calculator(x, y, BLUE))
    _write_png(
        ASSET_DIR / "icon_android_foreground.png",
        1024,
        1024,
        lambda x, y: _calculator((x - 512) * 1.25 + 512, (y - 512) * 1.25 + 512, TRANSPARENT),
    )
    # Flet accepts a square source image and scales it for the native splash.
    (ASSET_DIR / "splash.png").write_bytes((ASSET_DIR / "icon.png").read_bytes())


if __name__ == "__main__":
    generate()
