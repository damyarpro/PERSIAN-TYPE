"""Persian/Arabic support for Video Sequencer text strips.

A VSE text strip is drawn by the same glyph pipeline as a FONT object: no
HarfBuzz shaping and no bidi algorithm. It differs from a FONT object in one
decisive way -- it has no Edit Mode and no caret -- so the modal live-typing
model of ``VIEW3D_OT_PersianTextMode`` does not transfer.

This module therefore uses a field-and-apply model:

    Scene.persian_strip_text   logical Persian text, in reading order
              |  Apply         strip.text = swap_lines(link_text(logical))
              v
    TextStrip.text             presentation forms, visually reversed
              |  Load          logical = unlink_text(swap_lines(strip.text))
              v
    Scene.persian_strip_text

The shaping engine is the single source of truth for both directions; nothing
here reimplements shaping. The read-back direction is lossy -- measured against
the engine as it stands: Keheh comes back as its presentation form U+FB8E (the
defect in CLAUDE.md section 4), and left-to-right runs (Latin words, digit
groups) come back reversed, because ``unlink_text`` reverses the whole string
while ``link_text`` had kept those runs in logical order. ``Load`` therefore
re-shapes what it read and warns when the result does not match the strip's
current text, instead of silently handing back a corrupted buffer. Nothing here
tries to repair the engine.

Operators use the ``pt.*`` idname prefix: ``sequencer.*`` is Blender's own
operator namespace and must not be extended by an add-on.
"""

import os

import bpy
from bpy.props import StringProperty

from . import Persiantype as Ar

# Deliberately not imported from panel.py: __init__ -> panel and
# __init__ -> Persiantype are the only module edges this project allows, and a
# sequencer -> panel edge would add a third for the sake of one path join.
_FONT_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")

# Sample used when a strip is created with an empty text field. Deliberately
# carries no version number, so it cannot drift the way panel.py's sample did.
_DEFAULT_STRIP_TEXT = "متن فارسی"


def _active_text_strip(context):
    """Return the active strip if it is a text strip, else None.

    Cheap enough for poll(): three attribute reads and an isinstance test.
    """
    scene = getattr(context, "scene", None)
    if scene is None:
        return None
    editor = scene.sequence_editor
    if editor is None:
        return None
    strip = editor.active_strip
    if strip is None or not isinstance(strip, bpy.types.TextStrip):
        return None
    return strip


def _shape(logical_text):
    """Logical reading-order text -> presentation forms in strip order."""
    return Ar.swap_lines(Ar.link_text(list(logical_text)))


def _unshape(shaped_text):
    """Presentation forms in strip order -> logical reading-order text."""
    return ''.join(Ar.unlink_text(Ar.swap_lines(shaped_text)))


class PT_OT_SeqPastePersianText(bpy.types.Operator):
    bl_idname = "pt.seq_paste_persian_text"
    bl_label = "Paste"
    bl_description = (
        "Paste the clipboard into the Persian text field with normalization "
        "(Arabic Yeh/Kaf to Persian, remove Kashida and ZWJ)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return getattr(context, "scene", None) is not None

    def execute(self, context):
        from . import normalize_persian_text

        clipboard = context.window_manager.clipboard
        if not clipboard:
            self.report({'ERROR'}, "Clipboard is empty")
            return {'CANCELLED'}

        context.scene.persian_strip_text = normalize_persian_text(clipboard)
        self.report({'INFO'}, "Clipboard pasted into the Persian text field")
        return {'FINISHED'}


class PT_OT_SeqLoadPersianText(bpy.types.Operator):
    bl_idname = "pt.seq_load_persian_text"
    bl_label = "Load from Strip"
    bl_description = (
        "Read the active text strip back into the Persian text field for "
        "editing. Keheh and left-to-right runs do not round-trip exactly; "
        "you are warned when they do not"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _active_text_strip(context) is not None

    def execute(self, context):
        from . import normalize_persian_text

        strip = _active_text_strip(context)
        if strip is None:
            self.report({'ERROR'}, "No active text strip in the sequencer")
            return {'CANCELLED'}

        shaped = strip.text
        if not shaped:
            self.report({'ERROR'}, "The active text strip is empty")
            return {'CANCELLED'}

        # normalize repairs the unshaper's Persian Yeh -> Arabic Yeh
        # degradation; it cannot repair the Keheh defect, which is why the
        # result is checked against the original below rather than trusted.
        logical = normalize_persian_text(_unshape(shaped))
        context.scene.persian_strip_text = logical

        if _shape(logical) != shaped:
            self.report(
                {'WARNING'},
                "Loaded text does not re-shape to the strip's current text. "
                "Keheh returns as a presentation form and Latin or digit runs "
                "return reversed. Fix the field before applying",
            )
            return {'FINISHED'}

        self.report({'INFO'}, "Strip text loaded into the Persian text field")
        return {'FINISHED'}


class PT_OT_SeqApplyPersianText(bpy.types.Operator):
    bl_idname = "pt.seq_apply_persian_text"
    bl_label = "Apply to Strip"
    bl_description = (
        "Shape the Persian text field and write it into the active text "
        "strip, anchored and aligned right so it reads right-to-left"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _active_text_strip(context) is not None

    def execute(self, context):
        from . import normalize_persian_text

        strip = _active_text_strip(context)
        if strip is None:
            self.report({'ERROR'}, "No active text strip in the sequencer")
            return {'CANCELLED'}

        logical = context.scene.persian_strip_text
        if not logical:
            self.report({'ERROR'}, "The Persian text field is empty")
            return {'CANCELLED'}

        # The field can be edited or pasted into directly, bypassing the paste
        # operator, so normalize here too and store the normalized form back so
        # field and strip stay in step.
        logical = normalize_persian_text(logical)
        context.scene.persian_strip_text = logical

        strip.text = _shape(logical)

        missing = []
        for prop_name in ("alignment_x", "anchor_x"):
            if hasattr(strip, prop_name):
                setattr(strip, prop_name, 'RIGHT')
            else:
                missing.append(prop_name)

        if missing:
            self.report(
                {'WARNING'},
                "Text applied, but this Blender build has no "
                + " or ".join(missing)
                + " on text strips; set right alignment by hand",
            )
            return {'FINISHED'}

        self.report({'INFO'}, "Persian text applied to the active strip")
        return {'FINISHED'}


class PT_OT_SeqApplyPersianFont(bpy.types.Operator):
    bl_idname = "pt.seq_apply_persian_font"
    bl_label = "Apply Font"
    bl_description = (
        "Apply the selected Persian font to the active text strip. Blender's "
        "default interface font does not render Persian"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _active_text_strip(context) is not None

    def execute(self, context):
        strip = _active_text_strip(context)
        if strip is None:
            self.report({'ERROR'}, "No active text strip in the sequencer")
            return {'CANCELLED'}

        selected = getattr(context.scene, "persian_font", "")
        if not selected:
            self.report({'ERROR'}, "No font selected in the Font dropdown")
            return {'CANCELLED'}

        # Bundled fonts are stored as a bare filename, saved and custom fonts
        # as an absolute path. Same convention as view3d.change_persian_font.
        if os.path.isabs(selected):
            font_path = selected
        else:
            font_path = os.path.join(_FONT_FOLDER, selected)

        if not os.path.exists(font_path):
            self.report({'ERROR'}, f"Font file not found: {font_path}")
            return {'CANCELLED'}

        try:
            font = bpy.data.fonts.load(font_path, check_existing=True)
        except (RuntimeError, OSError) as exc:
            self.report({'ERROR'}, f"Could not load {os.path.basename(font_path)}: {exc}")
            return {'CANCELLED'}

        strip.font = font
        self.report({'INFO'}, f"Font applied: {font.name}")
        return {'FINISHED'}


class PT_OT_SeqAddPersianStrip(bpy.types.Operator):
    bl_idname = "pt.seq_add_persian_strip"
    bl_label = "Add Text Strip"
    bl_description = (
        "Create a text strip at the current frame, already right-aligned and "
        "carrying the Persian text field, then make it the active strip"
    )
    bl_options = {'REGISTER', 'UNDO'}

    length: bpy.props.IntProperty(
        name="Length",
        description="Strip length in frames",
        default=50,
        min=1,
    )

    @classmethod
    def poll(cls, context):
        area = getattr(context, "area", None)
        return (
            getattr(context, "scene", None) is not None
            and area is not None
            and area.type == 'SEQUENCE_EDITOR'
        )

    def execute(self, context):
        scene = context.scene

        # Returns the existing editor when the scene already has one.
        editor = scene.sequence_editor_create()

        # Place the strip above everything already in the timeline so it
        # cannot silently overlap an existing strip.
        used = [s.channel for s in editor.strips]
        channel = min(max(used) + 1, 128) if used else 1

        try:
            strip = editor.strips.new_effect(
                name="Persian Text",
                type='TEXT',
                channel=channel,
                frame_start=scene.frame_current,
                length=self.length,
            )
        except RuntimeError as exc:
            self.report({'ERROR'}, f"Could not create the text strip: {exc}")
            return {'CANCELLED'}

        logical = scene.persian_strip_text or _DEFAULT_STRIP_TEXT
        scene.persian_strip_text = logical
        strip.text = _shape(logical)

        # Guarded the same way as the Apply operator: a build without these
        # enums should report, not raise.
        missing = [n for n in ("alignment_x", "anchor_x") if not hasattr(strip, n)]
        if missing:
            self.report(
                {'WARNING'},
                "Strip created, but this Blender build has no "
                + " or ".join(missing)
                + "; align it to the right by hand",
            )
        else:
            strip.alignment_x = 'RIGHT'
            strip.anchor_x = 'RIGHT'

        editor.active_strip = strip
        self.report({'INFO'}, f"Created text strip on channel {channel}")
        return {'FINISHED'}


class SEQUENCER_PT_persiantype(bpy.types.Panel):
    bl_label = "Persian type Panel"
    bl_idname = "SEQUENCER_PT_persiantype"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Persian type"

    @classmethod
    def poll(cls, context):
        return getattr(context, "scene", None) is not None

    def draw(self, context):
        layout = self.layout
        strip = _active_text_strip(context)

        row = layout.row()
        row.scale_y = 1.35
        row.operator("pt.seq_add_persian_strip", text="Add Text Strip", icon='ADD')

        box = layout.box()
        box.label(text="Persian / Arabic Text", icon='FONT_DATA')
        if strip is None:
            box.label(text="Select a Text strip", icon='INFO')
        else:
            box.label(text=strip.name, icon='SEQ_STRIP_DUPLICATE')

        box.prop(context.scene, "persian_strip_text", text="Text")

        row = box.row(align=True)
        row.operator("pt.seq_paste_persian_text", text="Paste", icon='PASTEDOWN')
        row.operator("pt.seq_load_persian_text", text="Load from Strip", icon='IMPORT')

        row = box.row()
        row.scale_y = 1.35
        row.operator("pt.seq_apply_persian_text", text="Apply to Strip", icon='CHECKMARK')

        box = layout.box()
        box.label(text="Font Settings:", icon='PREFERENCES')
        row = box.row(align=True)
        row.prop(context.scene, "persian_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        box.operator("pt.seq_apply_persian_font", text="Apply Font", icon='FILE_FONT')


__classes__ = (
    PT_OT_SeqPastePersianText,
    PT_OT_SeqLoadPersianText,
    PT_OT_SeqApplyPersianText,
    PT_OT_SeqApplyPersianFont,
    PT_OT_SeqAddPersianStrip,
    SEQUENCER_PT_persiantype,
)


def register():
    bpy.types.Scene.persian_strip_text = StringProperty(
        name="Persian Text",
        description=(
            "Persian/Arabic text in logical reading order. Apply it to shape "
            "it into the active text strip"
        ),
        default="",
    )
    for cls in __classes__:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(__classes__):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.persian_strip_text
