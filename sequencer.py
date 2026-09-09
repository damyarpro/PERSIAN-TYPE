"""Persian/Arabic support for Video Sequencer text strips.

A VSE text strip is drawn by the same glyph pipeline as a FONT object: no
HarfBuzz shaping and no bidi algorithm. It differs from a FONT object in one
decisive way -- it has no Edit Mode and no caret -- so the modal live-typing
model of ``VIEW3D_OT_PersianTextMode`` does not transfer.

This module therefore uses a field-and-apply model. The editable field is a
collection of lines rather than one string, because a strip's text is routinely
multi-line and Blender's single-line ``StringProperty`` widget cannot enter a
newline:

    Scene.persian_strip_lines  logical Persian text, one entry per line
              |  Apply         strip.text = swap_lines(link_text("\\n".join(...)))
              v
    TextStrip.text             presentation forms, visually reversed
              |  Load          logical = unlink_text(swap_lines(strip.text))
              v                          then split back on "\\n"
    Scene.persian_strip_lines

The shaping engine is the single source of truth for both directions; nothing
here reimplements shaping. The read-back direction is no longer exact for every
input: ``link_text`` is not injective, so two different logical strings can
shape to one identical body, and no unshaper can choose between them. ``Load``
therefore re-shapes what it read and warns when the result does not match the
strip's current text, instead of silently handing back a buffer that would
render differently. Nothing here tries to repair the engine.

Appearance properties are drawn straight onto the strip with ``layout.prop``.
That is deliberate: direct property editing is what Blender users expect, and it
gets undo, keyframing and driver support for free, none of which an operator
wrapper would provide.

Operators use the ``pt.*`` idname prefix: ``sequencer.*`` is Blender's own
operator namespace and must not be extended by an add-on. Calling into that
namespace is a different matter -- the text style presets below are Blender's
own mechanism, driven by Blender's own ``sequencer.text_strip_style_preset_add``
and ``script.execute_preset``, and nothing here reimplements them.
"""

import math
import os

import bpy
from bpy.props import (
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from . import Persiantype as Ar

# Font path resolution lives in __init__.resolve_font_path. The bundled,
# system and custom groups share one convention -- bundled fonts are a bare
# filename, the other two an absolute path -- and a second copy of it here
# would be free to drift.

# Sample used when a strip is created with an empty text field. Deliberately
# carries no version number, so it cannot drift the way panel.py's sample did.
_DEFAULT_STRIP_TEXT = "متن فارسی"

# Blender registers this panel in the Properties editor header and keeps the
# name of the active text style preset in its ``bl_label``. It is the shared
# state the preset menu below reads and writes, not a class this add-on owns.
_STYLE_PRESET_OWNER = "STRIP_PT_effect_text_style_presets"

# Appearance values a freshly created text strip carries in Blender 5.2,
# measured by reading a new strip rather than taken from the RNA defaults.
# The two disagree and the RNA is the wrong one to trust here: RNA reports
# font_size 0.0, location (0, 0) and a fully transparent black colour, none of
# which a new strip actually has.
#
# alignment_x and anchor_x deviate from Blender on purpose. A new strip is
# CENTER on both; right alignment is the entire point of this add-on, so Reset
# restores the add-on's baseline rather than Blender's.
_STRIP_APPEARANCE_DEFAULTS = (
    ("font_size", 60.0),
    ("location", (0.5, 0.5)),
    ("wrap_width", 1.0),
    ("space_line", 1.0),
    ("use_absolute_line_spacing", False),
    ("abs_space_line", 60.0),
    ("color", (1.0, 1.0, 1.0, 1.0)),
    ("use_bold", False),
    ("use_italic", False),
    ("alignment_x", 'RIGHT'),
    ("anchor_x", 'RIGHT'),
    ("anchor_y", 'CENTER'),
    ("use_shadow", False),
    ("shadow_color", (0.0, 0.0, 0.0, 0.7)),
    ("shadow_angle", math.radians(65.0)),
    ("shadow_offset", 0.04),
    ("shadow_blur", 0.0),
    ("use_outline", False),
    ("outline_color", (0.0, 0.0, 0.0, 0.7)),
    ("outline_width", 0.05),
    ("use_box", False),
    ("box_color", (0.2, 0.2, 0.2, 0.7)),
    ("box_margin", 0.01),
    ("box_roundness", 0.0),
)


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


def _preset_strip(context):
    """Return the strip Blender's preset machinery acts on, if it is a text strip.

    Both ``sequencer.text_strip_style_preset_add`` and the preset files it
    writes resolve their target through ``bpy.context.active_strip``. Measured
    on 5.2, that context member comes from the *workspace's* sequencer scene,
    not from ``context.scene``, and reads None while the workspace has none --
    so it is not interchangeable with ``_active_text_strip`` and has to be
    checked separately before the preset controls are offered.

    Cheap enough for draw(): one attribute read and an isinstance test.
    """
    strip = getattr(context, "active_strip", None)
    if strip is None or not isinstance(strip, bpy.types.TextStrip):
        return None
    return strip


def _shape(logical_text):
    """Logical reading-order text -> presentation forms in strip order."""
    return Ar.swap_lines(Ar.link_text(list(logical_text)))


def _unshape(shaped_text):
    """Presentation forms in strip order -> logical reading-order text."""
    return ''.join(Ar.unlink_text(Ar.swap_lines(shaped_text)))


def _shape_for_display(logical_text):
    """Presentation forms for drawing a logical string in a UI label.

    Blender's interface font has no Arabic shaping and no bidi algorithm --
    the same limitation a FONT object and a text strip have -- so a logical
    string handed to a label comes out left-to-right with every letter in its
    isolated form, so a word reads backwards and its letters do not join.
    The shaped form is already presentation forms in visual order,
    which is exactly what an unshaped left-to-right renderer needs, so a label
    fed the shaped string draws readable Persian.

    This is a read path only. The shaped string is never written back into
    ``persian_strip_lines``; the logical text stays the single source of truth
    for Apply, as section 3 of CLAUDE.md requires.

    Pure ASCII is returned untouched. That is both a shortcut and a guarantee:
    it keeps a Latin strip name byte-identical instead of routing it through
    the bidi engine, and it costs 0.02 us against the 50 us the engine takes
    for a 12 character Latin string.
    """
    if not logical_text or logical_text.isascii():
        return logical_text
    return _shape(logical_text)


def _joined_lines(scene):
    """The line collection as one logical string, newline separated."""
    return "\n".join(line.text for line in scene.persian_strip_lines)


def _replace_lines(scene, logical_text):
    """Rebuild the line collection from a logical string.

    CR is folded into LF first. Clipboard text on Windows arrives CRLF
    separated, and a stray CR left on the end of a line would be handed to the
    shaping engine as an ordinary character.
    """
    flattened = logical_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = scene.persian_strip_lines
    lines.clear()
    for chunk in flattened.split("\n"):
        lines.add().text = chunk
    scene.persian_strip_lines_index = 0
    return len(lines)


class PT_PersianStripLine(PropertyGroup):
    """One line of the logical Persian text destined for a strip."""

    text: StringProperty(
        name="Line",
        description="One line of Persian/Arabic text, in logical reading order",
        default="",
    )


class PT_UL_persian_strip_lines(bpy.types.UIList):
    """Read-only preview of the text lines, one row per line.

    The rows are labels rather than editable fields, which is a deliberate
    split. Only a label can be given the *shaped* text and so read as Persian;
    an editable field has to be bound to the logical ``text`` property and
    would draw it garbled, and typing into a shaped string would write
    presentation forms straight back into the logical buffer. Editing
    therefore happens in the single field the panel draws under the list,
    bound to whichever row is active.
    """

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        row = layout.row(align=True)
        number = row.row()
        number.scale_x = 0.22
        number.label(text=str(index + 1))
        # Fed presentation forms on purpose -- see _shape_for_display. A label
        # showing shaped text is not a sign that the logical buffer has been
        # corrupted; item.text still holds the logical string.
        shaped = row.row()
        shaped.alignment = 'RIGHT'
        shaped.label(text=_shape_for_display(item.text))


class PT_OT_SeqLineAdd(bpy.types.Operator):
    bl_idname = "pt.seq_line_add"
    bl_label = "Add Line"
    bl_description = "Add an empty line below the selected line"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return getattr(context, "scene", None) is not None

    def execute(self, context):
        lines = context.scene.persian_strip_lines
        lines.add()
        context.scene.persian_strip_lines_index = len(lines) - 1
        return {'FINISHED'}


class PT_OT_SeqLineRemove(bpy.types.Operator):
    bl_idname = "pt.seq_line_remove"
    bl_label = "Remove Line"
    bl_description = "Remove the selected line"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        scene = getattr(context, "scene", None)
        return scene is not None and len(scene.persian_strip_lines) > 0

    def execute(self, context):
        scene = context.scene
        lines = scene.persian_strip_lines
        index = scene.persian_strip_lines_index
        if not 0 <= index < len(lines):
            self.report({'ERROR'}, f"No line selected at index {index}")
            return {'CANCELLED'}

        lines.remove(index)
        scene.persian_strip_lines_index = max(0, min(index, len(lines) - 1))
        return {'FINISHED'}


class PT_OT_SeqLineMove(bpy.types.Operator):
    bl_idname = "pt.seq_line_move"
    bl_label = "Move Line"
    bl_description = "Move the selected line up or down"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        description="Direction to move the selected line in",
        items=(
            ('UP', "Up", "Move the line one position earlier"),
            ('DOWN', "Down", "Move the line one position later"),
        ),
        default='UP',
    )

    @classmethod
    def poll(cls, context):
        scene = getattr(context, "scene", None)
        return scene is not None and len(scene.persian_strip_lines) > 1

    def execute(self, context):
        scene = context.scene
        lines = scene.persian_strip_lines
        index = scene.persian_strip_lines_index
        if not 0 <= index < len(lines):
            self.report({'ERROR'}, f"No line selected at index {index}")
            return {'CANCELLED'}

        target = index - 1 if self.direction == 'UP' else index + 1
        if not 0 <= target < len(lines):
            self.report(
                {'ERROR'},
                "The selected line is already at the "
                + ("top" if self.direction == 'UP' else "bottom"),
            )
            return {'CANCELLED'}

        lines.move(index, target)
        scene.persian_strip_lines_index = target
        return {'FINISHED'}


class PT_OT_SeqPastePersianText(bpy.types.Operator):
    bl_idname = "pt.seq_paste_persian_text"
    bl_label = "Paste"
    bl_description = (
        "Replace the line list with the clipboard, normalized (Arabic Yeh/Kaf "
        "to Persian, remove Kashida and ZWJ) and split into one entry per line"
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

        count = _replace_lines(context.scene, normalize_persian_text(clipboard))
        self.report({'INFO'}, f"Clipboard pasted into {count} line(s)")
        return {'FINISHED'}


class PT_OT_SeqLoadPersianText(bpy.types.Operator):
    bl_idname = "pt.seq_load_persian_text"
    bl_label = "Load from Strip"
    bl_description = (
        "Read the active text strip back into the line list for editing, one "
        "entry per line. A few inputs cannot be recovered exactly; you are "
        "warned whenever the recovered text would render differently"
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

        # normalize folds Arabic Yeh onto Persian Yeh, matching every other
        # ingest path. The re-shape check below still runs because link_text
        # is not injective, so recovery cannot be trusted on its own.
        logical = normalize_persian_text(_unshape(shaped))
        count = _replace_lines(context.scene, logical)

        if _shape(logical) != shaped:
            self.report(
                {'WARNING'},
                "Loaded text does not re-shape to the strip's current text, "
                "so applying it now would change what the strip shows. Check "
                "the lines before applying",
            )
            return {'FINISHED'}

        self.report({'INFO'}, f"Strip text loaded into {count} line(s)")
        return {'FINISHED'}


class PT_OT_SeqApplyPersianText(bpy.types.Operator):
    bl_idname = "pt.seq_apply_persian_text"
    bl_label = "Apply to Strip"
    bl_description = (
        "Join the lines, shape them and write the result into the active text "
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

        scene = context.scene
        # Lines can be typed or pasted into directly, bypassing the paste
        # operator, so normalize in place. Normalization never adds or removes
        # a newline, so this cannot change the line count or disturb the
        # selected row.
        for line in scene.persian_strip_lines:
            normalized = normalize_persian_text(line.text)
            if normalized != line.text:
                line.text = normalized

        logical = _joined_lines(scene)
        if not logical.strip():
            self.report({'ERROR'}, "The line list is empty")
            return {'CANCELLED'}

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

        self.report(
            {'INFO'},
            f"Applied {len(scene.persian_strip_lines)} line(s) to the active strip",
        )
        return {'FINISHED'}


class PT_OT_SeqResetAppearance(bpy.types.Operator):
    bl_idname = "pt.seq_reset_appearance"
    bl_label = "Reset Appearance"
    bl_description = (
        "Restore size, placement, spacing, style, shadow, outline and box to "
        "the values a new text strip carries. Alignment and anchor stay on "
        "the right, which is this add-on's baseline"
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

        applied = 0
        missing = []
        for prop_name, value in _STRIP_APPEARANCE_DEFAULTS:
            if not hasattr(strip, prop_name):
                missing.append(prop_name)
                continue
            setattr(strip, prop_name, value)
            applied += 1

        if missing:
            self.report(
                {'WARNING'},
                f"Reset {applied} appearance setting(s); this Blender build "
                "has no " + ", ".join(missing) + " on text strips",
            )
            return {'FINISHED'}

        self.report(
            {'INFO'},
            f"Reset {applied} appearance settings, alignment and anchor kept right",
        )
        return {'FINISHED'}


class PT_OT_SeqApplyPersianFont(bpy.types.Operator):
    bl_idname = "pt.seq_apply_persian_font"
    bl_label = "Apply Font"
    bl_description = (
        "Apply the font selected in the given group to the active text strip. "
        "Blender's default interface font does not render Persian"
    )
    bl_options = {'REGISTER', 'UNDO'}

    # One operator with a group argument rather than three near-identical
    # ones: the three groups differ only in which Scene enum they read, and
    # resolve_font_path already knows that mapping.
    source: EnumProperty(
        name="Source",
        description="Which of the three font groups to take the selection from",
        items=(
            ('BUNDLED', "Bundled", "Fonts shipped with the add-on"),
            ('SYSTEM', "System", "Fonts installed in the operating system"),
            ('CUSTOM', "Custom", "Your custom fonts folder and saved list"),
        ),
        default='BUNDLED',
    )

    @classmethod
    def poll(cls, context):
        return _active_text_strip(context) is not None

    def execute(self, context):
        from . import resolve_font_path

        strip = _active_text_strip(context)
        if strip is None:
            self.report({'ERROR'}, "No active text strip in the sequencer")
            return {'CANCELLED'}

        font_path, error = resolve_font_path(context.scene, self.source)
        if error is not None:
            self.report({'ERROR'}, error)
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
        "carrying the Persian text lines, then make it the active strip"
    )
    bl_options = {'REGISTER', 'UNDO'}

    length: IntProperty(
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

        logical = _joined_lines(scene)
        if not logical.strip():
            logical = _DEFAULT_STRIP_TEXT
            _replace_lines(scene, logical)
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


class PT_MT_text_style_presets(bpy.types.Menu):
    """Blender's text strip style presets, surfaced in the sequencer sidebar.

    Blender ships the entire mechanism -- the ``sequencer/text_style`` preset
    directory, the add/remove operator and ``script.execute_preset`` -- but
    only draws it in the Properties editor header, which the Video Sequencer
    sidebar cannot reach. This menu is a second view onto that one mechanism.
    It defines no storage, no file format and no apply logic of its own; the
    three ``preset_*`` attributes and the inherited ``draw_preset`` are the
    whole implementation.

    The one piece of state that needs care is which preset is active. Blender
    keeps it in the ``bl_label`` of whichever class ``script.execute_preset``
    was invoked from, while ``remove_active`` on the add operator reads that
    label off ``STRIP_PT_effect_text_style_presets`` specifically. A second
    view would therefore drift out of step with Blender's own: choosing a
    preset here would rename this class and leave Blender's showing the
    previous one, and Remove would then delete that previous one. So the label
    is read from Blender's class and ``post_cb`` pushes this class's back into
    it, leaving exactly one source of truth.
    """

    bl_idname = "PT_MT_text_style_presets"
    bl_label = "Text Style Presets"

    preset_subdir = "sequencer/text_style"
    preset_operator = "script.execute_preset"
    preset_add_operator = "sequencer.text_strip_style_preset_add"

    draw = bpy.types.Menu.draw_preset

    @classmethod
    def _owner(cls):
        """Blender's preset panel class, or None on a build without it."""
        return getattr(bpy.types, _STYLE_PRESET_OWNER, None)

    @classmethod
    def active_preset_name(cls):
        """Name of the active preset, as Blender records it."""
        return getattr(cls._owner(), "bl_label", None) or cls.bl_label

    @classmethod
    def post_cb(cls, context, filepath):
        """Mirror the label Blender just wrote here onto Blender's own class.

        Called by ``script.execute_preset`` after it has run the preset file
        and set ``cls.bl_label`` to the chosen preset's name.
        """
        del context, filepath
        owner = cls._owner()
        if owner is not None:
            owner.bl_label = cls.bl_label


class SEQUENCER_PT_persiantype(bpy.types.Panel):
    bl_label = "Persian type Panel"
    bl_idname = "SEQUENCER_PT_persiantype"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Persian type"

    @classmethod
    def poll(cls, context):
        return getattr(context, "scene", None) is not None

    def _draw_appearance(self, context, layout, strip):
        """Appearance controls, drawn straight onto the strip.

        Greyed out rather than hidden when there is no strip, matching the
        Appearance box in the 3D viewport panel.
        """
        box = layout.box()
        appearance = box.column()
        appearance.active = strip is not None
        appearance.label(text="Appearance", icon='SETTINGS')

        preset_row = appearance.row(align=True)
        # enabled, not just active: the add operator has no poll of its own
        # and would raise on a None strip. It resolves its target through
        # bpy.context.active_strip, so the presets are offered only when that
        # names the same strip the rest of this section edits -- otherwise a
        # preset could be saved from, or applied to, a strip not shown here.
        # Compared with ==, not is: two reads of the same strip hand back two
        # different bpy_struct wrappers, and only == compares what they wrap.
        preset_row.enabled = strip is not None and _preset_strip(context) == strip
        # Deliberately not run through _shape_for_display. A preset name is
        # user text and could be Persian, but the menu this labels is drawn by
        # Blender's own draw_preset and lists those names unshaped. Shaping
        # only the header would leave the active preset unrecognisable against
        # the list it was chosen from.
        preset_row.menu(
            PT_MT_text_style_presets.bl_idname,
            text=PT_MT_text_style_presets.active_preset_name(),
            icon='PRESET',
        )
        preset_row.operator(
            "sequencer.text_strip_style_preset_add", text="", icon='ADD',
        )
        preset_row.operator(
            "sequencer.text_strip_style_preset_add", text="", icon='REMOVE',
        ).remove_active = True

        if strip is None:
            appearance.label(text="Select a Text strip", icon='INFO')
            return

        col = appearance.column(align=True)
        col.prop(strip, "font_size", text="Size")
        col.prop(strip, "location", text="Location")
        col.prop(strip, "wrap_width", text="Wrap Width")

        col = appearance.column(align=True)
        col.prop(strip, "use_absolute_line_spacing", text="Absolute Line Spacing")
        # The two spacing properties are mutually exclusive in Blender's own
        # renderer, so only the one in effect is shown.
        if strip.use_absolute_line_spacing:
            col.prop(strip, "abs_space_line", text="Line Spacing")
        else:
            col.prop(strip, "space_line", text="Line Spacing")

        col = appearance.column(align=True)
        col.prop(strip, "color", text="Color")
        row = col.row(align=True)
        row.prop(strip, "use_bold", text="Bold", toggle=True)
        row.prop(strip, "use_italic", text="Italic", toggle=True)
        # Blender fakes both by transforming the regular face; neither loads a
        # real bold or italic file, and Persian letterforms suffer badly for
        # it. The RNA tooltip belongs to Blender and cannot say so, so the
        # panel does.
        col.label(text="Bold/Italic are synthetic, not real faces", icon='INFO')

        col = appearance.column(align=True)
        col.prop(strip, "alignment_x", text="Alignment X")
        col.prop(strip, "anchor_x", text="Anchor X")
        col.prop(strip, "anchor_y", text="Anchor Y")

        col = appearance.column(align=True)
        col.prop(strip, "use_shadow", text="Shadow")
        if strip.use_shadow:
            sub = col.column(align=True)
            sub.prop(strip, "shadow_color", text="Shadow Color")
            sub.prop(strip, "shadow_angle", text="Shadow Angle")
            sub.prop(strip, "shadow_offset", text="Shadow Offset")
            sub.prop(strip, "shadow_blur", text="Shadow Blur")

        col = appearance.column(align=True)
        col.prop(strip, "use_outline", text="Outline")
        if strip.use_outline:
            sub = col.column(align=True)
            sub.prop(strip, "outline_color", text="Outline Color")
            sub.prop(strip, "outline_width", text="Outline Width")

        col = appearance.column(align=True)
        col.prop(strip, "use_box", text="Box")
        if strip.use_box:
            sub = col.column(align=True)
            sub.prop(strip, "box_color", text="Box Color")
            sub.prop(strip, "box_margin", text="Box Margin")
            sub.prop(strip, "box_roundness", text="Box Roundness")

        appearance.operator(
            "pt.seq_reset_appearance",
            text="Reset Appearance",
            icon='LOOP_BACK',
        )

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        strip = _active_text_strip(context)

        row = layout.row()
        row.scale_y = 1.35
        row.operator("pt.seq_add_persian_strip", text="Add Text Strip", icon='ADD')

        box = layout.box()
        box.label(text="Persian / Arabic Text", icon='FONT_DATA')
        if strip is None:
            box.label(text="Select a Text strip", icon='INFO')
        else:
            # Shaped for the same reason the list rows are: a strip the user
            # named in Persian would otherwise draw reversed and disconnected.
            box.label(
                text=_shape_for_display(strip.name),
                icon='SEQ_STRIP_DUPLICATE',
            )

        row = box.row()
        row.template_list(
            "PT_UL_persian_strip_lines",
            "",
            scene,
            "persian_strip_lines",
            scene,
            "persian_strip_lines_index",
            rows=4,
        )
        side = row.column(align=True)
        side.operator("pt.seq_line_add", text="", icon='ADD')
        side.operator("pt.seq_line_remove", text="", icon='REMOVE')
        side.separator()
        side.operator("pt.seq_line_move", text="", icon='TRIA_UP').direction = 'UP'
        side.operator("pt.seq_line_move", text="", icon='TRIA_DOWN').direction = 'DOWN'

        # The list above is a preview; this is the only place a line is typed.
        # It is bound to the logical property, so it draws unshaped -- that is
        # the cost of it being the edit target, and the row above shows the
        # same line shaped.
        lines = scene.persian_strip_lines
        index = scene.persian_strip_lines_index
        edit = box.column(align=True)
        edit.label(text="Edit Active Line:", icon='GREASEPENCIL')
        if 0 <= index < len(lines):
            edit.prop(lines[index], "text", text="")
        else:
            empty = edit.row()
            empty.enabled = False
            empty.label(text="No line selected")

        row = box.row(align=True)
        row.operator("pt.seq_paste_persian_text", text="Paste", icon='PASTEDOWN')
        row.operator("pt.seq_load_persian_text", text="Load from Strip", icon='IMPORT')

        row = box.row()
        row.scale_y = 1.35
        row.operator("pt.seq_apply_persian_text", text="Apply to Strip", icon='CHECKMARK')

        # The three font groups get three boxes, exactly as in the 3D
        # viewport panel, so a strip can be given a bundled, a system or a
        # custom font without the lists being mixed together.
        box = layout.box()
        box.label(text="Bundled Fonts:", icon='PREFERENCES')
        row = box.row(align=True)
        row.prop(scene, "persian_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        box.operator(
            "pt.seq_apply_persian_font", text="Apply Font", icon='FILE_FONT',
        ).source = 'BUNDLED'

        box = layout.box()
        box.label(text="System Fonts:", icon='FILEBROWSER')
        row = box.row(align=True)
        row.prop(scene, "system_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        row = box.row(align=True)
        row.operator(
            "pt.seq_apply_persian_font", text="Apply Font", icon='FILE_FONT',
        ).source = 'SYSTEM'
        row.operator("pt.scan_system_fonts", text="", icon='FILE_REFRESH')

        box = layout.box()
        box.label(text="Custom Fonts:", icon='FILE_FOLDER')
        row = box.row(align=True)
        row.prop(scene, "custom_font", text="Font")
        row.operator("view3d.refresh_persian_fonts", text="", icon='FILE_REFRESH')
        box.operator(
            "pt.seq_apply_persian_font", text="Apply Font", icon='FILE_FONT',
        ).source = 'CUSTOM'

        self._draw_appearance(context, layout, strip)


# PT_PersianStripLine must be registered before the CollectionProperty that
# uses it, so it leads the tuple and register() installs the Scene properties
# only after the whole tuple is in.
__classes__ = (
    PT_PersianStripLine,
    PT_UL_persian_strip_lines,
    PT_OT_SeqLineAdd,
    PT_OT_SeqLineRemove,
    PT_OT_SeqLineMove,
    PT_OT_SeqPastePersianText,
    PT_OT_SeqLoadPersianText,
    PT_OT_SeqApplyPersianText,
    PT_OT_SeqResetAppearance,
    PT_OT_SeqApplyPersianFont,
    PT_OT_SeqAddPersianStrip,
    PT_MT_text_style_presets,
    SEQUENCER_PT_persiantype,
)


def register():
    for cls in __classes__:
        bpy.utils.register_class(cls)

    bpy.types.Scene.persian_strip_lines = CollectionProperty(
        type=PT_PersianStripLine,
        name="Persian Text Lines",
        description=(
            "Persian/Arabic text in logical reading order, one entry per "
            "line. Apply it to shape it into the active text strip"
        ),
    )
    bpy.types.Scene.persian_strip_lines_index = IntProperty(
        name="Active Line",
        description="Index of the line selected in the list",
        default=0,
        min=0,
    )


def unregister():
    del bpy.types.Scene.persian_strip_lines_index
    del bpy.types.Scene.persian_strip_lines

    for cls in reversed(__classes__):
        bpy.utils.unregister_class(cls)
