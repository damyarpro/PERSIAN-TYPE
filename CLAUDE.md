# Persian Type — Project Rules

Blender extension that lets users type, paste, style and mesh Persian/Arabic text
directly inside Blender. Repository: `damyarpro/PERSIAN-TYPE`.

These rules are project law. They sit on top of the global engineering rules and
override them wherever the two disagree.

---

## 1. What this project is

| Item | Value |
| --- | --- |
| Kind | Blender extension (manifest-based) + legacy `bl_info` add-on |
| Extension id | `persiantype` |
| Version | `3.0.0` |
| Minimum Blender | `5.0.1` |
| License | GPL-3.0-or-later |
| Language | Python, `bpy` only, no third-party runtime dependencies |
| UI location | 3D Viewport, N-panel, tab **Persian type** |

There is **no package manager, no build system and no test runner**. The whole
extension is three Python modules plus a font folder.

---

## 2. Module map and ownership

```
blender_manifest.toml   extension metadata + build excludes
__init__.py             registration, preferences, modal keyboard operator
Persiantype.py          shaping engine (pure logic, no UI)
panel.py                operators + N-panel UI
fonts/                  76 bundled .ttf files
fonts/licenses/         SIL OFL texts (redistribution requirement)
README.md               bilingual Persian/English documentation
```

**Layering rule.** Dependencies flow in one direction only:

```
panel.py  ──►  Persiantype.py
__init__.py ──►  Persiantype.py
__init__.py ──►  panel.py   (imports __classes__)
```

`Persiantype.py` must never import `panel.py` and must never build UI.
Keep the shaping engine free of operators, panels and properties so it stays
testable and replaceable.

---

## 3. The central design constraint — read before touching text

Blender's `FONT` objects have **no HarfBuzz shaping and no bidi algorithm**.
Everything in this add-on follows from that.

- The **logical string** lives in the Python global `Persiantype.text_buffer`,
  a list of base characters in reading order.
- The **visual string** lives in `curve.body`: already shaped into Unicode
  presentation forms and already reversed right-to-left.
- `link_text()` goes logical → visual. `unlink_text()` goes visual → logical.
  `swap_lines()` repairs line order after the reversal.

**Invariant.** For any logical buffer `b`:

```
unlink_text(swap_lines(link_text(b)))  ==  b
```

Any change to shaping must preserve this round trip **in both directions**.
Verify manually; there is no test harness yet.

Never write raw Persian text straight into `curve.body`, and never mutate
`curve.body` without also updating `text_buffer` and `current_char_index`.
The two go out of sync silently and the corruption only surfaces later.

---

## 4. Known defects — do not "fix" them incidentally

These are real, confirmed and currently load-bearing. Fix them only in a
dedicated change with its own verification, never as a drive-by edit.

1. **Kaf does not round-trip.** `Persiantype.py:485` maps Keheh presentation
   forms `U+FB8E..FB91` back to `'ﮎ'`, which is `U+FB8E` itself, not base
   `'ک'` `U+06A9`.
2. **Persian Yeh degrades to Arabic Yeh.** Initial/medial Persian Yeh shapes to
   `U+FEF3`/`U+FEF4`, which `unlink_text` maps back to `'ي'`. `panel.py`
   works around this by re-seeding `Ar.text_buffer` after `Ar.init()`.
3. **Global editing state.** `text_buffer` and `current_char_index` are module
   globals shared by every text object. Switching objects without calling
   `Ar.init()` desynchronizes the buffer.
4. **O(n) per keystroke.** `update_text()` rewrites the entire body via
   `select_all` + `delete` + `text_insert`, destroying per-character
   `body_format`. `update_visual_cursor_position()` issues `bpy.ops.font.move`
   in loops proportional to text length.
5. **Modal never terminates.** `VIEW3D_OT_PersianTextMode._is_running` is never
   reset and the modal never returns `FINISHED` or `CANCELLED`.
6. **Font enums are expensive.** `get_font_items` and `get_windows_font_items`
   call `bpy.data.fonts.load()` for every file on every redraw, bloating the
   blend file with font datablocks.
7. **Windows-only font browsing.** The scanner depends on `%WINDIR%`.
8. **Version strings disagree.** Manifest and `bl_info` say `3.0.0`; the
   user-facing strings in `panel.py` still say `0.3`.

When you touch code adjacent to one of these, leave it alone and say so.

---

## 5. Blender API rules

- **Registration is symmetric.** Every new class goes into `__classes__` in
  `panel.py` and is unregistered in reverse order. A class registered but not
  unregistered breaks add-on reload.
- **Every operator gets a `poll()`.** If it assumes an active `FONT` object or
  `EDIT` mode, `poll()` must say so. Do not discover it with an exception.
- **Naming.** `bl_idname` is `view3d.*` for viewport operators and `pt.*` for
  add-on utilities. Follow the existing split; do not invent a third prefix.
- **Preferences access** goes through
  `bpy.context.preferences.addons.get(__package__)` in `panel.py` and
  `__name__` in `__init__.py`. Both resolve to the same package. Keep them
  consistent with the file you are editing.
- **EnumProperty item callbacks** must stay cheap. They run on every redraw.
  Never load font datablocks, scan directories or hit the filesystem in a hot
  callback without a cache.
- **`bpy.ops` is a last resort.** Prefer `bpy.data` and direct property
  assignment. Operators depend on context and fail in ways that are hard to
  trace.
- **Never swallow exceptions.** `except Exception: pass` is banned in new code.
  Report through `self.report({'ERROR'}, ...)` with a message that names the
  cause.

---

## 6. Fonts

- Bundled fonts are **tracked binaries**. Never add one to `.gitignore`.
- Every bundled family **must** ship its license under `fonts/licenses/`.
  Adding a font without its OFL file is a redistribution violation.
- Adding or removing a font means updating the font count in `README.md`
  (currently 76) in **both** the Persian and English sections.

---

## 7. Verification — there is no CI

Because `bpy` cannot be imported outside Blender, verification is manual and
layered. Do all four before calling work done:

1. **Syntax.** `python -m py_compile __init__.py Persiantype.py panel.py`
2. **Manifest.** `blender --command extension validate`
3. **Live smoke test in Blender.** Enable the add-on, then exercise: Add Text →
   type Persian → Backspace → Delete → arrow keys → Enter for a second line →
   Paste → Toggle Text Direction → Change Font → Mesh Clean.
4. **Shaping strings.** Any change to `Persiantype.py` must be checked against
   at minimum: `سلام دنیا`, `لاله` (Lam-Alef ligature), `کتاب کوچک` (Kaf),
   `۱۲۳ و abc` (mixed direction), and a two-line string.

The `mcp__Blender__*` tools are available in this environment for live
verification. Use `execute_blender_code`, `get_objects_summary` and
`get_screenshot_of_window_as_image` rather than asking the user to test by hand.

Report what you actually ran. If you only compiled, say you only compiled.

---

## 8. Releasing

Version lives in **three** places and they must move together:

1. `blender_manifest.toml` → `version`
2. `__init__.py` → `bl_info["version"]` tuple
3. `panel.py` → `DEFAULT_PERSIAN_TEXT` and the created object names

Build with `blender --command extension build`, confirm the zip excludes
`__pycache__`, `.git` and other zips, then publish with `gh release create`
against `damyarpro/PERSIAN-TYPE`. Existing tag scheme: `v3.0`, older
`blender5`, `blender`.

---

## 9. Branches and commits

- `main` — released state. Never commit directly.
- `develope` — integration branch for current work.
- Feature work branches off `develope`.

Commit messages describe the behavior change, not the file list. Do not commit
or push unless asked.

---

## 10. Language and text conventions

- **Code, identifiers, comments and commit messages:** English.
- **User-facing strings in the Blender UI:** English labels, because Blender's
  own UI is English and mixed-direction labels render badly in its font system.
  Operator `report()` messages may be Persian where the existing code already
  is; stay consistent within a file.
- **README:** bilingual, Persian section first, then English. Update both or
  neither.
- Persian text in source must use **Persian** Yeh `ی` `U+06CC` and Keheh `ک`
  `U+06A9`, never the Arabic `ي` `U+064A` / `ك` `U+0643`.

---

## 11. Delegation

Project agents live in `.claude/agents/` and project skills in
`.claude/skills/`. Route work to the agent that owns the layer:

| Work | Agent |
| --- | --- |
| `Persiantype.py`, shaping, cursor, buffer | `rtl-shaping-engineer` |
| `panel.py` operators and N-panel UI | `blender-ui-engineer` |
| `__init__.py`, registration, preferences, keymaps, modal | `blender-addon-engineer` |
| `fonts/`, licenses, manifest, release packaging | `font-and-release-curator` |

Give parallel agents **disjoint file ownership**. These four modules are tightly
coupled, so two agents must never hold the same file at once.
