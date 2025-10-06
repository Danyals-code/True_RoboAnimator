# __init__.py  — True RoboAnimator (modularized, V8-compatible IDs)

bl_info = {
    "name": "True RoboAnimator",
    "author": "Danyal S.",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > N-Panel > True RoboAnimator",
    "description": "Engineering-accurate animation toolkit for differential-drive robots.",
    "category": "Animation",
}

import bpy

# --- Local imports (match your split) ---
from .props import SG_Props                # PropertyGroup (unchanged naming)
from .ui import SG_PT_Panel                # Main panel with foldouts

# Code path geometry + feasibility/autocorrect
from .core_path import (
    analyze_motion,
    build_s_ease_curve_and_bake,
    build_linear_path_and_bake,
    restore_chassis_backup,               # exposes backup->restore used by Revert
)

# Code RPM + drivers + baking
from .core_rpm import (
    build_cache,
    attach_drivers,
    bake_wheels,
    clear_wheels,
    register_driver_functions,            # installs sg_theta/sg_quat_* in driver namespace
    driver_key_available,                 # returns True if cache present
)

# File export (animation CSV + “engineering” CSV + keyframe CSV/JSON)
from .export import (
    write_animation_csv,                  # was SG_OT_ExportCSV
    write_keyframe_csv,                   # was SG_OT_ExportKeyframes
)

# ---------------------- Operators (same IDs/labels as V8) ----------------------
class SG_OT_ValidateMotion(bpy.types.Operator):
    bl_idname = "segway.validate_motion"
    bl_label  = "Validate Motion"
    bl_description = "Check current chassis animation for nonholonomic feasibility (mid-step heading)"
    def execute(self, context):
        try:
            a = analyze_motion(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        if a.get('violations', 0) > 0:
            frames = a.get('violation_frames', [])
            head = ", ".join(str(f) for f in frames[:12]) + (" …" if len(frames)>12 else "")
            self.report({'ERROR'},
                        f"This won't work: {a['violations']} step(s) exceed sideways tolerance > {a['side_tol']} (frames {head}).")
            return {'CANCELLED'}
        self.report({'INFO'}, "Motion is feasible (no slip violations).")
        return {'FINISHED'}


class SG_OT_AutocorrectBake(bpy.types.Operator):
    bl_idname = "segway.autocorrect_bake"
    bl_label  = "Autocorrect & Bake"
    bl_description = "Bake using the selected Autocorrect Mode (S-Ease or Linear) with the chosen Speed Profile"
    def execute(self, context):
        P = context.scene.sg_props
        try:
            if   P.autocorrect_mode == 'SEASE':  n = build_s_ease_curve_and_bake(context)
            elif P.autocorrect_mode == 'LINEAR': n = build_linear_path_and_bake(context)
            else:
                self.report({'ERROR'}, "Set Autocorrect Mode to S-Ease or Linear."); return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Autocorrect failed: {e}"); return {'CANCELLED'}
        self.report({'INFO'}, f"Autocorrect baked {n} frames. Re-run Validate Motion.")
        return {'FINISHED'}


class SG_OT_AutocorrectSEase(bpy.types.Operator):
    bl_idname = "segway.autocorrect_sease"
    bl_label  = "Autocorrect & Bake (Smooth S-Ease)"
    def execute(self, context):
        P = context.scene.sg_props
        if P.autocorrect_mode != 'SEASE':
            self.report({'ERROR'}, "Set Autocorrect Mode to 'Smooth Curve (S-Ease)'."); return {'CANCELLED'}
        try:
            n = build_s_ease_curve_and_bake(context)
        except Exception as e:
            self.report({'ERROR'}, f"Autocorrect failed: {e}"); return {'CANCELLED'}
        self.report({'INFO'}, f"Autocorrect baked {n} frames. Re-run Validate Motion.")
        return {'FINISHED'}


class SG_OT_AutocorrectLinear(bpy.types.Operator):
    bl_idname = "segway.autocorrect_linear"
    bl_label  = "Autocorrect & Bake (Linear: Rotate–Move–Rotate)"
    def execute(self, context):
        P = context.scene.sg_props
        if P.autocorrect_mode != 'LINEAR':
            self.report({'ERROR'}, "Set Autocorrect Mode to 'Linear (Rotate–Move–Rotate)'."); return {'CANCELLED'}
        try:
            n = build_linear_path_and_bake(context)
        except Exception as e:
            self.report({'ERROR'}, f"Autocorrect failed: {e}"); return {'CANCELLED'}
        self.report({'INFO'}, f"Linear autocorrect baked {n} frames. Re-run Validate Motion.")
        return {'FINISHED'}


class SG_OT_RevertAutocorrect(bpy.types.Operator):
    bl_idname = "segway.revert_autocorrect"
    bl_label  = "Revert Autocorrect"
    def execute(self, context):
        try:
            ok = restore_chassis_backup(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        if not ok:
            self.report({'ERROR'}, "No backup found to restore."); return {'CANCELLED'}
        self.report({'INFO'}, "Original chassis keyframes restored.")
        return {'FINISHED'}


class SG_OT_AttachDrivers(bpy.types.Operator):
    bl_idname = "segway.attach_drivers"
    bl_label  = "Attach Drivers"
    def execute(self, context):
        if not driver_key_available():
            self.report({'ERROR'}, "Build Cache first (and pass validation)."); return {'CANCELLED'}
        try:
            attach_drivers(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        self.report({'INFO'}, "Drivers attached to wheel objects.")
        return {'FINISHED'}


class SG_OT_BuildCache(bpy.types.Operator):
    bl_idname = "segway.build_cache"
    bl_label  = "Build Cache"
    def execute(self, context):
        try:
            d = build_cache(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        self.report({'INFO'}, f"OK | r={d['radius']:.4f} m | track={d['track']:.4f} m | maxRPM L/R {d['max_rpm_L']:.1f}/{d['max_rpm_R']:.1f}")
        return {'FINISHED'}


class SG_OT_Bake(bpy.types.Operator):
    bl_idname = "segway.bake_wheels"
    bl_label  = "Bake Wheels"
    def execute(self, context):
        if not driver_key_available():
            self.report({'ERROR'}, "Build Cache first (and pass validation)."); return {'CANCELLED'}
        try:
            bake_wheels(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        self.report({'INFO'}, "Baked wheel rotations to keyframes.")
        return {'FINISHED'}


class SG_OT_Clear(bpy.types.Operator):
    bl_idname = "segway.clear"
    bl_label  = "Clear Drivers/Keyframes"
    bl_description = "Remove wheel rotation drivers AND their rotation keyframes (Euler & Quaternion) on all wheel objects."
    def execute(self, context):
        try:
            removed_any = clear_wheels(context)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        self.report({'INFO'} if removed_any else {'WARNING'},
                    "Cleared drivers & rotation keyframes" if removed_any else "Nothing to clear on wheel objects.")
        return {'FINISHED'}


class SG_OT_ExportCSV(bpy.types.Operator):
    bl_idname = "segway.export_csv"
    bl_label  = "Export CSV"
    bl_description = "Export t, x, y, yaw, thetaR/L, rateR/L using chosen sampling and units"
    def execute(self, context):
        try:
            n, path = write_animation_csv(context)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write CSV: {e}"); return {'CANCELLED'}
        self.report({'INFO'}, f"Wrote {path} ({n} samples)")
        return {'FINISHED'}


class SG_OT_ExportKeyframes(bpy.types.Operator):
    bl_idname = "segway.export_keyframes"
    bl_label  = "Export Keyframes"
    def execute(self, context):
        try:
            n, path = write_keyframe_csv(context)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write: {e}"); return {'CANCELLED'}
        self.report({'INFO'}, f"Keyframes exported to {path} ({n} rows)")
        return {'FINISHED'}


# ---------------------- Registration ----------------------
CLASSES = (
    SG_Props,
    SG_PT_Panel,
    SG_OT_ValidateMotion,
    SG_OT_AutocorrectBake,
    SG_OT_AutocorrectSEase,
    SG_OT_AutocorrectLinear,
    SG_OT_RevertAutocorrect,
    SG_OT_AttachDrivers,
    SG_OT_BuildCache,
    SG_OT_Bake,
    SG_OT_Clear,
    SG_OT_ExportCSV,
    SG_OT_ExportKeyframes,
)

def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.sg_props = bpy.props.PointerProperty(type=SG_Props)
    # ensure driver functions exist for expressions
    register_driver_functions()

def unregister():
    del bpy.types.Scene.sg_props
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
