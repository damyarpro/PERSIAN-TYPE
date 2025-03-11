bl_info = {
    "name": "Persiantype",
    "author": "DAMYAR",
    "version": (1, 0),
    "blender": (2, 80, 0),
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

def get_font_items(self, context):
    items = []
    font_folder = os.path.join(os.path.dirname(__file__), "fonts")
    if os.path.exists(font_folder):
        for font_file in os.listdir(font_folder):
            if font_file.endswith((".ttf", ".otf")):
                font_name = os.path.splitext(font_file)[0]
                items.append((font_file, font_name, ""))
    return items

def register():
    # Register font property
    bpy.types.Scene.persian_font = bpy.props.EnumProperty(
        name="Persian Font",
        items=get_font_items
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

if __name__ == "__main__":
    register()

