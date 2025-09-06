import bpy
import os

FONT_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")

class VIEW3D_OT_ToggleTextDirection(bpy.types.Operator):
    bl_idname = "view3d.toggle_text_direction"
    bl_label = "Toggle Text Direction"
    bl_description = "Toggle text direction between English and Persian and Arabic"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object and context.active_object.type == 'FONT':
            text_obj = context.active_object
            
            if text_obj.data.align_x == 'LEFT':
                text_obj.data.align_x = 'RIGHT'
                self.report({'INFO'}, "Text direction: Right to Left (Persian / Arabic)")
            else:
                text_obj.data.align_x = 'LEFT'
                self.report({'INFO'}, "Text direction: Left to Right (English)")
                
            text_obj.data.update_tag()
            context.view_layer.update()
            
            return {'FINISHED'}


class VIEW3D_OT_ChangeWindowsFont(bpy.types.Operator):
    bl_idname = "view3d.change_windows_font"
    bl_label = "Apply Windows Font"
    bl_description = "Apply the selected Windows font to the active text object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Ensure selection and active text object
        fpath = getattr(context.scene, 'windows_font', '')
        if not fpath:
            self.report({'WARNING'}, "Please select a Windows font from the dropdown")
            return {'CANCELLED'}
        if not (context.active_object and context.active_object.type == 'FONT'):
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}

        # Validate path
        if not os.path.exists(fpath):
            self.report({'ERROR'}, "Selected font file does not exist")
            return {'CANCELLED'}

        try:
            font = bpy.data.fonts.load(fpath, check_existing=True)
            context.active_object.data.font = font
            # Optional: also add to saved list in preferences
            addon_key = __package__
            pref_container = bpy.context.preferences.addons.get(addon_key)
            if pref_container:
                prefs = pref_container.preferences
                if not any(it.path == fpath for it in prefs.saved_fonts):
                    item = prefs.saved_fonts.add()
                    item.name = os.path.splitext(os.path.basename(fpath))[0]
                    item.path = fpath
            # Refresh UI
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({'INFO'}, "Windows font applied")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply font: {e}")
            return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'FONT'

class VIEW3D_OT_ChangePersianFont(bpy.types.Operator):
    bl_idname = "view3d.change_persian_font"
    bl_label = "Change Font"
    bl_description = "Apply selected font to the active text object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Check if there's an active text object
        if context.active_object and context.active_object.type == 'FONT':
            text_obj = context.active_object
            selected = context.scene.persian_font
            # Support both bundled fonts (relative filename) and saved absolute paths
            if os.path.isabs(selected):
                font_path = selected
            else:
                font_path = os.path.join(FONT_FOLDER, selected)
            
            # Check if font file exists
            if os.path.exists(font_path):
                # Load and apply the font
                font = bpy.data.fonts.load(font_path, check_existing=True)
                text_obj.data.font = font
                self.report({'INFO'}, f"Font changed to {context.scene.persian_font}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Font file not found")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'FONT'

class VIEW3D_OT_LoadWindowsFont(bpy.types.Operator):
    bl_idname = "view3d.load_windows_font"
    bl_label = "Load from Windows Fonts"
    bl_description = "Browse and apply a font from the Windows Fonts folder to the active text object"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.ttf;*.otf",
        options={'HIDDEN'}
    )

    filepath: bpy.props.StringProperty(
        name="File Path",
        subtype='FILE_PATH'
    )

    def invoke(self, context, event):
        # Default to Windows Fonts directory if available
        win_dir = os.environ.get('WINDIR')
        if win_dir:
            default_dir = os.path.join(win_dir, 'Fonts')
        else:
            default_dir = os.path.expanduser('~')

        # Pre-fill a path to guide the file selector
        if not self.filepath:
            self.filepath = os.path.join(default_dir, "")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        # Validate selection
        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, "Please choose a valid font file (.ttf or .otf)")
            return {'CANCELLED'}

        if not (self.filepath.lower().endswith('.ttf') or self.filepath.lower().endswith('.otf')):
            self.report({'ERROR'}, "Unsupported file type. Choose a .ttf or .otf font file")
            return {'CANCELLED'}

        # Check active object
        if not (context.active_object and context.active_object.type == 'FONT'):
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}

        # Load and apply
        try:
            font = bpy.data.fonts.load(self.filepath, check_existing=True)
            context.active_object.data.font = font
            # Save to addon preferences saved list (so it appears in the dropdown)
            addon_key = __package__
            pref_container = bpy.context.preferences.addons.get(addon_key)
            if pref_container:
                prefs = pref_container.preferences
                exists = any(f.path == self.filepath for f in prefs.saved_fonts)
                if not exists:
                    item = prefs.saved_fonts.add()
                    item.name = os.path.splitext(os.path.basename(self.filepath))[0]
                    item.path = self.filepath
            # Trigger UI refresh so the dropdown updates immediately
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({'INFO'}, f"Applied font: {os.path.basename(self.filepath)}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load font: {e}")
            return {'CANCELLED'}


class VIEW3D_OT_RefreshPersianFonts(bpy.types.Operator):
    bl_idname = "view3d.refresh_persian_fonts"
    bl_label = "Refresh Fonts"
    bl_description = "Rescan and refresh the font list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        # Tag redraw for all areas to ensure the Enum items callback is run again
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        self.report({'INFO'}, "Font list refreshed")
        return {'FINISHED'}


class VIEW3D_OT_SaveCurrentFont(bpy.types.Operator):
    bl_idname = "view3d.save_current_persian_font"
    bl_label = "Save Current Font"
    bl_description = "Save the active text object's font into the saved list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not (obj and obj.type == 'FONT'):
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}

        fnt = obj.data.font
        if not fnt:
            self.report({'ERROR'}, "No font assigned to the text object")
            return {'CANCELLED'}

        # Try to get a filepath. Some fonts may be internal; in that case attempt fallbacks.
        font_path = getattr(fnt, 'filepath', '') or ''
        # Fallback 1: use current selection from persian_font enum
        if not (font_path and os.path.isabs(font_path) and os.path.exists(font_path)):
            sel = getattr(context.scene, 'persian_font', '')
            if sel:
                font_path = sel if os.path.isabs(sel) else os.path.join(FONT_FOLDER, sel)
        # Fallback 2: use current selection from windows_font enum
        if not (font_path and os.path.isabs(font_path) and os.path.exists(font_path)):
            win_sel = getattr(context.scene, 'windows_font', '')
            if win_sel and os.path.isabs(win_sel):
                font_path = win_sel
        # Final validation
        if not (font_path and os.path.isabs(font_path) and os.path.exists(font_path)):
            self.report({'ERROR'}, "Current font has no valid file path to save")
            return {'CANCELLED'}

        addon_key = __package__
        pref_container = bpy.context.preferences.addons.get(addon_key)
        if not pref_container:
            self.report({'ERROR'}, "Could not access add-on preferences")
            return {'CANCELLED'}

        prefs = pref_container.preferences
        # Avoid duplicates
        if any(item.path == font_path for item in prefs.saved_fonts):
            self.report({'INFO'}, "Font already in saved list")
        else:
            item = prefs.saved_fonts.add()
            item.name = os.path.splitext(os.path.basename(font_path))[0]
            item.path = font_path
            self.report({'INFO'}, f"Saved font: {item.name}")

        # Trigger UI refresh so it appears in the dropdown
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {'FINISHED'}

class PersiantypePanel(bpy.types.Panel):
    bl_label = "Persian type Panel"
    bl_idname = "VIEW3D_PT_persiantype"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Persian type"

    def draw(self, context):
        layout = self.layout
        
        # Main Section
        box = layout.box()
        box.label(text="Persian / Arabic Text", icon='FONT_DATA')
        
        # Enable Button
        row = box.row()
        row.operator("view3d.persian_text_mode", text="Enable Persian/Arabic Text", icon='GREASEPENCIL')
        
        # Toggle Text Direction Button
        row = box.row()
        row.operator("view3d.toggle_text_direction", text="Toggle Text Direction", icon='ARROW_LEFTRIGHT')
        
        # Font Settings
        box = layout.box()
        box.label(text="Font Settings:", icon='PREFERENCES')
        
        # Font List
        row = box.row(align=True)
        row.prop(context.scene, "persian_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        
        # Change Font Button
        row = box.row(align=True)
        row.operator("view3d.change_persian_font", text="Change Font", icon='FILE_FONT')
        row.operator("view3d.save_current_persian_font", text="", icon='FOLDER_REDIRECT')

        # Windows Fonts Section
        box = layout.box()
        box.label(text="Windows Fonts:", icon='FILEBROWSER')
        # Dropdown of Windows fonts with Apply & Refresh
        row = box.row(align=True)
        row.prop(context.scene, "windows_font", text="Windows Font")
        row.operator("view3d.change_windows_font", text="", icon='CHECKMARK')
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')

        # Load from Windows Fonts with adjacent Refresh
        row = box.row(align=True)
        row.operator("view3d.load_windows_font", text="Load from Windows Fonts", icon='FILE_FOLDER')
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')

# Export all classes
__classes__ = [
    VIEW3D_OT_ToggleTextDirection,
    VIEW3D_OT_ChangePersianFont,
    VIEW3D_OT_LoadWindowsFont,
    VIEW3D_OT_RefreshPersianFonts,
    VIEW3D_OT_SaveCurrentFont,
    VIEW3D_OT_ChangeWindowsFont,
    PersiantypePanel
]
