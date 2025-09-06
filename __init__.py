bl_info = {
    "name": "Persiantype",
    "author": "DAMYAR",
    "version": (2, 0, 0),
    "blender": (4, 3, 0),
    "location": "3Dviewport, Text edit mode",
    "description": "افزونه ای برای نوشتن متن فارسی در بلندر",
    "warning": "",
    "wiki_url": "",
    "category": "Text",
    "email": "farsayyad@gmail.com"
}

import bpy
import os
from . import Persiantype as Ar
from .panel import __classes__
from bpy.types import PropertyGroup, AddonPreferences
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty

# Keyboard Handler
class VIEW3D_OT_PersianTextMode(bpy.types.Operator):
    bl_idname = "view3d.persian_text_mode"
    bl_label = "Persian Text Mode"
    
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
            
        elif event.unicode:
            if event.value == 'PRESS':
                Ar.insert_text(event.unicode)
            return {'RUNNING_MODAL'}
        
        return {'PASS_THROUGH'}
     
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            self.key = ""
            context.window_manager.modal_handler_add(self)
            
            if bpy.context.object is not None and bpy.context.object.type == 'FONT' and bpy.context.object.mode == 'EDIT':
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()
                Ar.init()
            
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}

# Store keymaps
keymaps = []


class PT_FontItem(PropertyGroup):
    name: StringProperty(name="Name", default="")
    path: StringProperty(name="Path", default="")


class PersiantypePreferences(AddonPreferences):
    bl_idname = __name__

    saved_fonts: CollectionProperty(type=PT_FontItem)
    saved_fonts_index: IntProperty(name="Index", default=0)
    # Cache of Windows fonts to speed up dropdown population
    windows_fonts_cache: CollectionProperty(type=PT_FontItem)
    windows_fonts_cache_valid: BoolProperty(name="Windows Fonts Cache Valid", default=False)
    # User custom fonts directory
    custom_fonts_dir: StringProperty(name="Custom Fonts Folder", subtype='DIR_PATH', default="")

    def draw(self, context):
        layout = self.layout
        # Saved Windows fonts list (manually added by user from panel actions)
        box = layout.box()
        box.label(text="Saved Windows Fonts", icon='FILE_FONT')
        row = box.row()
        row.template_list("UI_UL_list", "PT_saved_fonts", self, "saved_fonts", self, "saved_fonts_index", rows=3)
        col = row.column(align=True)
        op = col.operator("pt.remove_saved_font", text="", icon='TRASH')
        op.index = self.saved_fonts_index

        # Windows fonts cache controls
        box = layout.box()
        box.label(text="Windows Fonts Cache", icon='FILEBROWSER')
        row = box.row()
        row.operator("pt.scan_windows_fonts", text="Scan/Refresh Windows Fonts", icon='FILE_REFRESH')
        cache_count = len(self.windows_fonts_cache)
        row.label(text=f"Cached: {cache_count}")

        # Custom fonts folder selection
        box = layout.box()
        box.label(text="Custom Fonts Folder", icon='FILE_FOLDER')
        col = box.column(align=True)
        col.prop(self, "custom_fonts_dir", text="Folder")
        col.operator("pt.choose_custom_fonts_dir", text="Choose Folder", icon='FILE_FOLDER')


class PT_OT_RemoveSavedFont(bpy.types.Operator):
    bl_idname = "pt.remove_saved_font"
    bl_label = "Remove Saved Font"
    bl_description = "Remove the selected Windows font from the saved list"

    index: IntProperty(default=0)

    def execute(self, context):
        addon_key = __name__
        pref_container = bpy.context.preferences.addons.get(addon_key)
        if not pref_container:
            return {'CANCELLED'}
        prefs = pref_container.preferences
        if 0 <= self.index < len(prefs.saved_fonts):
            prefs.saved_fonts.remove(self.index)
            # Adjust index
            prefs.saved_fonts_index = max(0, min(prefs.saved_fonts_index, len(prefs.saved_fonts) - 1))
            self.report({'INFO'}, "Removed saved font")
            return {'FINISHED'}
        return {'CANCELLED'}

def get_font_items(self, context):
    items = []
    seen = set()
    font_folder = os.path.join(os.path.dirname(__file__), "fonts")
    if os.path.exists(font_folder):
        for font_file in os.listdir(font_folder):
            if font_file.endswith((".ttf", ".otf")):
                # Try to read family name via bpy font datablock
                display = os.path.splitext(font_file)[0]
                full_path = os.path.join(font_folder, font_file)
                try:
                    fdat = bpy.data.fonts.load(full_path, check_existing=True)
                    if getattr(fdat, 'name', ''):
                        display = fdat.name
                except Exception:
                    pass
                key = (font_file, display)
                if key not in seen:
                    items.append((font_file, display, ""))
                    seen.add(key)
    # Include custom fonts folder from preferences (absolute paths)
    addon_key = __name__
    prefs_container = bpy.context.preferences.addons.get(addon_key)
    prefs = prefs_container.preferences if prefs_container else None
    if prefs and prefs.custom_fonts_dir and os.path.isdir(prefs.custom_fonts_dir):
        try:
            for fname in os.listdir(prefs.custom_fonts_dir):
                if fname.lower().endswith((".ttf", ".otf")):
                    fpath = os.path.join(prefs.custom_fonts_dir, fname)
                    display = os.path.splitext(fname)[0]
                    try:
                        fdat = bpy.data.fonts.load(fpath, check_existing=True)
                        if getattr(fdat, 'name', ''):
                            display = fdat.name
                    except Exception:
                        pass
                    label = f"{display} (Custom)"
                    key = (fpath, label)
                    if key not in seen:
                        items.append((fpath, label, ""))
                        seen.add(key)
        except Exception:
            pass
    # Include saved Windows fonts from preferences (store value as absolute path)
    prefs_container = bpy.context.preferences.addons.get(addon_key)
    if prefs_container:
        prefs = prefs_container.preferences
        for f in prefs.saved_fonts:
            if os.path.exists(f.path):
                display = os.path.splitext(os.path.basename(f.path))[0]
                # Try to read family name via bpy font datablock
                try:
                    fdat = bpy.data.fonts.load(f.path, check_existing=True)
                    if getattr(fdat, 'name', ''):
                        display = fdat.name
                except Exception:
                    pass
                label = display + " (Windows)"
                key = (f.path, label)
                if key not in seen:
                    items.append((f.path, label, ""))
                    seen.add(key)
    return items

class PT_OT_ScanWindowsFonts(bpy.types.Operator):
    bl_idname = "pt.scan_windows_fonts"
    bl_label = "Scan Windows Fonts"
    bl_description = "Scan C\\Windows\\Fonts and cache results for fast dropdown"
    bl_options = {'REGISTER'}

    def execute(self, context):
        addon_key = __name__
        pref_container = bpy.context.preferences.addons.get(addon_key)
        if not pref_container:
            return {'CANCELLED'}
        prefs = pref_container.preferences
        # Invalidate first
        prefs.windows_fonts_cache_valid = False
        prefs.windows_fonts_cache.clear()

        win_dir = os.environ.get('WINDIR')
        if not win_dir:
            self.report({'ERROR'}, "Windows directory not found")
            return {'CANCELLED'}
        fonts_dir = os.path.join(win_dir, 'Fonts')
        if not os.path.exists(fonts_dir):
            self.report({'ERROR'}, "Windows Fonts folder not found")
            return {'CANCELLED'}

        scanned = []
        try:
            for fname in os.listdir(fonts_dir):
                if fname.lower().endswith((".ttf", ".otf")):
                    fpath = os.path.join(fonts_dir, fname)
                    display = os.path.splitext(fname)[0]
                    try:
                        fdat = bpy.data.fonts.load(fpath, check_existing=True)
                        if getattr(fdat, 'name', ''):
                            display = fdat.name
                    except Exception:
                        pass
                    scanned.append((display, fpath))
            scanned.sort(key=lambda x: x[0].lower())
            for disp, path in scanned:
                slot = prefs.windows_fonts_cache.add()
                slot.name = disp
                slot.path = path
            prefs.windows_fonts_cache_valid = True
            # Trigger redraw
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({'INFO'}, f"Cached {len(scanned)} Windows fonts")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Scan failed: {e}")
            return {'CANCELLED'}


class PT_OT_ChooseCustomFontsDir(bpy.types.Operator):
    bl_idname = "pt.choose_custom_fonts_dir"
    bl_label = "Choose Custom Fonts Folder"
    bl_description = "Select a folder to include your personal fonts in the dropdown"
    bl_options = {'REGISTER'}

    directory: StringProperty(subtype='DIR_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        addon_key = __name__
        pref_container = bpy.context.preferences.addons.get(addon_key)
        if not pref_container:
            return {'CANCELLED'}
        prefs = pref_container.preferences
        if not self.directory or not os.path.isdir(self.directory):
            self.report({'ERROR'}, "Invalid folder")
            return {'CANCELLED'}
        prefs.custom_fonts_dir = self.directory
        # Redraw UI so dropdown updates
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        self.report({'INFO'}, "Custom fonts folder set")
        return {'FINISHED'}


def get_windows_font_items(self, context):
    items = []
    seen = set()
    # Serve from cache if valid
    addon_key = __name__
    pref_container = bpy.context.preferences.addons.get(addon_key)
    prefs = pref_container.preferences if pref_container else None
    if prefs and prefs.windows_fonts_cache_valid and len(prefs.windows_fonts_cache) > 0:
        for it in prefs.windows_fonts_cache:
            if os.path.exists(it.path):
                label = it.name if it.name else os.path.splitext(os.path.basename(it.path))[0]
                key = (it.path, label)
                if key not in seen:
                    items.append((it.path, label, ""))
                    seen.add(key)
        return items

    # Else scan Windows Fonts and fill cache
    win_dir = os.environ.get('WINDIR')
    if not win_dir:
        return items
    fonts_dir = os.path.join(win_dir, 'Fonts')
    if not os.path.exists(fonts_dir):
        return items
    scanned = []
    try:
        for fname in os.listdir(fonts_dir):
            if fname.lower().endswith(('.ttf', '.otf')):
                fpath = os.path.join(fonts_dir, fname)
                display = os.path.splitext(fname)[0]
                # Try to get family name
                try:
                    fdat = bpy.data.fonts.load(fpath, check_existing=True)
                    if getattr(fdat, 'name', ''):
                        display = fdat.name
                except Exception:
                    pass
                key = (fpath, display)
                if key not in seen:
                    items.append((fpath, display, ""))
                    seen.add(key)
                    scanned.append((display, fpath))
        # Sort and cache
        items.sort(key=lambda x: x[1].lower())
        if prefs is not None:
            prefs.windows_fonts_cache.clear()
            for disp, path in sorted(scanned, key=lambda x: x[0].lower()):
                slot = prefs.windows_fonts_cache.add()
                slot.name = disp
                slot.path = path
            prefs.windows_fonts_cache_valid = True
    except Exception:
        pass
    return items

def register():
    # Register preferences and property group
    bpy.utils.register_class(PT_FontItem)
    bpy.utils.register_class(PersiantypePreferences)
    bpy.utils.register_class(PT_OT_RemoveSavedFont)
    bpy.utils.register_class(PT_OT_ScanWindowsFonts)
    bpy.utils.register_class(PT_OT_ChooseCustomFontsDir)

    # Register font property
    bpy.types.Scene.persian_font = bpy.props.EnumProperty(
        name="Persian Font",
        items=get_font_items
    )
    # Register Windows font property
    bpy.types.Scene.windows_font = bpy.props.EnumProperty(
        name="Windows Font",
        description="Fonts from Windows\\Fonts",
        items=get_windows_font_items
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
        km = wm.keyconfigs.addon.keymaps.new(name="Window")
        kmi = km.keymap_items.new(VIEW3D_OT_PersianTextMode.bl_idname, 'F1', 'PRESS', ctrl=True)
        keymaps.append((km, kmi))

    # Register paste normalize operator
    bpy.utils.register_class(PT_OT_PastePersianNormalize)

def unregister():
    # Remove keyboard shortcut
    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)
    keymaps.clear()
    
    # Unregister keyboard handler
    bpy.utils.unregister_class(VIEW3D_OT_PersianTextMode)
    
    # Unregister all panel classes
    for cls in reversed(__classes__):
        bpy.utils.unregister_class(cls)
    
    # Remove font property
    del bpy.types.Scene.persian_font
    del bpy.types.Scene.windows_font

    # Unregister preferences and property group
    bpy.utils.unregister_class(PT_OT_RemoveSavedFont)
    bpy.utils.unregister_class(PT_OT_ChooseCustomFontsDir)
    bpy.utils.unregister_class(PT_OT_ScanWindowsFonts)
    bpy.utils.unregister_class(PersiantypePreferences)
    bpy.utils.unregister_class(PT_FontItem)
    # Unregister paste normalize operator
    bpy.utils.unregister_class(PT_OT_PastePersianNormalize)

if __name__ == "__main__":
    register()


class PT_OT_PastePersianNormalize(bpy.types.Operator):
    bl_idname = "pt.paste_persian_normalize"
    bl_label = "Paste Persian (Normalize)"
    bl_description = "Paste clipboard text with Persian normalization (Yeh/Kaf, remove Kashida, clean ZWJ)"
    bl_options = {'REGISTER', 'UNDO'}

    def normalize_text(self, s: str) -> str:
        if not s:
            return s
        trans_map = {
            '\u064a': '\u06cc',  # ي -> ی
            '\u0643': '\u06a9',  # ك -> ک
            '\u0640': '',         # Tatweel (ـ)
            '\u200d': '',         # ZWJ remove
        }
        out = []
        for ch in s:
            out.append(trans_map.get(ch, ch))
        return ''.join(out)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'FONT' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "لطفاً یک آبجکت متن را در حالت ویرایش انتخاب کنید")
            return {'CANCELLED'}
        clip = context.window_manager.clipboard
        if not clip:
            self.report({'WARNING'}, "کلیپ‌بورد خالی است")
            return {'CANCELLED'}
        norm = self.normalize_text(clip)
        try:
            for ch in norm:
                Ar.insert_text(ch)
            self.report({'INFO'}, "متن نرمال‌شده چسبانده شد")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Paste failed: {e}")
            return {'CANCELLED'}

