#!/usr/bin/env python3

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


SIZE = 1024


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = clamp((x - edge0) / (edge1 - edge0))
    return t * t * (3.0 - 2.0 * t)


def mix(a: float, b: float, t: float) -> float:
    return a * (1.0 - t) + b * t


def mix_color(c1: tuple[float, float, float], c2: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return tuple(mix(c1[i], c2[i], t) for i in range(3))


def alpha_over(
    base_rgb: tuple[float, float, float],
    base_a: float,
    top_rgb: tuple[float, float, float],
    top_a: float,
) -> tuple[tuple[float, float, float], float]:
    out_a = top_a + base_a * (1.0 - top_a)
    if out_a <= 0.0:
        return (0.0, 0.0, 0.0), 0.0

    out_rgb = tuple(
        (top_rgb[i] * top_a + base_rgb[i] * base_a * (1.0 - top_a)) / out_a
        for i in range(3)
    )
    return out_rgb, out_a


def rgb(r: int, g: int, b: int) -> tuple[float, float, float]:
    return (r / 255.0, g / 255.0, b / 255.0)


def rounded_rect_mask(
    x: float,
    y: float,
    cx: float,
    cy: float,
    hw: float,
    hh: float,
    radius: float,
    feather: float,
) -> float:
    dx = abs(x - cx) - (hw - radius)
    dy = abs(y - cy) - (hh - radius)
    qx = max(dx, 0.0)
    qy = max(dy, 0.0)
    outside = math.hypot(qx, qy)
    inside = min(max(dx, dy), 0.0)
    dist = outside + inside - radius
    return 1.0 - smoothstep(0.0, feather, dist)


def circle_mask(x: float, y: float, cx: float, cy: float, radius: float, feather: float) -> float:
    dist = math.hypot(x - cx, y - cy) - radius
    return 1.0 - smoothstep(0.0, feather, dist)


def segment_mask(
    x: float,
    y: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    radius: float,
    feather: float,
) -> float:
    pax = x - ax
    pay = y - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay
    h = 0.0 if denom == 0.0 else clamp((pax * bax + pay * bay) / denom)
    dx = pax - bax * h
    dy = pay - bay * h
    dist = math.hypot(dx, dy) - radius
    return 1.0 - smoothstep(0.0, feather, dist)


def diamond_mask(x: float, y: float, cx: float, cy: float, rx: float, ry: float, feather: float) -> float:
    dist = abs(x - cx) / rx + abs(y - cy) / ry - 1.0
    return 1.0 - smoothstep(0.0, feather / max(rx, ry), dist)


def write_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(width: int, height: int, rgba_bytes: bytes, path: Path) -> None:
    stride = width * 4
    scanlines = bytearray()
    for row in range(height):
        start = row * stride
        scanlines.append(0)
        scanlines.extend(rgba_bytes[start:start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(scanlines), level=9)
    png = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            write_png_chunk(b"IHDR", ihdr),
            write_png_chunk(b"IDAT", idat),
            write_png_chunk(b"IEND", b""),
        ]
    )
    path.write_bytes(png)


def render() -> bytes:
    blue_top = rgb(80, 194, 255)
    blue_bottom = rgb(20, 103, 226)
    blue_dark = rgb(17, 83, 193)
    aqua = rgb(98, 236, 214)
    aqua_dark = rgb(49, 214, 194)
    white = rgb(255, 255, 255)
    ice = rgb(214, 239, 255)
    navy = rgb(18, 74, 180)
    transparent = (0.0, 0.0, 0.0)

    cx = cy = SIZE / 2
    tile = 860
    radius = 188

    data = bytearray()
    for j in range(SIZE):
        y = j + 0.5
        ny = y / SIZE

        for i in range(SIZE):
            x = i + 0.5
            nx = x / SIZE

            color = transparent
            alpha = 0.0

            shadow = rounded_rect_mask(x, y, cx, cy + 34, tile / 2, tile / 2, radius, 58)
            color, alpha = alpha_over(color, alpha, rgb(10, 74, 167), 0.16 * shadow)

            tile_mask = rounded_rect_mask(x, y, cx, cy, tile / 2, tile / 2, radius, 1.2)
            if tile_mask > 0.0:
                bg = mix_color(blue_top, blue_bottom, 0.82 * ny + 0.08 * nx)
                top_glow = circle_mask(x, y, cx - 120, cy - 170, 250, 60)
                bg = mix_color(bg, rgb(134, 221, 255), 0.18 * top_glow)
                color, alpha = alpha_over(color, alpha, bg, tile_mask)

                rim_outer = rounded_rect_mask(x, y, cx, cy, tile / 2, tile / 2, radius, 1.0)
                rim_inner = rounded_rect_mask(x, y, cx, cy, tile / 2 - 22, tile / 2 - 22, radius - 18, 1.0)
                rim = max(rim_outer - rim_inner, 0.0)
                color, alpha = alpha_over(color, alpha, white, 0.10 * rim)

                orb = circle_mask(x, y, cx - 10, cy + 36, 222, 1.4)
                orb_color = mix_color(rgb(94, 224, 255), blue_dark, 0.65 * ny)
                color, alpha = alpha_over(color, alpha, orb_color, 0.95 * orb)

                cut = circle_mask(x, y, cx - 10, cy + 36, 152, 1.4)
                color, alpha = alpha_over(color, alpha, blue_bottom, 0.78 * cut)

                ring = max(
                    circle_mask(x, y, cx - 10, cy + 36, 250, 1.6) - circle_mask(x, y, cx - 10, cy + 36, 216, 1.6),
                    0.0,
                )
                color, alpha = alpha_over(color, alpha, aqua, 0.80 * ring)

                handle_shadow = segment_mask(x, y, cx - 106, cy + 182, cx + 142, cy - 66, 64, 1.2)
                color, alpha = alpha_over(color, alpha, rgb(8, 70, 156), 0.18 * handle_shadow)

                handle = segment_mask(x, y, cx - 116, cy + 166, cx + 128, cy - 78, 58, 0.9)
                color, alpha = alpha_over(color, alpha, white, 0.99 * handle)

                groove = segment_mask(x, y, cx - 18, cy + 74, cx + 86, cy - 30, 20, 0.9)
                color, alpha = alpha_over(color, alpha, ice, 0.92 * groove)

                ferrule = segment_mask(x, y, cx + 116, cy - 118, cx + 164, cy - 166, 26, 0.8)
                color, alpha = alpha_over(color, alpha, rgb(230, 247, 255), 0.98 * ferrule)

                tip = diamond_mask(x, y, cx + 206, cy - 208, 68, 62, 0.8)
                color, alpha = alpha_over(color, alpha, white, 0.99 * tip)

                bristle = diamond_mask(x, y, cx + 220, cy - 222, 28, 28, 0.6)
                color, alpha = alpha_over(color, alpha, aqua, 0.98 * bristle)

                sparkle1 = max(
                    segment_mask(x, y, cx - 256, cy - 6, cx - 256, cy + 54, 10, 0.7),
                    segment_mask(x, y, cx - 286, cy + 24, cx - 226, cy + 24, 10, 0.7),
                )
                color, alpha = alpha_over(color, alpha, white, 0.95 * sparkle1)

                sparkle2 = max(
                    segment_mask(x, y, cx + 226, cy + 52, cx + 226, cy + 98, 8, 0.7),
                    segment_mask(x, y, cx + 203, cy + 75, cx + 249, cy + 75, 8, 0.7),
                )
                color, alpha = alpha_over(color, alpha, white, 0.78 * sparkle2)

                badge = circle_mask(x, y, cx + 172, cy + 202, 64, 0.9)
                color, alpha = alpha_over(color, alpha, aqua_dark, 0.96 * badge)

                badge_mark = segment_mask(x, y, cx + 142, cy + 202, cx + 202, cy + 202, 10, 0.7)
                color, alpha = alpha_over(color, alpha, navy, 0.94 * badge_mark)

            data.extend(
                [
                    int(clamp(color[0]) * 255 + 0.5),
                    int(clamp(color[1]) * 255 + 0.5),
                    int(clamp(color[2]) * 255 + 0.5),
                    int(clamp(alpha) * 255 + 0.5),
                ]
            )

    return bytes(data)


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    output_dir = project_dir / "resources"
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "app_icon.png"
    write_png(SIZE, SIZE, render(), png_path)
    print(png_path)


if __name__ == "__main__":
    main()
