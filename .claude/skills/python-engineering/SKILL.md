---
name: python-engineering
description: Load this skill for any Python work in this repository — editing __init__.py, Persiantype.py or panel.py, adding a module, refactoring a function, handling errors and exceptions, choosing data structures, writing type hints, adding logging, or reviewing Python for correctness and readability. Also load it when a change needs verification and there is no test runner, when deciding whether a helper belongs in the shaping engine or the UI layer, when Unicode string handling is involved, or when a review flags mutable global state, broad except clauses, O(n) loops in a hot path, or a function that has grown past readable size.
---

# Python engineering in this repository

This is a **Blender extension**, not an application. That single fact drives most
of the rules below: the runtime is Blender's embedded CPython, there is no
package manager, no virtualenv, no dependency file and no test runner.

## Runtime constraints — read first

- **Python version is Blender's, not yours.** Blender 5.x embeds CPython 3.11+.
  Write for that. Do not use syntax newer than the embedded interpreter.
- **No third-party imports.** The only imports allowed at runtime are the
  standard library and `bpy` / `bpy.props` / `bpy.types`. Adding `requests`,
  `numpy` or anything from PyPI breaks installation for every user, because the
  extension ships as a zip with no install step.
- **`bpy` does not exist outside Blender.** Any module that imports `bpy` at
  top level cannot be imported by a plain Python process. This is why syntax
  checking is `py_compile`, never `import`.
- **Module-level code runs at add-on load.** Anything expensive at import time
  delays Blender's startup for every user.

## Verification without a test runner

There is no pytest, no CI and no coverage. Verification is layered and manual.
Do all of the steps that apply, and report exactly which ones you ran.

```bash
python -m py_compile __init__.py Persiantype.py panel.py
```

That proves syntax only. It proves nothing about behaviour.

For pure logic that does not touch `bpy` — `link_text`, `unlink_text`,
`swap_lines`, `_font_family_stem` — you can exercise it directly in a throwaway
script by importing the module's functions in isolation, since those functions
do not call `bpy`. Put the script in the scratchpad, never in the repository.

For anything that touches `bpy`, verify inside Blender. The `mcp__Blender__*`
tools are available: `execute_blender_code`, `get_objects_summary`,
`get_screenshot_of_window_as_image`. Use them rather than asking the user to
click through the UI.

**Never report a behavioural change as verified on the strength of a compile.**
Say "compiles, not run" when that is what happened.

## Style rules for this codebase

### Errors

Blender swallows tracebacks in some contexts, so silent failure is genuinely
invisible here.

- `except Exception: pass` is banned in new code. The existing font-loading
  callbacks use it; do not copy the pattern.
- Catch the narrowest exception that can actually occur. `RuntimeError` for
  failed `bpy.ops` calls, `OSError` for filesystem work.
- Inside an operator, surface failures through
  `self.report({'ERROR'}, "...")` and return `{'CANCELLED'}`. The message must
  name the cause, not restate the action.
- Outside an operator, let the exception propagate. Do not invent a return
  sentinel that callers will forget to check.

### State

- **Mutable module-level globals are a known liability here.** `text_buffer`
  and `current_char_index` in `Persiantype.py` are shared across every text
  object in the scene. Do not add more globals. If a new function needs state,
  pass it in and return it out.
- Prefer pure functions. Every function in `Persiantype.py` that does not call
  `bpy` is pure and therefore checkable by hand; keep it that way.

### Strings and Unicode

This codebase is entirely about text, so string handling is not incidental.

- Source files are UTF-8. Persian literals in source must use **Persian** Yeh
  `ی` `U+06CC` and Keheh `ک` `U+06A9`, never Arabic `ي` `U+064A` / `ك` `U+0643`.
- When a literal is a specific codepoint rather than readable text, write it as
  an escape with a comment, not as a raw glyph. `'‌'  # ZWNJ` is
  reviewable; a bare invisible character is not.
- Never assume one character equals one visual glyph. The Lam-Alef ligatures
  occupy one glyph and two buffer slots, and the cursor code compensates for
  exactly that.
- Compare codepoints with `ord()` against hex constants, matching the existing
  convention, rather than against literal presentation-form glyphs.

### Data structures and performance

- `list.insert(0, x)` is O(n). `Persiantype.py` uses it deliberately to build
  reversed output, and that is correct, but do not reach for it casually.
- Watch for accidental quadratic behaviour. `update_text()` and
  `update_visual_cursor_position()` are already O(n) per keystroke; do not add
  a third pass over the buffer.
- Anything called from a UI `draw()` or an `EnumProperty` items callback runs
  on **every redraw**. Filesystem access, font loading and directory scans do
  not belong there without a cache. The `windows_fonts_cache` mechanism in
  `__init__.py` is the pattern to follow.

### Functions and naming

- Prefer readability over cleverness, and small focused functions over long
  ones. Several functions in this codebase are long for historical reasons;
  new code does not have to match that.
- Module-private helpers take a leading underscore, matching
  `_font_family_stem` and `_find_font_weight_file` in `panel.py`.
- Blender classes follow Blender's own convention, not PEP 8:
  `VIEW3D_OT_Something`, `PT_OT_Something`, `VIEW3D_PT_something`.
- Comments explain **why**, never what. The dense positional logic in
  `link_text` is the one place where a "what" comment earns its keep.

### Type hints

The codebase is largely unhinted. Do not run a hinting campaign across it.
Add hints to **new** functions where they clarify a non-obvious contract, as
`normalize_persian_text(s: str) -> str` already does. `bpy` types are poorly
stubbed, so do not fight the type checker over them.

## Minimal change principle

This repository has no tests, so every edit carries risk that only a human will
catch. Make the smallest change that is correct. Do not reformat, reorder
imports, rename variables or "tidy" code adjacent to your change. If you notice
a defect outside your task, report it rather than fixing it.

## Before you finish

1. `python -m py_compile` on every file you touched.
2. No new third-party imports.
3. No new module-level mutable state.
4. No bare or broad `except`.
5. Nothing expensive added to a `draw()` or an enum items callback.
6. State plainly what you verified and what you did not.
