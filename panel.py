import bpy
import os

FONT_FOLDER = os.path.join(os.path.dirname(__file__), "fonts")

class VIEW3D_OT_ToggleTextDirection(bpy.types.Operator):
    bl_idname = "view3d.toggle_text_direction"
    bl_label = "Toggle Text Direction"
    bl_description = "Toggle text direction between English and Persian"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object and context.active_object.type == 'FONT':
            text_obj = context.active_object
            
            if text_obj.data.align_x == 'LEFT':
                text_obj.data.align_x = 'RIGHT'
                self.report({'INFO'}, "Text direction: Right to Left (Persian)")
            else:
                text_obj.data.align_x = 'LEFT'
                self.report({'INFO'}, "Text direction: Left to Right (English)")
                
            text_obj.data.update_tag()
            context.view_layer.update()
            
            return {'FINISHED'}
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
            font_path = os.path.join(FONT_FOLDER, context.scene.persian_font)
            
            # Check if font file exists
            if os.path.exists(font_path):
                # Load and apply the font
                font = bpy.data.fonts.load(font_path)
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

class PersiantypePanel(bpy.types.Panel):
    bl_label = "Persian Text Panel"
    bl_idname = "VIEW3D_PT_persiantype"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Persian Text"

    def draw(self, context):
        layout = self.layout
        
        # Main Section
        box = layout.box()
        box.label(text="Persian Text", icon='FONT_DATA')
        
        # Enable Button
        row = box.row()
        row.operator("view3d.persian_text_mode", text="Enable Persian Text", icon='GREASEPENCIL')
        
        # Toggle Text Direction Button
        row = box.row()
        row.operator("view3d.toggle_text_direction", text="Toggle Text Direction", icon='ARROW_LEFTRIGHT')
        
        # Font Settings
        box = layout.box()
        box.label(text="Font Settings:", icon='PREFERENCES')
        
        # Font List
        row = box.row()
        row.prop(context.scene, "persian_font", text="Font")
        
        # Change Font Button
        row = box.row()
        row.operator("view3d.change_persian_font", text="Change Font", icon='FILE_FONT')

# Export all classes
__classes__ = [
    VIEW3D_OT_ToggleTextDirection,
    VIEW3D_OT_ChangePersianFont,
    PersiantypePanel
]
