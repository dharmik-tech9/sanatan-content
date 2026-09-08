#!/usr/bin/env python3
"""Generates thumbnail/preview/full variants for STATIC wallpaper source
images, per the content-delivery plan's three-size guidance (section 7):
  thumbnail  300-400px wide   -> thumbnails/wallpapers/<id>_thumb.webp
  preview    720-1080px wide  -> content-source/wallpapers/<id>_preview.webp
  full       ~1440px wide     -> content-source/wallpapers/<id>_full.webp

Run this before scripts/generate_catalog.py wallpapers so the CSV's
sourceFile can point at the generated *_full.webp (the file that gets
uploaded to the GitHub Release). Thumbnails land directly in
thumbnails/wallpapers/ since those are small enough to commit to the repo
itself, per the plan's repository design.

Only touches STATIC wallpapers -- LIVE wallpaper videos aren't resized;
add/trim those with your own video tooling before running generate_catalog.

Usage: python3 scripts/optimize_wallpapers.py <source_image> <id>
Example: python3 scripts/optimize_wallpapers.py ~/raw/shiva1.jpg wallpaper_shiva_0001
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
THUMB_WIDTH = 360
PREVIEW_WIDTH = 1080
FULL_WIDTH = 1440


def resized(image, target_width: int):
    from PIL import Image
    if image.width <= target_width:
        return image.copy()
    ratio = target_width / image.width
    return image.resize((target_width, round(image.height * ratio)), Image.LANCZOS)


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow not installed -- run: pip install Pillow")

    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <source_image> <id>")
    source_path, wallpaper_id = Path(sys.argv[1]), sys.argv[2]
    if not source_path.exists():
        sys.exit(f"Source image not found: {source_path}")

    thumb_dir = REPO_ROOT / "thumbnails" / "wallpapers"
    source_dir = REPO_ROOT / "content-source" / "wallpapers"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as original:
        original = original.convert("RGB")
        thumb_path = thumb_dir / f"{wallpaper_id}_thumb.webp"
        preview_path = source_dir / f"{wallpaper_id}_preview.webp"
        full_path = source_dir / f"{wallpaper_id}_full.webp"

        resized(original, THUMB_WIDTH).save(thumb_path, "WEBP", quality=80)
        resized(original, PREVIEW_WIDTH).save(preview_path, "WEBP", quality=85)
        resized(original, FULL_WIDTH).save(full_path, "WEBP", quality=90)

    for path in (thumb_path, preview_path, full_path):
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    print(f"\nCommit {thumb_path.relative_to(REPO_ROOT)} to the repo; "
          f"upload {full_path.name} to the wallpapers-v1 GitHub Release; "
          f"reference {preview_path.name} as previewUrl if hosting it too.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
