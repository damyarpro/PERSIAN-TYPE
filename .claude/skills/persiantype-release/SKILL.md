---
name: persiantype-release
description: Load this skill when cutting or preparing a release of the Persian Type Blender extension — bumping the version in blender_manifest.toml, the bl_info["version"] tuple in __init__.py or the user-facing "Persian Type 0.3" strings in panel.py, editing the [build] paths_exclude_pattern, building or validating the extension zip with "blender --command extension build" / "extension validate", adding or removing a font under fonts/ and its SIL OFL file under fonts/licenses/, updating the bundled-font count or the persiantype-<version>.zip download links in README.md, or publishing a tag and a GitHub release on damyarpro/PERSIAN-TYPE. Also load it for questions about the GPL-3.0-or-later obligation, the existing tag scheme (v3.0, blender5, blender), or what must never be shipped inside the zip.
---

# Cutting a Persian Type release

Repo: `github.com/damyarpro/PERSIAN-TYPE`, working branch `develope`.
Extension id `persiantype`, license `SPDX:GPL-3.0-or-later`, `blender_version_min = "5.0.1"`.

## 1. Version lives in three places — update all of them

| File | Form | Current |
|---|---|---|
| `blender_manifest.toml` | `version = "3.0.0"` (string, SemVer) | 3.0.0 |
| `__init__.py` | `bl_info["version"] = (3, 0, 0)` (tuple) | 3.0.0 |
| `panel.py` | user-facing strings | **"0.3"** — stale |

`panel.py` still says `0.3` in three spots, all of which the user sees:

```
panel.py:6    DEFAULT_PERSIAN_TEXT = "پرشین تایپ 0.3"
panel.py:60   bpy.data.curves.new("Persian Type 0.3", 'FONT')
panel.py:65   bpy.data.objects.new("Persian Type 0.3", curve)
panel.py:101  bl_description = "Create Persian Type 0.3 and start typing in Persian"
```

Also update `bl_info["blender"]` if `blender_version_min` moves. The manifest is what
Blender 4.2+ actually reads; `bl_info` is the legacy dict kept for older loaders. They must
not disagree.

Before tagging, grep for stragglers:

```bash
grep -rn "0\.3\|3\.0\.0\|3, 0, 0" --include="*.py" --include="*.toml" --include="*.md" .
```

## 2. What ships, and what must never ship

`blender_manifest.toml` `[build] paths_exclude_pattern`:

```toml
[build]
paths_exclude_pattern = [
    "__pycache__/",
    "/.git/",
    "/*.zip",
]
```

Never in the zip: `__pycache__/`, `.git/`, previously built `*.zip`, and (add them if you
introduce any) `.claude/`, `.gitignore`, editor and OS junk. A stale `.pyc` inside the
archive is a real source of "the fix didn't take" bug reports. If you add a top-level
directory that is not part of the add-on, add its pattern here in the same commit.

Everything else is shipped, including all of `fonts/` — that is the bulk of the archive.

## 3. Build and validate

```bash
blender --command extension validate "D:/Damyar/Persian type"
blender --command extension build --source-dir "D:/Damyar/Persian type"
```

`validate` checks the manifest schema, the SPDX license id, and version formatting — run it
first and fix everything it reports. `build` produces `persiantype-<version>.zip` in the
source dir (hence the `/*.zip` exclude, so a rebuild does not swallow the previous artifact).

Then install the built zip into a clean Blender profile and smoke-test:
Add Persian Text → type `سلام دنیا` → switch bundled font → Bold → Reset Appearance →
Toggle Direction → Mesh Clean. Disable and re-enable the extension with the console open;
there must be no registration errors.

## 4. Fonts and licenses

`fonts/` currently holds 76 `.ttf` files (LMU family plus Vazirmatn, Estedad, Lalezar,
Markazi Text, Noto Sans Arabic, Noto Naskh Arabic, Amiri, Scheherazade New) and
`fonts/licenses/` holds 8 SIL OFL files, one per family.

When adding a font:

- [ ] Confirm the license permits redistribution and bundling (SIL OFL for everything here).
- [ ] Copy the family's `OFL.txt` into `fonts/licenses/` with a family-identifying name.
- [ ] Verify it actually renders Persian: create a text object with it and confirm shaped
      Persian geometry, not tofu.
- [ ] Update the bundled-font count in `README.md` (currently "76 fonts" / "شامل ۷۶ فونت")
      and the family list in the bundled-fonts section.
- [ ] Check the added size — the zip is font-dominated.

Removing a font is the same checklist in reverse, plus removing its OFL file if no other
bundled family shares it.

## 5. Licensing obligation

The extension is **GPL-3.0-or-later** (`blender_manifest.toml` `license` and the README
license section). Consequences for a release:

- Complete corresponding source must be available for the released binary — publishing the
  same tree on GitHub under the tag satisfies this.
- Any code copied in from elsewhere must be GPL-compatible; note its origin.
- The bundled fonts stay under their own SIL OFL — OFL and GPL coexist here, and the README
  states both. Do not relicense the fonts or drop their license files.

## 6. Tag and publish

Existing tag scheme is inconsistent — `v3.0` is the current release, with older tags
`blender5` and `blender`. Stay with the `v<major>.<minor>` form (`v3.1`, `v4.0`) so the
README links keep working; do not switch to `v3.1.0` without also rewriting every README
link.

The README links to the release **download** by full manifest version, not by tag:

```
https://github.com/damyarpro/PERSIAN-TYPE/releases/download/v3.0/persiantype-3.0.0.zip
```

So the tag (`v3.0`) and the asset filename (`persiantype-3.0.0.zip`) differ by design — the
asset name is whatever `extension build` produced. Update both README occurrences (Persian
section around line 30, English around line 119), the two "download version" links near
line 11, and the release-notes link near line 205.

```bash
git checkout develope
git pull
# version bump + README updates committed first
git tag -a v3.1 -m "Persian Type 3.1"
git push origin v3.1

gh release create v3.1 \
  --repo damyarpro/PERSIAN-TYPE \
  --title "Persian Type 3.1" \
  --notes-file RELEASE_NOTES.md \
  "persiantype-3.1.0.zip"
```

Confirm afterwards that the asset URL in the README resolves.

## Release checklist

- [ ] `blender_manifest.toml` `version` bumped.
- [ ] `__init__.py` `bl_info["version"]` tuple matches, and `bl_info["blender"]` matches
      `blender_version_min`.
- [ ] `panel.py` user-facing "0.3" strings updated to the real version.
- [ ] `grep` finds no stale version strings.
- [ ] `extension validate` clean.
- [ ] `extension build` produces `persiantype-<version>.zip`; inspect it for `__pycache__`,
      `.git`, `.claude`, nested zips.
- [ ] Fresh-profile install smoke test passes, disable/re-enable clean.
- [ ] Font count, family list and both download links in `README.md` are current; every
      bundled family has its OFL under `fonts/licenses/`.
- [ ] Release notes written (features, fixes, known issues — the shaping round-trip defects
      for Persian Kaf and Yeh are still open and should be listed as known issues until fixed).
- [ ] Tag pushed, `gh release create` run with the zip attached, README link verified live.
