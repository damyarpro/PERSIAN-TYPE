bl_info = {
    "name": "Persiantype",
    "author": "DAMYAR",
    "version": (3, 1, 0),
    "blender": (5, 0, 1),
    "location": "3Dviewport, Text edit mode",
    "description": "افزونه ای برای نوشتن متن فارسی و عربی در بلندر",
    "warning": "",
    "wiki_url": "",
    "category": "Text",
    "email": "farsayyad@gmail.com"
}

import bpy
import os
import re
import sys
from . import Persiantype as Ar
from .panel import __classes__
from . import sequencer
from bpy.types import PropertyGroup, AddonPreferences
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty

# Shared normalization for pasted Persian/Arabic text
def normalize_persian_text(s: str) -> str:
    if not s:
        return s
    trans_map = {
        '\u064a': '\u06cc',  # Yeh (Arabic) -> Yeh (Persian)
        '\u0643': '\u06a9',  # Kaf (Arabic) -> Kaf (Persian)
        '\u0640': '',         # Tatweel
        '\u200d': '',         # ZWJ remove
    }
    out = []
    for ch in s:
        out.append(trans_map.get(ch, ch))
    return ''.join(out)

# Keyboard Handler
class VIEW3D_OT_PersianTextMode(bpy.types.Operator):
    bl_idname = "view3d.persian_text_mode"
    bl_label = "Persian Text Mode"
    _is_running = False
    
    def modal(self, context, event):
        if bpy.context.object is None or bpy.context.object.type != 'FONT' or bpy.context.object.mode != 'EDIT':
            return {'PASS_THROUGH'}
        
        if event.type == 'BACK_SPACE':
            if event.value == 'PRESS':
                Ar.delete_previous()
            return {'RUNNING_MODAL'}
        
        elif event.type == 'DEL':
            if event.value == 'PRESS':
                Ar.delete_next()
            return {'RUNNING_MODAL'}
        
        elif event.type == 'HOME':
            if event.value == 'PRESS':
                Ar.move_line_start()
            return {'RUNNING_MODAL'}
        
        elif event.type == 'END':
            if event.value == 'PRESS':
                Ar.move_line_end()
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHT_ARROW':
            if event.value == 'PRESS':
                Ar.move_previous()
            return {'RUNNING_MODAL'}
            
        elif event.type == 'LEFT_ARROW':
            if event.value == 'PRESS':
                Ar.move_next()
            return {'RUNNING_MODAL'}
        
        elif event.type == 'UP_ARROW':
            if event.value == 'PRESS':
                Ar.move_up()
            return {'RUNNING_MODAL'}

        elif event.type == 'DOWN_ARROW':
            if event.value == 'PRESS':
                Ar.move_down()
            return {'RUNNING_MODAL'}

        elif event.type == 'RET':
            if event.value == 'PRESS':
                Ar.insert_text('\n')
            return {'RUNNING_MODAL'}
                   
        elif event.type == 'TAB':
            if event.value == 'RELEASE':
                if bpy.context.object.mode == 'EDIT':
                    Ar.init()
            return {'PASS_THROUGH'}
            
        elif (event.type == 'V' and event.value == 'PRESS' and event.ctrl) or (
            event.type == 'INSERT' and event.value == 'PRESS' and event.shift
        ):
            clip = context.window_manager.clipboard
            if clip:
                norm = normalize_persian_text(clip)
                for ch in norm:
                    Ar.insert_text(ch)
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        elif event.unicode:
            if event.value == 'PRESS':
                Ar.insert_text(event.unicode)
            return {'RUNNING_MODAL'}
        
        return {'PASS_THROUGH'}
     
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            if self.__class__._is_running:
                if (bpy.context.object is not None and
                        bpy.context.object.type == 'FONT' and
                        bpy.context.object.mode == 'EDIT'):
                    Ar.init()
                return {'CANCELLED'}

            self.key = ""
            context.window_manager.modal_handler_add(self)
            self.__class__._is_running = True
            
            if bpy.context.object is not None and bpy.context.object.type == 'FONT' and bpy.context.object.mode == 'EDIT':
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()
                Ar.init()
            
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}

# Store keymaps
keymaps = []


# ---------------------------------------------------------------------------
# Font discovery
#
# Three separate groups, three separate enums:
#   bundled -> the add-on's own fonts/ folder            (Scene.persian_font)
#   system  -> the operating system's font folders       (Scene.system_font)
#   custom  -> the user's folder plus saved favourites   (Scene.custom_font)
#
# EnumProperty item callbacks run on every UI redraw. Nothing in them may load
# a font datablock -- doing so bloats the blend file with fonts that are never
# freed (CLAUDE.md section 4, defect 6) -- and nothing in them may walk the
# filesystem unguarded. Each group is therefore built once into a module-level
# list and reused until something it is derived from changes. Holding the list
# at module level is also what keeps Blender from collecting item strings it
# does not own, which is the classic cause of garbled enum labels.
# ---------------------------------------------------------------------------

# Blender loads all three through FreeType. .ttc is a TrueType Collection;
# Blender takes the first face in it.
FONT_EXTENSIONS = ('.ttf', '.otf', '.ttc')

_BUNDLED_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")

# Trailing axis list on a variable font filename, e.g. "Vazirmatn[wght]".
_AXIS_TAIL_RE = re.compile(r'\[[^]]*\]$')

# An EnumProperty with no items reads back as an empty string and gives the
# user nothing to look at, so every group falls back to one inert entry.
_EMPTY_ITEMS = [('NONE', "No fonts found", "", 'ERROR', 0)]

FONT_GROUPS = ('BUNDLED', 'SYSTEM', 'CUSTOM')

_GROUP_PROPERTY = {
    'BUNDLED': 'persian_font',
    'SYSTEM': 'system_font',
    'CUSTOM': 'custom_font',
}

_GROUP_LABEL = {
    'BUNDLED': "bundled",
    'SYSTEM': "system",
    'CUSTOM': "custom",
}

_bundled_items = []
_bundled_key = None
_system_items = []
_system_key = None
_custom_items = []
_custom_key = None


def _preferences():
    """The add-on's preferences, or None when they are not available.

    ``__package__ or __name__`` rather than a bare ``__name__``: they are the
    same string in this module, but the fallback is what keeps the lookup
    correct if any of this ever moves into a submodule. Never index
    ``addons[key]`` -- the extension system installs under
    ``bl_ext.<repo>.persiantype`` and a missing key must not raise.
    """
    container = bpy.context.preferences.addons.get(__package__ or __name__)
    return container.preferences if container is not None else None


def _tag_redraw(context):
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def invalidate_font_caches(group=None):
    """Drop cached enum items so the next redraw rebuilds them.

    Called from the operators that change what a group contains. Passing None
    invalidates all three.
    """
    global _bundled_key, _system_key, _custom_key
    if group in (None, 'BUNDLED'):
        _bundled_key = None
    if group in (None, 'SYSTEM'):
        _system_key = None
    if group in (None, 'CUSTOM'):
        _custom_key = None


def _font_display_name(path):
    """Display label for a font file, derived from its filename.

    Deliberately filename-derived. Reading the real family name means loading
    the file as a font datablock, and these labels are produced on every
    redraw. Unlike panel._font_family_stem this keeps the weight suffix: a
    picker has to be able to tell Regular from Bold.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = _AXIS_TAIL_RE.sub('', stem)
    stem = ' '.join(stem.replace('_', ' ').replace('-', ' ').split())
    return stem or os.path.basename(path)


def _scan_fonts(folder, recursive=True):
    """Sorted font files under *folder*; empty when it is not a directory.

    os.walk reports nothing for a directory it cannot open, which is exactly
    the wanted behaviour: a font root that does not exist on this platform is
    not an error.
    """
    if not folder or not os.path.isdir(folder):
        return []
    found = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.lower().endswith(FONT_EXTENSIONS):
                found.append(os.path.join(dirpath, filename))
        if not recursive:
            break
    return found


def system_font_roots():
    """The current platform's font directories, existing ones only.

    Windows keeps per-user installs ("Install for me only") outside %WINDIR%,
    and Linux distributions nest fonts several levels deep, which is why the
    scan below is recursive.
    """
    roots = []
    if sys.platform.startswith('win'):
        windir = os.environ.get('WINDIR')
        if windir:
            roots.append(os.path.join(windir, 'Fonts'))
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            roots.append(os.path.join(local_appdata, 'Microsoft', 'Windows', 'Fonts'))
    elif sys.platform == 'darwin':
        roots.append('/System/Library/Fonts')
        roots.append('/Library/Fonts')
        roots.append(os.path.expanduser('~/Library/Fonts'))
    else:
        roots.append('/usr/share/fonts')
        roots.append('/usr/local/share/fonts')
        roots.append(os.path.expanduser('~/.fonts'))
        roots.append(os.path.expanduser('~/.local/share/fonts'))
    return [root for root in roots if os.path.isdir(root)]


def scan_system_fonts():
    """(display name, absolute path) for every system font, deduplicated."""
    seen = set()
    found = []
    for root in system_font_roots():
        for path in _scan_fonts(root):
            marker = os.path.normcase(os.path.abspath(path))
            if marker in seen:
                continue
            seen.add(marker)
            found.append((_font_display_name(path), path))
    found.sort(key=lambda entry: entry[0].casefold())
    return found


def resolve_font_path(scene, group):
    """(path, error) for the font currently selected in *group*.

    Exactly one of the two is None. Bundled values are bare filenames resolved
    against the add-on's fonts folder; system and custom values are absolute
    paths. Its callers are operators, so this runs on a user action -- the
    enum callbacks stay free of path checks and font loading.
    """
    property_name = _GROUP_PROPERTY.get(group)
    if property_name is None:
        return None, f"Unknown font group: {group}"

    value = getattr(scene, property_name, '') or ''
    if not value or value == 'NONE':
        return None, f"No {_GROUP_LABEL[group]} font selected"

    path = value if os.path.isabs(value) else os.path.join(_BUNDLED_FOLDER, value)
    if not os.path.isfile(path):
        return None, f"Font file not found: {path}"
    return path, None


def get_bundled_font_items(self, context):
    """Items for Scene.persian_font: the add-on's own fonts/ folder only."""
    global _bundled_items, _bundled_key
    if _bundled_key != _BUNDLED_FOLDER:
        items = []
        # Stored as a bare filename; resolve_font_path joins it onto the
        # bundled folder, which keeps the value stable across installs.
        for path in _scan_fonts(_BUNDLED_FOLDER, recursive=False):
            filename = os.path.basename(path)
            items.append((filename, _font_display_name(filename), filename))
        items.sort(key=lambda entry: entry[1].casefold())
        _bundled_items = items or list(_EMPTY_ITEMS)
        _bundled_key = _BUNDLED_FOLDER
    return _bundled_items


def get_system_font_items(self, context):
    """Items for Scene.system_font: the operating system's font folders.

    Served from the preferences cache when it is populated. When it is not --
    a fresh install, or the cache was cleared -- the scan runs once and is
    kept in the module-level list for the rest of the session. Writing the
    result back into preferences is pt.scan_system_fonts's job; a redraw does
    not write to preferences.
    """
    global _system_items, _system_key
    prefs = _preferences()
    cached = prefs.system_fonts_cache if prefs is not None else ()
    from_cache = bool(prefs is not None and prefs.system_fonts_cache_valid and len(cached))
    key = ('cache', len(cached)) if from_cache else ('scan',)

    if _system_key != key:
        if from_cache:
            entries = [
                (item.name or _font_display_name(item.path), item.path)
                for item in cached
                if item.path
            ]
        else:
            entries = scan_system_fonts()
        items = [(path, name, path) for name, path in entries]
        _system_items = items or list(_EMPTY_ITEMS)
        _system_key = key
    return _system_items


def _custom_signature(prefs):
    """Everything the custom group is derived from, cheap enough per redraw.

    The folder's modification time is included so a font dropped into it
    appears without pressing Refresh; that is one stat call, not a walk.
    """
    if prefs is None:
        return ('', 0, ())
    folder = bpy.path.abspath(prefs.custom_fonts_dir) if prefs.custom_fonts_dir else ''
    stamp = 0
    if folder:
        try:
            stamp = os.stat(folder).st_mtime_ns
        except OSError:
            # Unset, removed or unreadable: an empty group, not an error.
            stamp = 0
    return (folder, stamp, tuple(item.path for item in prefs.saved_fonts))


def get_custom_font_items(self, context):
    """Items for Scene.custom_font: the user's folder plus saved favourites."""
    global _custom_items, _custom_key
    prefs = _preferences()
    key = _custom_signature(prefs)

    if _custom_key != key:
        items = []
        seen = set()
        for path in _scan_fonts(key[0]):
            marker = os.path.normcase(os.path.abspath(path))
            if marker in seen:
                continue
            seen.add(marker)
            items.append((path, _font_display_name(path), path))

        for saved in (prefs.saved_fonts if prefs is not None else ()):
            path = saved.path
            if not path or not os.path.isfile(path):
                continue
            marker = os.path.normcase(os.path.abspath(path))
            if marker in seen:
                continue
            seen.add(marker)
            items.append((path, saved.name or _font_display_name(path), path))

        items.sort(key=lambda entry: entry[1].casefold())
        _custom_items = items or list(_EMPTY_ITEMS)
        _custom_key = key
    return _custom_items


def _custom_fonts_dir_changed(self, context):
    invalidate_font_caches('CUSTOM')


class PT_FontItem(PropertyGroup):
    name: StringProperty(name="Name", default="")
    path: StringProperty(name="Path", default="")


class PersiantypePreferences(AddonPreferences):
    bl_idname = __name__

    saved_fonts: CollectionProperty(type=PT_FontItem)
    saved_fonts_index: IntProperty(name="Index", default=0)
    # Cached system font scan, persisted so it does not have to run again next
    # session. Filled only by pt.scan_system_fonts, never from a redraw.
    system_fonts_cache: CollectionProperty(type=PT_FontItem)
    system_fonts_cache_valid: BoolProperty(name="System Fonts Cache Valid", default=False)
    # User custom fonts directory
    custom_fonts_dir: StringProperty(
        name="Custom Fonts Folder",
        subtype='DIR_PATH',
        default="",
        update=_custom_fonts_dir_changed,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="System Fonts Cache", icon='FILEBROWSER')
        row = box.row()
        row.operator("pt.scan_system_fonts", text="Rescan System Fonts", icon='FILE_REFRESH')
        row.label(text=f"Cached: {len(self.system_fonts_cache)}")
        box.label(text=", ".join(system_font_roots()) or "No system font folder on this platform")

        box = layout.box()
        box.label(text="Custom Fonts Folder", icon='FILE_FOLDER')
        col = box.column(align=True)
        col.prop(self, "custom_fonts_dir", text="Folder")
        col.operator("pt.choose_custom_fonts_dir", text="Choose Folder", icon='FILE_FOLDER')

        box = layout.box()
        box.label(text="Saved Custom Fonts", icon='FILE_FONT')
        row = box.row()
        row.template_list(
            "UI_UL_list", "PT_saved_fonts",
            self, "saved_fonts",
            self, "saved_fonts_index",
            rows=3,
        )
        col = row.column(align=True)
        col.operator("pt.remove_saved_font", text="", icon='TRASH').index = self.saved_fonts_index


class PT_OT_RemoveSavedFont(bpy.types.Operator):
    bl_idname = "pt.remove_saved_font"
    bl_label = "Remove Saved Font"
    bl_description = "Remove the selected font from the saved custom font list"
    bl_options = {'REGISTER'}

    index: IntProperty(default=0)

    @classmethod
    def poll(cls, context):
        prefs = _preferences()
        return prefs is not None and len(prefs.saved_fonts) > 0

    def execute(self, context):
        prefs = _preferences()
        if prefs is None:
            self.report({'ERROR'}, "Could not access the add-on preferences")
            return {'CANCELLED'}
        if not 0 <= self.index < len(prefs.saved_fonts):
            self.report({'ERROR'}, f"No saved font at index {self.index}")
            return {'CANCELLED'}

        removed = prefs.saved_fonts[self.index].name
        prefs.saved_fonts.remove(self.index)
        prefs.saved_fonts_index = max(
            0, min(prefs.saved_fonts_index, len(prefs.saved_fonts) - 1)
        )
        invalidate_font_caches('CUSTOM')
        _tag_redraw(context)
        self.report({'INFO'}, f"Removed saved font: {removed}")
        return {'FINISHED'}


class PT_OT_ScanSystemFonts(bpy.types.Operator):
    bl_idname = "pt.scan_system_fonts"
    bl_label = "Rescan System Fonts"
    bl_description = (
        "Rescan the operating system's font folders and cache the result, so "
        "the System Fonts dropdown stays cheap to redraw"
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _preferences() is not None

    def execute(self, context):
        prefs = _preferences()
        if prefs is None:
            self.report({'ERROR'}, "Could not access the add-on preferences")
            return {'CANCELLED'}

        prefs.system_fonts_cache.clear()
        prefs.system_fonts_cache_valid = False
        invalidate_font_caches('SYSTEM')

        roots = system_font_roots()
        if not roots:
            self.report(
                {'ERROR'},
                f"No system font folder exists on this platform ({sys.platform})",
            )
            return {'CANCELLED'}

        found = scan_system_fonts()
        for name, path in found:
            slot = prefs.system_fonts_cache.add()
            slot.name = name
            slot.path = path
        prefs.system_fonts_cache_valid = bool(found)
        invalidate_font_caches('SYSTEM')
        _tag_redraw(context)

        if not found:
            self.report({'WARNING'}, "No font files found in: " + ", ".join(roots))
            return {'FINISHED'}

        self.report(
            {'INFO'},
            f"Cached {len(found)} system font(s) from {len(roots)} folder(s)",
        )
        return {'FINISHED'}


class PT_OT_ChooseCustomFontsDir(bpy.types.Operator):
    bl_idname = "pt.choose_custom_fonts_dir"
    bl_label = "Choose Custom Fonts Folder"
    bl_description = "Select the folder whose fonts appear in the Custom Fonts dropdown"
    bl_options = {'REGISTER'}

    directory: StringProperty(subtype='DIR_PATH')

    @classmethod
    def poll(cls, context):
        return _preferences() is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = _preferences()
        if prefs is None:
            self.report({'ERROR'}, "Could not access the add-on preferences")
            return {'CANCELLED'}
        if not self.directory or not os.path.isdir(self.directory):
            self.report({'ERROR'}, f"Not a folder: {self.directory}")
            return {'CANCELLED'}

        # Assignment fires _custom_fonts_dir_changed, which drops the cache.
        prefs.custom_fonts_dir = self.directory
        _tag_redraw(context)
        self.report({'INFO'}, f"Custom fonts folder set to {self.directory}")
        return {'FINISHED'}


def register():
    # Property group and preferences first: the collections below are typed on
    # PT_FontItem, and the Scene enums read the preferences.
    bpy.utils.register_class(PT_FontItem)
    bpy.utils.register_class(PersiantypePreferences)

    # Add-on utility operators
    bpy.utils.register_class(PT_OT_RemoveSavedFont)
    bpy.utils.register_class(PT_OT_ScanSystemFonts)
    bpy.utils.register_class(PT_OT_ChooseCustomFontsDir)

    # A reload must not serve items built against the previous registration.
    invalidate_font_caches()

    # The three font groups, one enum each.
    bpy.types.Scene.persian_font = bpy.props.EnumProperty(
        name="Bundled Font",
        description="Fonts shipped with the add-on",
        items=get_bundled_font_items,
    )
    bpy.types.Scene.system_font = bpy.props.EnumProperty(
        name="System Font",
        description="Fonts installed in the operating system's font folders",
        items=get_system_font_items,
    )
    bpy.types.Scene.custom_font = bpy.props.EnumProperty(
        name="Custom Font",
        description="Fonts from your custom fonts folder and your saved list",
        items=get_custom_font_items,
    )

    # Register keyboard handler
    bpy.utils.register_class(VIEW3D_OT_PersianTextMode)

    # Register all panel classes
    for cls in __classes__:
        bpy.utils.register_class(cls)

    # Setup keyboard shortcut
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Window")
        kmi = km.keymap_items.new(VIEW3D_OT_PersianTextMode.bl_idname, 'F1', 'PRESS', ctrl=True)
        keymaps.append((km, kmi))

    # Register paste normalize operator
    bpy.utils.register_class(PT_OT_PastePersianNormalize)

    # Video Sequencer text strip support (owns its own classes)
    sequencer.register()


def unregister():
    # Exact mirror of register(), in reverse.
    sequencer.unregister()

    bpy.utils.unregister_class(PT_OT_PastePersianNormalize)

    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)
    keymaps.clear()

    for cls in reversed(__classes__):
        bpy.utils.unregister_class(cls)

    bpy.utils.unregister_class(VIEW3D_OT_PersianTextMode)

    del bpy.types.Scene.custom_font
    del bpy.types.Scene.system_font
    del bpy.types.Scene.persian_font

    invalidate_font_caches()

    bpy.utils.unregister_class(PT_OT_ChooseCustomFontsDir)
    bpy.utils.unregister_class(PT_OT_ScanSystemFonts)
    bpy.utils.unregister_class(PT_OT_RemoveSavedFont)
    bpy.utils.unregister_class(PersiantypePreferences)
    bpy.utils.unregister_class(PT_FontItem)

if __name__ == "__main__":
    register()


class PT_OT_PastePersianNormalize(bpy.types.Operator):
    bl_idname = "pt.paste_persian_normalize"
    bl_label = "Paste Persian (Normalize)"
    bl_description = "Paste clipboard text with Persian normalization (Yeh/Kaf, remove Kashida, clean ZWJ)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'FONT' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "لطفاً یک آبجکت متن را در حالت ویرایش انتخاب کنید")
            return {'CANCELLED'}
        clip = context.window_manager.clipboard
        if not clip:
            self.report({'WARNING'}, "کلیپ‌بورد خالی است")
            return {'CANCELLED'}
        norm = normalize_persian_text(clip)
        try:
            for ch in norm:
                Ar.insert_text(ch)
            self.report({'INFO'}, "متن نرمال‌شده چسبانده شد")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Paste failed: {e}")
            return {'CANCELLED'}
