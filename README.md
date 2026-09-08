# sanatan-content

Public content repository for the [Sanatan](https://github.com/<GITHUB_USERNAME>/Sanatan) app: wallpapers, ringtones, and Aarti audio, delivered without a custom backend, per `Sanatan_Content_Delivery_Final_Plan.md`.

```
Sanatan Android app
        |
        +--> catalog/*.json in this repo (small, versioned JSON)
        |
        +--> GitHub Releases on this repo (large media files)
```

The app fetches `catalog/version.json` on launch, and only re-fetches a
catalog file whose version number changed. Large media (wallpaper videos,
ringtone/Aarti audio) is never stored in git history -- it's attached to
GitHub Releases and referenced by URL from the catalog.

## Repository layout

```
catalog/            version.json, wallpapers.json, ringtones.json, aartis.json, categories.json
thumbnails/          small images committed directly to the repo (gallery thumbnails, category art)
lyrics/aartis/        Aarti lyrics documents (referenced by aartis.json's lyrics field), once written
schemas/              JSON Schema for each catalog file -- documentation, and CI validation input
scripts/              validate_catalog.py, generate_catalog.py, optimize_wallpapers.py
content-source/       per-type CSV metadata sheets + local staging for source media (git-ignored except the CSVs)
```

## First-time setup (create the real GitHub repo)

This directory is a real content library, already populated with a
bootstrap catalog matching the two live wallpapers and six devotional
tracks currently bundled in the app. It has not been pushed anywhere yet.
To publish it:

```bash
cd /Volumes/extra/WorkSpace/sanatan-content
git init
git add -A
git commit -m "Initial sanatan-content catalog"

# Create the repo on GitHub (pick one):
gh repo create <GITHUB_USERNAME>/sanatan-content --public --source=. --remote=origin --push
# or, without the gh CLI: create an empty public repo named
# "sanatan-content" at github.com/new, then:
git remote add origin https://github.com/<GITHUB_USERNAME>/sanatan-content.git
git branch -M main
git push -u origin main
```

Then replace every `<GITHUB_USERNAME>` placeholder in `catalog/*.json`
(and in `scripts/generate_catalog.py`'s `GITHUB_USERNAME_PLACEHOLDER`) with
your real GitHub username or org, commit, and push again. Run
`python3 scripts/validate_catalog.py` first -- it warns on any remaining
placeholder.

**This repository must stay public** (or the app's anonymous fetch of
`catalog/*.json` and Release assets will fail -- see Security below).

## Adding wallpapers, ringtones, or Aartis

1. Drop source files under `content-source/<type>/`.
2. Add one row per item to that folder's CSV (headers are documented at
   the top of `scripts/generate_catalog.py`).
3. For STATIC wallpapers, run `scripts/optimize_wallpapers.py` first to
   generate the thumbnail/preview/full variants the CSV's `sourceFile`
   should point at.
4. Run `python3 scripts/generate_catalog.py <wallpapers|ringtones|aartis|all>`.
5. Run `python3 scripts/validate_catalog.py` and fix anything it flags.
6. Create (or reuse) the matching GitHub Release --
   `wallpapers-v1` / `live-wallpapers-v1` / `ringtones-v1` / `aartis-v1` --
   and upload each new/changed full-resolution file as a release asset:
   ```bash
   gh release create ringtones-v1 content-source/ringtones/*.mp3 --title "Ringtones v1"
   # or, to add assets to an existing release:
   gh release upload ringtones-v1 content-source/ringtones/new-track.mp3
   ```
7. Commit any new `thumbnails/` files and the regenerated `catalog/*.json`.
8. Bump the relevant `*Version` field and `catalogVersion` in
   `catalog/version.json`.
9. Push. The app picks up the change next time it fetches `version.json`.
10. Sanity-check on a clean install and on an install with an already-
    cached older catalog.

## Rollback

If a published catalog update is bad: `git revert` the bad commit,
bump `catalogVersion` again (never decrease a version number), and push
the corrected catalog. The app always keeps its last-known-good cached
catalog until a new one both downloads and validates successfully.

## Content IDs

Every item has a permanent id, assigned once and never reused or recycled
even after the item is deactivated (`isActive: false`). The plan's
convention for **new** items going forward is `<type>_<deity>_<seq>` (e.g.
`wallpaper_shiva_0001`, `ringtone_hanuman_0001`, `aarti_ganesh_0001`). The
six bootstrap ringtones/aartis in this initial catalog instead reuse the
slug ids already assigned to them inside the Android app itself (e.g.
`ram-kripa-sundar`) so that existing installs' favorites keep matching once
the app switches from bundled to remote-catalog ids for these six items.

## Security

- No GitHub token or credential of any kind belongs in this repo or in the
  Android app -- every URL shipped to the client is public and
  unauthenticated by design.
- Treat every URL in the catalog as public; don't rely on an obscure/
  unlisted URL as access control.
- Keep any real licensing/ownership paperwork for wallpapers, ringtones,
  and Aarti recordings outside this public repo.
