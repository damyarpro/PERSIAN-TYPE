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
panel.py                operators + 3D Viewport N-panel UI
sequencer.py            operators + Video Sequencer N-panel UI (text strips)
fonts/                  76 bundled .ttf files
fonts/licenses/         SIL OFL texts (redistribution requirement)
README.md               bilingual Persian/English documentation
```

**Layering rule.** Dependencies flow in one direction only:

```
panel.py      ──►  Persiantype.py
sequencer.py  ──►  Persiantype.py
__init__.py   ──►  Persiantype.py
__init__.py   ──►  panel.py       (imports __classes__)
__init__.py   ──►  sequencer.py   (calls its register/unregister)
```

`Persiantype.py` must never import `panel.py` or `sequencer.py`, and must never
build UI. Keep the shaping engine free of operators, panels and properties so it
stays testable and replaceable.

`panel.py` and `sequencer.py` are siblings and must not import each other. They
are two independent front ends onto the same engine. If they need to share a
helper, it goes into the engine or gets duplicated — a `sequencer → panel` edge
is not allowed.

`sequencer.py` owns its own class tuple and its own `register()` /
`unregister()`, called from `__init__.py`. Do not add its classes to `panel.py`'s
`__classes__`.

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
8. **Left-to-right runs reverse on read-back.** `unlink_text` reverses the whole
   string, but `link_text` had deliberately kept Latin words and digit groups in
   logical order. So `۱۲۳` returns as `۳۲۱` and `abc` as `cba`. Measured in
   Blender 5.2, not inferred.

Measured round-trip status, Blender 5.2, against the engine as it stands:

| Input | Result |
| --- | --- |
| `لاله` (Lam-Alef) | exact |
| `سلامی` (final Yeh) | exact |
| two-line string | exact |
| `می‌رود` (ZWNJ) | exact |
| `میان` (medial Yeh) | Yeh `U+06CC` → `U+064A` |
| `کتاب کوچک` (Keheh) | Kaf `U+06A9` → `U+FB8E` |
| `۱۲۳ و abc` | digit and Latin runs reversed |

The Yeh degradation is repaired downstream by `normalize_persian_text`, so a
read path that normalizes afterwards survives it. Defects 1 and 8 are not
repairable that way. Any feature that reads shaped text back into logical form
must verify by re-shaping and comparing, and must tell the user when they differ
rather than handing back a corrupted buffer. `sequencer.py` does this.

When you touch code adjacent to one of these, leave it alone and say so.

**Fixed, kept here as history.** The user-facing strings in `panel.py` used to
say `0.3` while the manifest and `bl_info` said `3.0.0`, and that disagreement
shipped inside the `v3.0` package. `panel.py` now derives both the object name
and the sample text from a single `ADDON_VERSION` constant.

---

## 5. Blender API rules

### The official documentation is the reference

**<https://docs.blender.org/>**

Whenever you are unsure about an API, hit a wall, or a new Blender version
changes something, read the documentation. Never answer a Blender API question
from memory, and never guess a property, operator or enum value.

| What you need | Where |
| --- | --- |
| Python API, current release | <https://docs.blender.org/api/current/> |
| Python API, a specific version | `https://docs.blender.org/api/<version>/` — e.g. `.../api/5.2/` |
| A single type | `https://docs.blender.org/api/current/bpy.types.<Type>.html` |
| User manual | <https://docs.blender.org/manual/en/latest/> |

**Fetch it with `curl`.** The site returns `403` to the WebFetch tool but `200`
to `curl`. Verified this session on all four URL shapes above.

Two faster stops before the website, in this order:

1. **The bundled offline API reference.** The `mcp__Blender__search_api_docs`
   tool does a full-text search over Blender's own RST reference with no
   network. Fastest way to find a type or property.
2. **A live Blender instance.** Introspecting `bl_rna.properties` on a real
   object tells you exactly what this build exposes.

### Documentation is not the same as behaviour — measure

Neither the website nor RNA introspection is the final word on **values**.

Measured this session on Blender 5.2: a freshly created `TextStrip` has
`font_size` 60.0 while its RNA default says 0.0, white `color` while RNA says
transparent black, `wrap_width` 1.0 against 0.0, `location` (0.5, 0.5) against
the origin, and `abs_space_line` 60.0 against 1.0. A Reset built on the declared
defaults would have set text to size zero in a transparent colour and looked
like a rendering bug.

So: the docs and introspection tell you **what exists and what it is called**.
Only a live Blender tells you **what it actually does and what value it holds**.
For anything behavioural, run it.

### Blender is available in this environment

`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, with 5.0 and 5.1
alongside it. Run it headless rather than asking the maintainer to click:

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup --python test.py
```

Stage the add-on into a temp folder, `sys.path.insert` that folder, import
`persiantype` and call `register()` directly. Use `--factory-startup` so the
maintainer's installed copy of this add-on does not load instead of your working
tree. Test scripts go in the system temp directory, never in the repository.

### Registration and structure

- **Registration is symmetric.** Every new class goes into `__classes__` in
  `panel.py` and is unregistered in reverse order. A class registered but not
  unregistered breaks add-on reload. `sequencer.py` keeps its own class tuple
  and its own register/unregister pair instead.
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

1. `blender_manifest.toml` → `version`, three-part, e.g. `"3.0.0"`
2. `__init__.py` → `bl_info["version"]` tuple, e.g. `(3, 0, 0)`
3. `panel.py` → `ADDON_VERSION`, two-part display form, e.g. `"3.0"`

`ADDON_VERSION` feeds `DEFAULT_TEXT_OBJECT_NAME` and `DEFAULT_PERSIAN_TEXT`, so
that module needs exactly one edit. Grep for the old version number afterwards
to confirm nothing was missed.

Build with `blender --command extension build`, confirm the zip excludes
`__pycache__`, `.git` and other zips, then publish with `gh release create`
against `damyarpro/PERSIAN-TYPE`. Existing tag scheme: `v3.0`, older
`blender5`, `blender`.

### Distribution channels

There are **two**, and they are separate:

1. **GitHub Releases** — the zip attached to a tag, for direct download and for
   the README link.
2. **Blender Extensions Platform** (`extensions.blender.org`) — Blender's own
   upload and review system. It has its own submission flow, its own review
   queue and its own versioning checks. It is not driven from this repository
   and is not something a tool here can push to.

A GitHub release is therefore **not** a complete release. Publishing to
Blender's platform is a separate, maintainer-performed step.

### Release gating — standing rule

**Never build, tag, publish a release, deploy, or merge on your own initiative.
Each of those happens only when the maintainer asks for it by name, in that
message.**

- "commit" and "push to a working branch" are ordinary work and do not need a
  fresh instruction each time.
- Building an extension zip, creating a tag, `gh release create`, uploading an
  asset, merging into `main`, and anything that reaches
  `extensions.blender.org` all require an explicit, current instruction.
- Approval for one release never carries over to the next.
- When a release is asked for, follow the procedure above in full. Do not
  shorten it because a previous release went smoothly.

You may always **prepare** a release without being asked: audit the version
strings, check license coverage, draft the notes. Prepare, show the maintainer
exactly what would be published, and stop there.

---

## 9. Branches and commits

- `main` — released state. Never commit directly, and never merge into it
  without an explicit instruction for that merge.
- `develope` — integration branch for current work. This is where commits and
  pushes land by default.
- `version3` — legacy branch, retained for history.
- Feature work branches off `develope`.

Commit messages describe the behavior change, not the file list. Do not commit
or push unless asked.

### Line endings — check the diff size

`panel.py`, `__init__.py` and `Persiantype.py` have **mixed** line endings in
the repository, and `core.autocrlf` is `true` here. An editor that rewrites a
whole file normalizes them, which turns a four-line change into a six-hundred
line diff and buries the real edit.

After editing any of the three modules, run `git --no-pager diff --stat` and
confirm the changed-line count matches what you actually changed. If it does
not, restore with `git checkout HEAD -- <file>` and re-apply the edit as a
targeted byte replacement instead of a full-file rewrite. Do not "fix" the
mixed endings as a side effect of an unrelated change.

---

## 10. Language and text conventions

- **Code, identifiers, comments and commit messages:** English.
- **User-facing strings in the Blender UI:** English labels, because Blender's
  own UI is English and mixed-direction labels render badly in its font system.
  Operator `report()` messages may be Persian where the existing code already
  is; stay consistent within a file.
- Persian text in source must use **Persian** Yeh `ی` `U+06CC` and Keheh `ک`
  `U+06A9`, never the Arabic `ي` `U+064A` / `ك` `U+0643`.

### Documentation standard — every description surface

**Every description is bilingual, everywhere. No exceptions among these:**

| Surface | Bilingual |
| --- | --- |
| `README.md` | yes |
| GitHub release notes | yes |
| Repository About / description | yes |
| Issue descriptions | yes |
| Pull request descriptions | yes |

The `v3.0` notes are the reference example for shape; the two older releases
predate the standard and are not models.

**Persian first.** Persian section, then English, in that order, under
`## فارسی` and `## English`. The two halves carry the same facts. Update both or
neither — a change to one half alone is an incomplete change. Where a surface is
too short for headings, such as the repository About line, put the Persian
sentence first and the English sentence after it, separated by a line break or a
`|`.

**Two deliberate exceptions, both technical, not stylistic.**

1. **Commit messages stay English**, per §10's first rule. They are developer
   history, not a description a user reads.
2. **Blender UI strings stay English** — `bl_label`, `bl_description`, panel
   labels. Blender's own interface is English, and mixed-direction text renders
   badly in its font system, so a bilingual tooltip degrades the product rather
   than documenting it. This is the same reason the existing 3D panel is English.

If either exception should change, it needs an explicit decision, because both
were chosen for a reason rather than by neglect.

**Never translate Blender's interface terms.** Anything the user reads inside
Blender stays in English inside Persian prose: `Add Text`, `Paste`,
`Mesh Clean`, `Edit Mode`, `3D Cursor`, `Text Object`, `Clipboard`, `Offset`,
`Extrude`, `Bevel`, `Curve Resolution`, `Backspace`, `Delete`. Translating them
breaks the reader's ability to find the control.

**Digits.** Latin digits for anything a machine also reads — version numbers,
file names, paths, measurements, code: `5.0.1`, `persiantype-3.0.0.zip`,
`0.01401 m`. Persian digits for plain counts in Persian prose: `۷۶ فونت`,
`۱۰ فایل فونت`. A release *title* uses Persian digits in its Persian half:
`Persian Type 3.0 | پرشین تایپ ۳.۰`.

**Feature bullets name the control first, in bold.** `- **Add Text:** ساخت
فوری متن راست‌چین…`. One line per feature, describing what the user gets, not
how it is implemented.

**The install path is fixed boilerplate.** Always
`Edit > Preferences > Get Extensions > Install from Disk`, and always name the
exact asset file. Do not paraphrase it.

**Claims need evidence.** A `Validation` section may list only what was
actually run, in this session, with the tool that ran it. If Blender was not
available, the notes say so instead of asserting that tests passed. Never carry
a validation claim forward from a previous release.

**Every release note carries a Known Issues section** listing the defects in
§4 that are still present. A release that silently ships known defects is a
defect in the notes.

### Release notes skeleton

```
Title:  Persian Type <x.y> | پرشین تایپ <x.y in Persian digits>

## فارسی
<one sentence: what this version gives the user>
### قابلیت‌های جدید
- <bold control name>: <what it does>
### مشکلات شناخته‌شده
- <open defects from §4>
<install line naming the exact zip>

## English
<mirror of the above>
### New features
### Known issues
<install line>

### Validation
<only what was actually run>
```

### Known documentation gaps

Do not treat these as settled; they are open and should be raised when touching
the surface they affect.

1. **No `LICENSE` file at the repository root.** The manifest declares
   `SPDX:GPL-3.0-or-later` and the README shows a GPL-3.0 badge, but GitHub
   reports no detected license because the text is absent. GPL-3.0 requires the
   license text to travel with the work.
2. **The About text is one run-on sentence** with the maintainer email appended
   with no separator, and the repository has no homepage and no topics set.
3. **The `blender` and `blender5` releases put English before Persian** and
   carry no installable zip. They predate this standard.

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
