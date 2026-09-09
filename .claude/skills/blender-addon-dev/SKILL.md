---
name: blender-addon-dev
description: Load this skill for any change to the Blender integration layer of the Persian Type add-on — adding or editing an operator (the VIEW3D_OT_* and PT_OT_* classes in panel.py and __init__.py), editing PersiantypePanel or its N-panel layout, adding a property to PersiantypePreferences or PT_FontItem, touching the persian_font / windows_font EnumProperty callbacks get_font_items and get_windows_font_items, editing the __classes__ list at the bottom of panel.py, editing register() / unregister() or the Ctrl+F1 keymap in __init__.py, or working on the VIEW3D_OT_PersianTextMode modal operator. Also load it when an add-on fails to enable, a class stays registered after disable, an operator is greyed out or crashes on a non-FONT object, the blend file bloats with font datablocks, or a UI enum shows garbled entries.
---

# Blender add-on development for Persian Type

Target: Blender 4.2+ extension format, `blender_version_min = "5.0.1"`. `bpy` cannot be
imported outside Blender, so nothing here is verifiable by running the module directly.

## Registration chain

```
panel.py  __classes__ = [ ...operators..., PersiantypePanel ]
                    |
                    v
__init__.py  from .panel import __classes__
             register()   -> register_class() for prefs/property groups,
                             then for cls in __classes__, then keymap
             unregister() -> reverse order
```

`register()` in `__init__.py` (line ~409) registers, in this order:
`PT_FontItem`, `PersiantypePreferences`, `PT_OT_RemoveSavedFont`, `PT_OT_ScanWindowsFonts`,
`PT_OT_ChooseCustomFontsDir`, the `bpy.types.Scene` properties (`persian_font`,
`windows_font`), `VIEW3D_OT_PersianTextMode`, then every class in `__classes__`, then the
`Ctrl+F1` keymap item in the `"Window"` keymap (appended to the module-level `keymaps`
list), then `PT_OT_PastePersianNormalize`.

Rules:

- A new operator or panel goes in **`panel.py.__classes__`** — that is the manifest. A class
  not in the list is never registered and its `bl_idname` will not exist at runtime.
- A class registered by hand in `register()` **must** be unregistered by hand in
  `unregister()`, in **reverse order**. `unregister()` today removes the keymap items first,
  clears `keymaps`, then unwinds the manual classes in reverse. Keep that symmetry;
  asymmetry leaves stale classes behind and breaks add-on disable/re-enable.
- Scene properties added with `bpy.types.Scene.x = ...` must be deleted with
  `del bpy.types.Scene.x` in `unregister()`.
- Every keymap item created must be recorded in `keymaps` and removed on unregister.

## Naming conventions

- `bl_idname` for operators: `"<category>.<snake_case>"`, and the class name must match
  Blender's convention — `VIEW3D_OT_ChangePersianFont` ↔ `view3d.change_persian_font`.
  Existing prefixes here: `VIEW3D_OT_*` (viewport actions) and `PT_OT_*` (preferences-side
  actions, e.g. `PT_OT_ScanWindowsFonts`). Panels use `PersiantypePanel` with
  `bl_category = "Persian type"` in the 3D-view N-panel.
- `bl_label` is user-facing text; `bl_description` is the tooltip. Both are read by users, so
  keep them short and consistent with the existing wording.
- `bl_options`: add `{'REGISTER', 'UNDO'}` to any operator that mutates scene data
  (object creation, font change, mesh clean) so it lands in the undo stack. Do **not** add
  `'UNDO'` to the modal typing operator — `Ar.update_text()` already rewrites the body every
  keystroke and pushing an undo step per key makes the stack useless.

## poll() is not optional

Most operators here assume an active FONT object, and several assume EDIT mode. Without a
`poll()` they are clickable on a mesh or with nothing selected and will raise inside
`execute()`.

```python
@classmethod
def poll(cls, context):
    obj = context.active_object
    return obj is not None and obj.type == 'FONT'
```

Add `and context.mode == 'EDIT_TEXT'` for anything that drives `bpy.ops.font.*`
(the cursor and buffer operations in `Persiantype.py` all do).
`VIEW3D_OT_MeshClean` is the opposite case: it converts FONT → MESH, so its `poll` must
accept FONT objects in OBJECT mode and handle a multi-object selection.

## Add-on preferences access

The codebase uses two different keys and this is a real trap:

- `__init__.py` uses `addon_key = __name__` (lines 192, 226, 276, 337, 358)
- `panel.py` uses `addon_key = __package__` (lines 365, 476, 545)

For the package `__init__.py` these are the same string, but inside a submodule
`__name__` is `persiantype.panel` while `__package__` is `persiantype`. Only `__package__`
is correct in a submodule. Always write:

```python
addon_key = __package__ or __name__
container = bpy.context.preferences.addons.get(addon_key)
if container is None:
    self.report({'ERROR'}, "Persian Type preferences not found")
    return {'CANCELLED'}
prefs = container.preferences
```

Never index `addons[key]` — it raises `KeyError` when the extension is installed under a
different id (e.g. `bl_ext.user_default.persiantype`). Always `.get()` and handle `None`.

## EnumProperty items-callback pitfall

`get_font_items` and `get_windows_font_items` feed `bpy.types.Scene.persian_font` and
`bpy.types.Scene.windows_font`. Two known hazards, both live in this codebase:

1. **String lifetime.** Blender does not keep a reference to the strings inside the list a
   callback returns. Building a fresh list of freshly-built Python strings every call is the
   classic cause of garbled or empty enum entries and hard crashes. Cache the list in a
   module-level global and return the *same* list object.
2. **Cost in a redraw path.** These callbacks are invoked on every UI redraw. Calling
   `bpy.data.fonts.load()` there loads a font datablock per file per redraw, which bloats
   the .blend file and stalls the panel. Font loading belongs in an operator's `execute()`,
   never in an items callback or a `draw()`.

Also: `draw()` must be side-effect free. No `bpy.ops`, no `bpy.data.*.new/load`, no writes to
properties.

Windows font scanning depends on `%WINDIR%`, so `PT_OT_ScanWindowsFonts` and
`VIEW3D_OT_LoadWindowsFont` are Windows-only. Guard them (`sys.platform`) rather than letting
them fail on Linux/macOS; the bundled `fonts/` folder and `custom_fonts_dir` are the
cross-platform path.

## Modal operator discipline

`VIEW3D_OT_PersianTextMode` hijacks keyboard input in the 3D viewport and routes keys to the
shaping engine. Requirements for any change to it:

- `invoke()` must call `context.window_manager.modal_handler_add(self)` and return
  `{'RUNNING_MODAL'}`.
- `modal()` must return `{'RUNNING_MODAL'}` while active, `{'PASS_THROUGH'}` for events it
  does not own (navigation, mouse), and `{'FINISHED'}` or `{'CANCELLED'}` on exit — and the
  exit branch must reset the class flag `_is_running = False`.
  **Today it never does**, so once the operator has run, a second Ctrl+F1 is refused for the
  rest of the session. If you touch this class, fix or at least do not deepen that.
- Consuming an event you do not handle breaks Blender's own shortcuts. Only claim
  `BACK_SPACE`, `DEL`, `HOME`, `END`, arrows, `RET`, `TAB`, Ctrl+V / Shift+Insert, and
  events with a non-empty `event.unicode`.
- Run pasted text through `normalize_persian_text` before it reaches `Ar.text_buffer`.

## Verifying a change

`bpy` is unavailable outside Blender, so there is no unit-test path today (no tests, no CI).
Two levels of verification:

```bash
# 1. syntax only — catches typos, nothing else
python -m py_compile "D:/Damyar/Persian type/__init__.py" \
                     "D:/Damyar/Persian type/panel.py" \
                     "D:/Damyar/Persian type/Persiantype.py"
```

2. **Live, inside Blender.** The Blender MCP tools are available in this environment:

- `mcp__Blender__execute_blender_code` — re-register the add-on, call an operator by
  `bl_idname`, inspect `bpy.context.preferences.addons`, read back
  `bpy.context.active_object.data.body` and `Ar.text_buffer`.
- `mcp__Blender__get_objects_summary` — confirm the FONT object was created, named and
  typed as expected.
- `mcp__Blender__get_screenshot_of_window_as_image` — the only way to actually see whether
  the shaped Persian text renders correctly and whether the N-panel draws.

Live check for a registration change:

```python
import bpy
print(hasattr(bpy.types, "VIEW3D_OT_add_persian_text"))
print([k for k in bpy.context.preferences.addons.keys() if "persiantype" in k])
```

## Before you ship

- [ ] New class is in `panel.py.__classes__`, or hand-registered **and** hand-unregistered in
      reverse order.
- [ ] Scene properties and keymap items are removed in `unregister()`.
- [ ] Disable → re-enable the add-on in Preferences with no console errors.
- [ ] Every operator has a `poll()` matching its assumptions (FONT type, EDIT mode, selection).
- [ ] No `bpy.data.fonts.load()` and no `bpy.ops` inside `draw()` or an enum items callback.
- [ ] `__package__ or __name__` used for preferences lookup, with a `None` guard.
- [ ] `py_compile` clean on all three modules.
- [ ] Live check in Blender: create text, type Persian, switch font, Mesh Clean, screenshot.
- [ ] Shaping touched? Also follow the `persian-text-shaping` skill's verification checklist.
