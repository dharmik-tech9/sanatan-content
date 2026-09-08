#!/usr/bin/env python3
"""Generates catalog/{wallpapers,ringtones,aartis}.json from CSV metadata
sheets, per the content-delivery plan's content processing pipeline
(section 13-14). This is the tool to run instead of hand-editing catalog
JSON when adding new content.

Reads three metadata sheets (one per content type) from content-source/,
computes each file's size/duration/dimensions from the actual source file,
and writes the corresponding catalog JSON. Run scripts/validate_catalog.py
afterwards to confirm the result before publishing.

Metadata sheet columns (CSV, header row required):

  wallpapers.csv:  id,type,deityId,categoryId,titleGu,titleHi,titleEn,
                    sourceFile,featured,sortOrder,tags
  ringtones.csv:    id,deityId,titleGu,titleHi,titleEn,sourceFile,featured,
                    sortOrder,tags
  aartis.csv:       id,deityId,titleGu,titleHi,titleEn,sourceFile,coverFile,
                    featured,sortOrder,tags

`sourceFile` is relative to content-source/<wallpapers|ringtones|aartis>/.
`tags` is a single string of space-separated tags (e.g. "shiva mahadev om").

mediaUrl/audioUrl/mediaUrl in the generated catalog point at the GitHub
Release asset location this script expects the file to be uploaded to
(release tag from --release-tag, default matching the plan's naming:
wallpapers-v1/ringtones-v1/aartis-v1/live-wallpapers-v1) -- this script
does not upload anything itself; see README.md's operating procedure.

Requires ffprobe (from ffmpeg) on PATH to read audio/video duration and
video dimensions. Exits with a clear error naming what's missing rather
than writing a partial/incorrect catalog.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "catalog"
SOURCE_DIR = REPO_ROOT / "content-source"
GITHUB_USERNAME_PLACEHOLDER = "<GITHUB_USERNAME>"


def ffprobe_json(path: Path) -> dict:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        sys.exit("ffprobe not found on PATH -- install ffmpeg to run the generator (brew install ffmpeg).")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"ffprobe failed for {path}: {exc.stderr}")
    return json.loads(result.stdout)


def probe_audio(path: Path) -> tuple[int, int]:
    """Returns (durationMs, fileSizeBytes)."""
    info = ffprobe_json(path)
    duration_seconds = float(info["format"]["duration"])
    return round(duration_seconds * 1000), path.stat().st_size


def probe_video(path: Path) -> tuple[int, int, int]:
    """Returns (width, height, fileSizeBytes)."""
    info = ffprobe_json(path)
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    return int(video_stream["width"]), int(video_stream["height"]), path.stat().st_size


def read_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        sys.exit(f"Metadata sheet not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def release_url(release_tag: str, filename: str) -> str:
    return f"https://github.com/{GITHUB_USERNAME_PLACEHOLDER}/sanatan-content/releases/download/{release_tag}/{filename}"


def generate_wallpapers(release_tag_override: str | None) -> None:
    rows = read_rows(SOURCE_DIR / "wallpapers" / "wallpapers.csv")
    entries = []
    for row in rows:
        source_path = SOURCE_DIR / "wallpapers" / row["sourceFile"]
        if not source_path.exists():
            sys.exit(f"wallpapers.csv references missing file: {source_path}")
        width, height, size_bytes = probe_video(source_path) if row["type"] == "LIVE" else _probe_image(source_path)
        release_tag = release_tag_override or ("live-wallpapers-v1" if row["type"] == "LIVE" else "wallpapers-v1")
        entries.append({
            "id": row["id"],
            "type": row["type"],
            "deityId": row["deityId"] or None,
            "categoryId": row["categoryId"],
            "titleGu": row["titleGu"],
            "titleHi": row["titleHi"],
            "titleEn": row["titleEn"],
            "thumbnailUrl": "",
            "previewUrl": "",
            "mediaUrl": release_url(release_tag, source_path.name),
            "width": width,
            "height": height,
            "fileSizeBytes": size_bytes,
            "featured": row["featured"].strip().lower() == "true",
            "isActive": True,
            "sortOrder": int(row["sortOrder"]),
            "tags": row["tags"].split(),
        })
    write_catalog("wallpapers.json", entries)


def _probe_image(path: Path) -> tuple[int, int, int]:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow not installed -- run: pip install Pillow (needed for STATIC wallpaper dimensions).")
    with Image.open(path) as image:
        width, height = image.size
    return width, height, path.stat().st_size


def generate_ringtones(release_tag: str) -> None:
    rows = read_rows(SOURCE_DIR / "ringtones" / "ringtones.csv")
    entries = []
    for row in rows:
        source_path = SOURCE_DIR / "ringtones" / row["sourceFile"]
        if not source_path.exists():
            sys.exit(f"ringtones.csv references missing file: {source_path}")
        duration_ms, size_bytes = probe_audio(source_path)
        entries.append({
            "id": row["id"],
            "deityId": row["deityId"] or None,
            "titleGu": row["titleGu"],
            "titleHi": row["titleHi"],
            "titleEn": row["titleEn"],
            "audioUrl": release_url(release_tag, source_path.name),
            "durationMs": duration_ms,
            "fileSizeBytes": size_bytes,
            "featured": row["featured"].strip().lower() == "true",
            "isActive": True,
            "sortOrder": int(row["sortOrder"]),
            "tags": row["tags"].split(),
        })
    write_catalog("ringtones.json", entries)


def generate_aartis(release_tag: str) -> None:
    rows = read_rows(SOURCE_DIR / "aartis" / "aartis.csv")
    entries = []
    for row in rows:
        source_path = SOURCE_DIR / "aartis" / row["sourceFile"]
        if not source_path.exists():
            sys.exit(f"aartis.csv references missing file: {source_path}")
        duration_ms, size_bytes = probe_audio(source_path)
        cover_file = row.get("coverFile", "").strip()
        entries.append({
            "id": row["id"],
            "deityId": row["deityId"] or None,
            "titleGu": row["titleGu"],
            "titleHi": row["titleHi"],
            "titleEn": row["titleEn"],
            "coverUrl": f"https://raw.githubusercontent.com/{GITHUB_USERNAME_PLACEHOLDER}/sanatan-content/main/thumbnails/aartis/{cover_file}" if cover_file else "",
            "audioUrl": release_url(release_tag, source_path.name),
            "durationMs": duration_ms,
            "fileSizeBytes": size_bytes,
            "lyrics": None,
            "featured": row["featured"].strip().lower() == "true",
            "isActive": True,
            "sortOrder": int(row["sortOrder"]),
            "tags": row["tags"].split(),
        })
    write_catalog("aartis.json", entries)


def write_catalog(filename: str, entries: list[dict]) -> None:
    path = CATALOG_DIR / filename
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path} ({len(entries)} entries)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("content_type", choices=["wallpapers", "ringtones", "aartis", "all"])
    parser.add_argument("--release-tag", default=None, help="Override the GitHub Release tag (default: <type>-v1, or live-wallpapers-v1 for LIVE wallpapers)")
    args = parser.parse_args()

    if args.content_type in ("wallpapers", "all"):
        generate_wallpapers(args.release_tag)
    if args.content_type in ("ringtones", "all"):
        generate_ringtones(args.release_tag or "ringtones-v1")
    if args.content_type in ("aartis", "all"):
        generate_aartis(args.release_tag or "aartis-v1")

    print("\nRun scripts/validate_catalog.py next, then bump catalog/version.json before publishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
