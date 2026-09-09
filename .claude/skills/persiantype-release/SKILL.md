---
name: persiantype-release
description: Load this skill when cutting or preparing a release of the Persian Type Blender extension — bumping the version in blender_manifest.toml, the bl_info["version"] tuple in __init__.py or the ADDON_VERSION constant in panel.py, editing the [build] paths_exclude_pattern, building or validating the extension zip with "blender --command extension build" / "extension validate", adding or removing a font under fonts/ and its SIL OFL file under fonts/licenses/, updating the bundled-font count or the persiantype-<version>.zip download links in README.md, or writing release notes and publishing a tag and a GitHub release on damyarpro/PERSIAN-TYPE. Also load it for the bilingual Persian-first release-notes format, the mandatory Known Issues and Validation sections, the GPL-3.0-or-later obligation and the missing root LICENSE file, the existing tag scheme (v3.0, blender5, blender), or what must never be shipped inside the zip.
---

# Cutting a Persian Type release

Repo: `github.com/damyarpro/PERSIAN-TYPE`, working branch `develope`.
Extension id `persiantype`, license `SPDX:GPL-3.0-or-later`, `blender_version_min = "5.0.1"`.

## 0. Gating — read before doing anything here

**Never build, tag, publish, deploy or merge on your own initiative.** Each of
those happens only when the maintainer asks for it by name, in that message.
Approval for one release never carries over to the next, and a smooth previous
release is not permission for the current one.

| Action | Needs a fresh instruction? |
|---|---|
| Auditing versions, licenses, drift | No — always allowed |
| Drafting release notes | No — always allowed |
| Editing version strings | Yes |
| `blender --command extension build` | Yes |
| Creating a tag, `gh release create`, uploading an asset | Yes |
| Merging into `main` | Yes |
| Anything reaching `extensions.blender.org` | Yes, and it is manual |

You may always **prepare**: audit, verify, draft, and show the maintainer
exactly what would be published. Then stop.

### Two distribution channels

1. **GitHub Releases** — the zip attached to a tag. This is what the README
   links to.
2. **Blender Extensions Platform** (`extensions.blender.org`) — Blender's own
   upload and review system, with its own submission flow and review queue. It
   is not driven from this repository and no tool here can push to it. The
   maintainer performs that step by hand.

A GitHub release alone is **not** a complete release.

## 1. Version lives in three places — update all of them

| File | Form | Current |
|---|---|---|
| `blender_manifest.toml` | `version = "3.3.0"` (string, SemVer) | 3.3.0 |
| `__init__.py` | `bl_info["version"] = (3, 3, 0)` (tuple) | 3.3.0 |
| `panel.py` | `ADDON_VERSION = "3.3"` (two-part display form) | 3.3 |

`panel.py` needs exactly one edit. `ADDON_VERSION` feeds both user-facing
strings, so they cannot drift apart again:

```
panel.py:10  ADDON_VERSION = "3.3"
panel.py:11  DEFAULT_TEXT_OBJECT_NAME = f"Persian Type {ADDON_VERSION}"
panel.py:12  DEFAULT_PERSIAN_TEXT     = f"پرشین تایپ {ADDON_VERSION}"
```

Historical note: these strings said `0.3` while the manifest said `3.0.0`, and
that disagreement shipped inside the `v3.0` package. Verify the grep below
actually comes back empty before tagging.

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

The root `LICENSE` file was added in 3.2 and ships inside the package. Keep it there; the
GPL requires the license text to travel with the work.

## 5a. Writing the release notes

The full documentation standard is in `CLAUDE.md` §10. The parts that bite here:

- **Persian first, then English**, same facts in both. The `v3.0` notes are the reference;
  `blender` and `blender5` predate the standard and put English first — do not copy them.
- **Title form:** `Persian Type <x.y> | پرشین تایپ <x.y in Persian digits>`.
- **Blender UI terms stay English** inside Persian prose — `Add Text`, `Mesh Clean`,
  `Edit Mode`, `3D Cursor`.
- **Digits:** Latin for versions, filenames, paths and measurements (`5.0.1`,
  `persiantype-3.0.0.zip`, `0.01401 m`); Persian digits for plain counts (`۷۶ فونت`).
- **Install line is fixed boilerplate:** `Edit > Preferences > Get Extensions >
  Install from Disk`, naming the exact asset.
- **Known Issues section is mandatory**, listing the defects from `CLAUDE.md` §4 that are
  still present. The `v3.0` notes omitted it and shipped two confirmed shaping defects
  undocumented — do not repeat that.
- **A `Validation` section may list only what actually ran in this session.** If Blender was
  unavailable, say so. Never carry a validation claim forward from a previous release; the
  `v3.0` notes assert manifest validation and Blender 5.1.2 end-to-end tests with no
  evidence trail.

## 6. Tag and publish

Existing tag scheme is inconsistent — `v3.0` is the current release, with older tags
`blender5` and `blender`. Stay with the `v<major>.<minor>` form (`v3.1`, `v4.0`) so the
README links keep working; do not switch to `v3.1.0` without also rewriting every README
link.

The README links to the release **download** by full manifest version, not by tag:

```
https://github.com/damyarpro/PERSIAN-TYPE/releases/download/v3.3/persiantype-3.3.0.zip
```

So the tag (`v3.3`) and the asset filename (`persiantype-3.3.0.zip`) differ by design — the
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
