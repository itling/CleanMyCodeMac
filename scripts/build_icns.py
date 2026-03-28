#!/usr/bin/env python3

from __future__ import annotations

import struct
from pathlib import Path


ICON_TYPES = [
    ("icp4", "icon_16x16.png"),
    ("icp5", "icon_32x32.png"),
    ("icp6", "icon_64x64.png"),
    ("ic07", "icon_128x128.png"),
    ("ic08", "icon_256x256.png"),
    ("ic09", "icon_512x512.png"),
    ("ic10", "icon_1024x1024.png"),
]


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    icon_dir = project_dir / "resources" / "generated_icons"
    output_path = project_dir / "resources" / "app.icns"

    chunks: list[bytes] = []
    for icon_type, filename in ICON_TYPES:
        image_path = icon_dir / filename
        if not image_path.exists():
            raise FileNotFoundError(f"missing icon source: {image_path}")
        data = image_path.read_bytes()
        chunk = icon_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data
        chunks.append(chunk)

    body = b"".join(chunks)
    output_path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)
    print(output_path)


if __name__ == "__main__":
    main()
