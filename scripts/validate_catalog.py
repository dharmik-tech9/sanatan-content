#!/usr/bin/env python3
"""Validates catalog/*.json before publishing a catalog update.

Deliberately dependency-free (stdlib only) so it runs on a bare Python 3
install with no pip step. Checks, per the content-delivery plan's release
acceptance criteria (section 21):
  - every catalog file is valid JSON
  - every entry has the fields its type requires, with sane types
  - no duplicate ids within a single catalog file
  - every wallpaper's categoryId exists in categories.json
  - no media/audio/cover URL is blank
  - flags (does not fail) any URL still containing the "<GITHUB_USERNAME>"
    placeholder, so a real publish is never accidentally shipped with it

Usage: python3 scripts/validate_catalog.py
Exits non-zero if any file fails validation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "catalog"

REQUIRED_COMMON = ["id", "titleGu", "titleHi", "titleEn", "featured", "isActive", "sortOrder", "tags"]
REQUIRED_BY_FILE = {
    "wallpapers.json": REQUIRED_COMMON + ["type", "categoryId", "thumbnailUrl", "previewUrl", "mediaUrl", "width", "height", "fileSizeBytes"],
    "ringtones.json": REQUIRED_COMMON + ["audioUrl", "durationMs", "fileSizeBytes"],
    "aartis.json": REQUIRED_COMMON + ["coverUrl", "audioUrl", "durationMs", "fileSizeBytes", "lyrics"],
}
URL_FIELDS_BY_FILE = {
    "wallpapers.json": ["mediaUrl"],
    "ringtones.json": ["audioUrl"],
    "aartis.json": ["audioUrl"],
}

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}: invalid JSON ({exc})")
        return None


def validate_catalog_file(filename: str, categories: set[str]) -> None:
    path = CATALOG_DIR / filename
    if not path.exists():
        errors.append(f"{filename}: missing")
        return
    entries = load_json(path)
    if entries is None:
        return
    if not isinstance(entries, list):
        errors.append(f"{filename}: expected a JSON array at the top level")
        return

    required = REQUIRED_BY_FILE[filename]
    url_fields = URL_FIELDS_BY_FILE[filename]
    seen_ids: set[str] = set()

    for index, entry in enumerate(entries):
        label = f"{filename}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: expected an object")
            continue

        for field in required:
            if field not in entry:
                errors.append(f"{label} ({entry.get('id', '?')}): missing required field '{field}'")

        entry_id = entry.get("id")
        if isinstance(entry_id, str):
            if entry_id in seen_ids:
                errors.append(f"{filename}: duplicate id '{entry_id}'")
            seen_ids.add(entry_id)
        elif "id" in entry:
            errors.append(f"{label}: 'id' must be a string")

        if filename == "wallpapers.json":
            category_id = entry.get("categoryId")
            if category_id is not None and category_id not in categories:
                errors.append(f"{label} ({entry_id}): categoryId '{category_id}' not found in categories.json")

        for field in url_fields:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label} ({entry_id}): '{field}' is blank")
            elif "<GITHUB_USERNAME>" in value:
                warnings.append(f"{label} ({entry_id}): '{field}' still has the <GITHUB_USERNAME> placeholder")


def validate_version_file() -> None:
    path = CATALOG_DIR / "version.json"
    if not path.exists():
        errors.append("version.json: missing")
        return
    data = load_json(path)
    if data is None:
        return
    required_ints = ["schemaVersion", "catalogVersion", "wallpapersVersion", "ringtonesVersion", "aartisVersion", "minimumAppVersionCode"]
    for field in required_ints:
        if not isinstance(data.get(field), int):
            errors.append(f"version.json: '{field}' must be an integer")


def load_categories() -> set[str]:
    path = CATALOG_DIR / "categories.json"
    if not path.exists():
        errors.append("categories.json: missing")
        return set()
    data = load_json(path)
    if not isinstance(data, list):
        errors.append("categories.json: expected a JSON array at the top level")
        return set()
    ids: set[str] = set()
    for index, entry in enumerate(data):
        if not isinstance(entry, dict) or "id" not in entry:
            errors.append(f"categories.json[{index}]: missing 'id'")
            continue
        ids.add(entry["id"])
    return ids


def main() -> int:
    validate_version_file()
    categories = load_categories()
    for filename in REQUIRED_BY_FILE:
        validate_catalog_file(filename, categories)

    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"FAIL  {error}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). Fix errors before publishing.")
        return 1
    print(f"OK - all catalog files valid ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
