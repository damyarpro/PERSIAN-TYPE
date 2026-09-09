import bpy
import os
import re

FONT_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")

# Must move together with `version` in blender_manifest.toml and the
# bl_info["version"] tuple in __init__.py. Defined once so a version bump
# touches a single line in this module.
ADDON_VERSION = "3.1"
DEFAULT_TEXT_OBJECT_NAME = f"Persian Type {ADDON_VERSION}"
DEFAULT_PERSIAN_TEXT = f"پرشین تایپ {ADDON_VERSION}"


def _font_family_stem(filepath):
    stem = os.path.splitext(os.path.basename(filepath))[0]
    stem = re.sub(r'\[[^]]+\]$', '', stem)
    return re.sub(
        r'[-_ ](?:Thin|ExtraLight|Light|Regular|Medium|SemiBold|Bold|ExtraBold|Black)(?:Italic)?$',
        '',
        stem,
        flags=re.IGNORECASE,
    )


def _find_font_weight_file(font, weight):
    filepath = bpy.path.abspath(getattr(font, "filepath", "") or "")
    family = _font_family_stem(filepath or font.name)
    wanted = ("Regular", "Book", "Roman") if weight == 'REGULAR' else ("Bold",)
    folders = []
    if filepath:
        folders.append(os.path.dirname(filepath))
    if FONT_FOLDER not in folders:
        folders.append(FONT_FOLDER)

    matches = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            if not filename.lower().endswith(('.ttf', '.otf')):
                continue
            if _font_family_stem(filename).casefold() != family.casefold():
                continue
            stem = os.path.splitext(filename)[0]
            if any(re.search(rf'(^|[-_ ]){name}($|[-_ ])', stem, re.IGNORECASE) for name in wanted):
                matches.append(os.path.join(folder, filename))
    return sorted(matches)[0] if matches else None


def create_persian_text(context, *, initial_text=DEFAULT_PERSIAN_TEXT, start_typing=True):
    """Create a ready-to-edit RTL text object at the 3D Cursor."""

    from . import Persiantype as Ar

    active = context.active_object
    if active is not None and active.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            return None

    for obj in context.selected_objects:
        obj.select_set(False)

    curve = bpy.data.curves.new(DEFAULT_TEXT_OBJECT_NAME, 'FONT')
    logical_text = list(initial_text)
    curve.body = Ar.swap_lines(Ar.link_text(logical_text))
    curve.align_x = 'RIGHT'

    obj = bpy.data.objects.new(DEFAULT_TEXT_OBJECT_NAME, curve)
    collection = context.collection or context.scene.collection
    collection.objects.link(obj)
    obj.location = context.scene.cursor.location
    obj.select_set(True)
    context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
    except RuntimeError:
        return obj

    # Read the shaped sample into the add-on's edit buffer and place the
    # logical caret at the end for immediate typing and Backspace support.
    Ar.init()
    # The legacy unshaper normalizes Persian Yeh to Arabic Yeh. Preserve the
    # exact Persian sample in the live logical buffer.
    Ar.text_buffer = list(logical_text)
    Ar.current_char_index = len(Ar.text_buffer)
    Ar.update_visual_cursor_position()
    curve.align_x = 'RIGHT'

    if start_typing:
        bpy.ops.view3d.persian_text_mode('INVOKE_DEFAULT')
        # PersianTextMode re-reads the shaped body. Put the logical caret at
        # the end so typing appends and Backspace immediately deletes text.
        Ar.text_buffer = list(logical_text)
        Ar.current_char_index = len(Ar.text_buffer)
        Ar.update_visual_cursor_position()

    return obj


class VIEW3D_OT_AddPersianText(bpy.types.Operator):
    bl_idname = "view3d.add_persian_text"
    bl_label = "Add Text"
    bl_description = "Create a Persian text object at the 3D Cursor and start typing in Persian"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        obj = create_persian_text(context, start_typing=True)
        if obj is None:
            self.report({'ERROR'}, "Could not create a Text object in the current mode")
            return {'CANCELLED'}
        self.report({'INFO'}, "Persian typing is ready")
        return {'FINISHED'}


class VIEW3D_OT_PastePersianText(bpy.types.Operator):
    bl_idname = "view3d.paste_persian_text"
    bl_label = "Paste"
    bl_description = "Create right-aligned Persian/Arabic text from the clipboard and continue typing"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        from . import normalize_persian_text

        clipboard = context.window_manager.clipboard
        if not clipboard or not clipboard.strip():
            self.report({'WARNING'}, "Clipboard is empty")
            return {'CANCELLED'}

        # Arabic, Arabic Supplement, Arabic Extended and presentation forms.
        if not any(
            '\u0600' <= char <= '\u06ff'
            or '\u0750' <= char <= '\u077f'
            or '\u08a0' <= char <= '\u08ff'
            or '\ufb50' <= char <= '\ufdff'
            or '\ufe70' <= char <= '\ufeff'
            for char in clipboard
        ):
            self.report({'WARNING'}, "Clipboard does not contain Persian or Arabic text")
            return {'CANCELLED'}

        logical_text = normalize_persian_text(clipboard)
        obj = create_persian_text(
            context,
            initial_text=logical_text,
            start_typing=True,
        )
        if obj is None:
            self.report({'ERROR'}, "Could not create a Text object in the current mode")
            return {'CANCELLED'}

        self.report({'INFO'}, "Clipboard text pasted; Persian typing is ready")
        return {'FINISHED'}


class VIEW3D_OT_MeshClean(bpy.types.Operator):
    bl_idname = "view3d.persian_mesh_clean"
    bl_label = "Mesh Clean"
    bl_description = (
        "Convert selected text to mesh, apply Planar Decimate, Delete Loose, "
        "and Merge by Distance (0.01401 m)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    merge_distance: bpy.props.FloatProperty(
        name="Merge Distance",
        default=0.01401,
        min=0.0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and active is not None
            and active.type == 'FONT'
        )

    def execute(self, context):
        text_objects = [obj for obj in context.selected_objects if obj.type == 'FONT']
        active = context.active_object
        if active is not None and active.type == 'FONT' and active not in text_objects:
            text_objects.append(active)

        if not text_objects:
            self.report({'WARNING'}, "Select at least one Text object")
            return {'CANCELLED'}

        if active.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError as exc:
                self.report({'ERROR'}, f"Could not leave Edit Mode: {exc}")
                return {'CANCELLED'}

        # Convert only the selected text objects; unrelated selected objects
        # must not be converted along with them.
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in text_objects:
            obj.select_set(True)
        context.view_layer.objects.active = active if active in text_objects else text_objects[0]

        try:
            bpy.ops.object.convert(target='MESH')
        except RuntimeError as exc:
            self.report({'ERROR'}, f"Text conversion failed: {exc}")
            return {'CANCELLED'}

        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        try:
            for obj in mesh_objects:
                context.view_layer.objects.active = obj
                modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                modifier.decimate_type = 'DISSOLVE'
                bpy.ops.object.modifier_apply(modifier=modifier.name)

                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                # Match Mesh > Clean Up > Delete Loose defaults. Enabling
                # loose faces here can erase the filled surfaces of letters.
                bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
                bpy.ops.mesh.remove_doubles(threshold=self.merge_distance)
                bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError as exc:
            if context.object is not None and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'ERROR'}, f"Mesh cleanup failed: {exc}")
            return {'CANCELLED'}

        if mesh_objects:
            context.view_layer.objects.active = mesh_objects[0]
        self.report(
            {'INFO'},
            f"Cleaned {len(mesh_objects)} text object(s); merge distance: {self.merge_distance:.5f} m",
        )
        return {'FINISHED'}


class VIEW3D_OT_SetFontWeight(bpy.types.Operator):
    bl_idname = "view3d.set_persian_font_weight"
    bl_label = "Set Font Weight"
    bl_description = "Apply Regular or Bold to all characters using Blender's native font slots"
    bl_options = {'REGISTER', 'UNDO'}

    weight: bpy.props.EnumProperty(
        items=(
            ('REGULAR', "Regular", "Use the regular font style"),
            ('BOLD', "Bold", "Use the bold font style"),
        ),
        default='REGULAR',
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'FONT'

    def execute(self, context):
        curve = context.active_object.data
        variant_path = _find_font_weight_file(curve.font, self.weight)

        if self.weight == 'BOLD':
            if variant_path is None:
                self.report({'WARNING'}, "This font family has no separate Bold file")
                return {'CANCELLED'}
            curve.font_bold = bpy.data.fonts.load(variant_path, check_existing=True)
            for character in curve.body_format:
                character.use_bold = True
        else:
            if variant_path is not None:
                curve.font = bpy.data.fonts.load(variant_path, check_existing=True)
            for character in curve.body_format:
                character.use_bold = False

        curve.update_tag()
        context.view_layer.update()
        self.report({'INFO'}, f"Font weight: {self.weight.title()}")
        return {'FINISHED'}


class VIEW3D_OT_ResetFontAppearance(bpy.types.Operator):
    bl_idname = "view3d.reset_persian_font_appearance"
    bl_label = "Reset Font Settings"
    bl_description = "Reset size, slant, spacing, offset, extrusion and bevel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'FONT'

    def execute(self, context):
        curve = context.active_object.data
        curve.size = 1.0
        curve.shear = 0.0
        curve.space_character = 1.0
        curve.space_word = 1.0
        curve.space_line = 1.0
        curve.offset_x = 0.0
        curve.extrude = 0.0
        curve.bevel_depth = 0.0
        curve.bevel_resolution = 4
        curve.resolution_u = 12
        curve.update_tag()
        context.view_layer.update()
        self.report({'INFO'}, "Font appearance reset")
        return {'FINISHED'}

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


def _apply_group_font(operator, context, group, label):
    """Apply the font selected in one of the three font groups.

    Path resolution lives in __init__.resolve_font_path so the bundled /
    system / custom convention is stated once. Loading happens here, in an
    operator, never in the enum items callbacks that feed the dropdowns.
    """
    from . import resolve_font_path

    text_object = context.active_object
    if text_object is None or text_object.type != 'FONT':
        operator.report({'WARNING'}, "Please select a text object first")
        return {'CANCELLED'}

    font_path, error = resolve_font_path(context.scene, group)
    if error is not None:
        operator.report({'ERROR'}, error)
        return {'CANCELLED'}

    try:
        font = bpy.data.fonts.load(font_path, check_existing=True)
    except (RuntimeError, OSError) as exc:
        operator.report({'ERROR'}, f"Could not load {os.path.basename(font_path)}: {exc}")
        return {'CANCELLED'}

    text_object.data.font = font
    operator.report({'INFO'}, f"{label} font applied: {os.path.basename(font_path)}")
    return {'FINISHED'}


class VIEW3D_OT_ChangeSystemFont(bpy.types.Operator):
    bl_idname = "view3d.change_system_font"
    bl_label = "Apply System Font"
    bl_description = "Apply the selected operating-system font to the active text object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active is not None and active.type == 'FONT'

    def execute(self, context):
        return _apply_group_font(self, context, 'SYSTEM', "System")


class VIEW3D_OT_ChangeCustomFont(bpy.types.Operator):
    bl_idname = "view3d.change_custom_font"
    bl_label = "Apply Custom Font"
    bl_description = (
        "Apply the selected font from your custom fonts folder or saved list "
        "to the active text object"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active is not None and active.type == 'FONT'

    def execute(self, context):
        return _apply_group_font(self, context, 'CUSTOM', "Custom")


class VIEW3D_OT_ChangePersianFont(bpy.types.Operator):
    bl_idname = "view3d.change_persian_font"
    bl_label = "Change Font"
    bl_description = "Apply the selected bundled font to the active text object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active is not None and active.type == 'FONT'

    def execute(self, context):
        return _apply_group_font(self, context, 'BUNDLED', "Bundled")

class VIEW3D_OT_LoadCustomFont(bpy.types.Operator):
    bl_idname = "view3d.load_custom_font"
    bl_label = "Load Font from Disk"
    bl_description = (
        "Browse for a font file, apply it to the active text object and add it "
        "to the saved custom font list"
    )
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.ttf;*.otf;*.ttc",
        options={'HIDDEN'}
    )

    filepath: bpy.props.StringProperty(
        name="File Path",
        subtype='FILE_PATH'
    )

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active is not None and active.type == 'FONT'

    def invoke(self, context, event):
        from . import system_font_roots

        # Start in a font folder that exists on this platform rather than
        # %WINDIR%, falling back to the home directory where there is none.
        if not self.filepath:
            roots = system_font_roots()
            start = roots[0] if roots else os.path.expanduser('~')
            self.filepath = os.path.join(start, "")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from . import FONT_EXTENSIONS, invalidate_font_caches

        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "Please choose a font file")
            return {'CANCELLED'}

        if not self.filepath.lower().endswith(FONT_EXTENSIONS):
            self.report(
                {'ERROR'},
                "Unsupported file type; choose one of: " + ", ".join(FONT_EXTENSIONS),
            )
            return {'CANCELLED'}

        text_object = context.active_object
        if text_object is None or text_object.type != 'FONT':
            self.report({'WARNING'}, "Please select a text object first")
            return {'CANCELLED'}

        try:
            font = bpy.data.fonts.load(self.filepath, check_existing=True)
        except (RuntimeError, OSError) as exc:
            self.report(
                {'ERROR'},
                f"Could not load {os.path.basename(self.filepath)}: {exc}",
            )
            return {'CANCELLED'}

        text_object.data.font = font

        # A font picked by hand belongs to the Custom group, so remember it.
        pref_container = context.preferences.addons.get(__package__ or __name__)
        if pref_container is not None:
            prefs = pref_container.preferences
            if not any(item.path == self.filepath for item in prefs.saved_fonts):
                item = prefs.saved_fonts.add()
                item.name = os.path.splitext(os.path.basename(self.filepath))[0]
                item.path = self.filepath
                invalidate_font_caches('CUSTOM')

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        self.report({'INFO'}, f"Applied font: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class VIEW3D_OT_RefreshPersianFonts(bpy.types.Operator):
    bl_idname = "view3d.refresh_persian_fonts"
    bl_label = "Refresh Fonts"
    bl_description = "Rebuild the bundled, system and custom font lists"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.window_manager is not None

    def execute(self, context):
        from . import invalidate_font_caches

        # Drop the cached items, then make the items callbacks run again.
        invalidate_font_caches()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        self.report({'INFO'}, "Font lists refreshed")
        return {'FINISHED'}


class VIEW3D_OT_SaveCurrentFont(bpy.types.Operator):
    bl_idname = "view3d.save_current_persian_font"
    bl_label = "Save Current Font"
    bl_description = "Save the active text object's font into the saved list"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active is not None and active.type == 'FONT'

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
        # Fallback 2: use the current System or Custom selection
        if not (font_path and os.path.isabs(font_path) and os.path.exists(font_path)):
            for property_name in ("system_font", "custom_font"):
                candidate = getattr(context.scene, property_name, '')
                if candidate and os.path.isabs(candidate) and os.path.exists(candidate):
                    font_path = candidate
                    break
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
            from . import invalidate_font_caches

            item = prefs.saved_fonts.add()
            item.name = os.path.splitext(os.path.basename(font_path))[0]
            item.path = font_path
            invalidate_font_caches('CUSTOM')
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

        # One-click setup: creates the sample, enables RTL and starts typing.
        row = layout.row()
        row.scale_y = 1.35
        row.operator("view3d.add_persian_text", text="Add Text", icon='ADD')
        row.operator("view3d.paste_persian_text", text="Paste", icon='PASTEDOWN')
        clean_row = layout.row()
        clean_row.scale_y = 1.2
        clean_row.operator("view3d.persian_mesh_clean", text="Mesh Clean", icon='MOD_DECIM')

        # Main Section
        box = layout.box()
        box.label(text="Persian / Arabic Text", icon='FONT_DATA')
        
        # Enable Button
        row = box.row()
        row.operator("view3d.persian_text_mode", text="Enable Persian/Arabic Text", icon='GREASEPENCIL')

        # Paste Normalize Button
        row = box.row()
        row.operator("pt.paste_persian_normalize", text="Paste Persian (Normalize)")
        
        # Toggle Text Direction Button
        row = box.row()
        row.operator("view3d.toggle_text_direction", text="Toggle Text Direction", icon='ARROW_LEFTRIGHT')
        
        # Font Settings
        box = layout.box()
        box.label(text="Bundled Fonts:", icon='PREFERENCES')
        
        # Font List
        row = box.row(align=True)
        row.prop(context.scene, "persian_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        
        # Change Font Button
        row = box.row(align=True)
        row.operator("view3d.change_persian_font", text="Change Font", icon='FILE_FONT')
        row.operator("view3d.save_current_persian_font", text="", icon='FOLDER_REDIRECT')

        text_obj = context.active_object
        appearance = box.column(align=True)
        appearance.active = text_obj is not None and text_obj.type == 'FONT'
        appearance.label(text="Appearance", icon='SETTINGS')
        if text_obj is not None and text_obj.type == 'FONT':
            curve = text_obj.data

            row = appearance.row(align=True)
            regular = row.operator("view3d.set_persian_font_weight", text="Regular")
            regular.weight = 'REGULAR'
            bold = row.operator("view3d.set_persian_font_weight", text="Bold")
            bold.weight = 'BOLD'

            row = appearance.row(align=True)
            row.prop(curve, "size", text="Size")
            row.prop(curve, "shear", text="Slant")

            appearance.prop(curve, "space_character", text="Character Spacing")
            appearance.prop(curve, "space_word", text="Word Spacing")
            appearance.prop(curve, "space_line", text="Line Spacing")

            row = appearance.row(align=True)
            row.prop(curve, "offset_x", text="Offset")
            row.prop(curve, "extrude", text="Extrude")

            row = appearance.row(align=True)
            row.prop(curve, "bevel_depth", text="Bevel")
            row.prop(curve, "bevel_resolution", text="Segments")

            appearance.prop(curve, "resolution_u", text="Curve Resolution")
            appearance.operator(
                "view3d.reset_persian_font_appearance",
                text="Reset Font Settings",
                icon='LOOP_BACK',
            )
        else:
            appearance.label(text="Select a Text object", icon='INFO')

        # System Fonts: the operating system's own font folders. Cross-platform
        # since 3.1; pt.scan_system_fonts refreshes the cache behind it.
        box = layout.box()
        box.label(text="System Fonts:", icon='FILEBROWSER')
        row = box.row(align=True)
        row.prop(context.scene, "system_font", text="Font")
        row.operator("view3d.change_system_font", text="", icon='CHECKMARK')
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        box.operator("pt.scan_system_fonts", text="Rescan System Fonts", icon='FILE_REFRESH')

        # Custom Fonts: the user's own folder plus the fonts they saved.
        box = layout.box()
        box.label(text="Custom Fonts:", icon='FILE_FOLDER')
        row = box.row(align=True)
        row.prop(context.scene, "custom_font", text="Font")
        row.operator("view3d.change_custom_font", text="", icon='CHECKMARK')
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        row = box.row(align=True)
        row.operator("view3d.load_custom_font", text="Load Font from Disk", icon='FILE_FOLDER')
        row.operator("pt.choose_custom_fonts_dir", text="", icon='PREFERENCES')

# Export all classes
__classes__ = [
    VIEW3D_OT_AddPersianText,
    VIEW3D_OT_PastePersianText,
    VIEW3D_OT_MeshClean,
    VIEW3D_OT_SetFontWeight,
    VIEW3D_OT_ResetFontAppearance,
    VIEW3D_OT_ToggleTextDirection,
    VIEW3D_OT_ChangePersianFont,
    VIEW3D_OT_LoadCustomFont,
    VIEW3D_OT_RefreshPersianFonts,
    VIEW3D_OT_SaveCurrentFont,
    VIEW3D_OT_ChangeSystemFont,
    VIEW3D_OT_ChangeCustomFont,
    PersiantypePanel
]
