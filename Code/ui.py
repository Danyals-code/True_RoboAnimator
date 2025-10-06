# ui.py
import bpy

class SG_PT_Panel(bpy.types.Panel):
    bl_idname = "SG_PT_TRUE_ROBOANIMATOR"
    bl_label = "True RoboAnimator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "True RoboAnimator"

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, "sg_props")

    def draw(self, context):
        P = context.scene.sg_props
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # --- Instructions ---
        _section_toggle(layout, P, "show_instructions", "Instructions")
        if P.show_instructions:
            col = layout.column(align=True)
            col.label(text="Workflow:")
            col.label(text="1) Select objects and set wheel params.")
            col.label(text="2) Validate → Autocorrect.")
            col.label(text="3) Build Cache → Attach Drivers → Bake.")
            col.label(text="4) Export CSV or Keyframes.")

        # --- Selection / Calibration ---
        _section_toggle(layout, P, "show_selection", "Object Selection")
        if P.show_selection:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "chassis")
            c.prop(P, "left_collection")
            c.prop(P, "right_collection")
            r = c.row(align=True)
            r.prop(P, "swap_lr")
            r.prop(P, "wheel_forward_invert")
            c.separator()
            c.prop(P, "wheel_axis")
            c.prop(P, "rotation_mode")

        _section_toggle(layout, P, "show_calibration", "Geometry / Wheels")
        if P.show_calibration:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "track_width")
            c.prop(P, "tire_spacing")
            r = c.row(align=True)
            r.prop(P, "auto_radius")
            sub = r.row(align=True)
            sub.enabled = not P.auto_radius
            sub.prop(P, "wheel_radius")

        # --- Feasibility / Autocorrect / Timing ---
        _section_toggle(layout, P, "show_feasibility", "Feasibility + Autocorrect")
        if P.show_feasibility:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "body_forward_axis")
            c.prop(P, "side_tol")
            c.separator()
            c.prop(P, "autocorrect_mode")
            row = c.row(align=True)
            row.enabled = (P.autocorrect_mode == 'SEASE')
            row.prop(P, "bezier_tangent_scale")
            row = c.row(align=True)
            row.enabled = (P.autocorrect_mode == 'LINEAR')
            row.prop(P, "linear_rotation_fraction")
            c.separator()
            c.prop(P, "speed_profile")
            r = c.row(align=True); r.enabled = (P.speed_profile == 'CONSTANT'); r.prop(P, "constant_ramp_frames")
            r = c.row(align=True); r.enabled = (P.speed_profile == 'GLOBAL_EASE'); r.prop(P, "timeline_ease_frames")
            r = c.row(align=True); r.enabled = (P.speed_profile == 'PER_KEY_EASE'); r.prop(P, "segment_ease_frames")
            c.separator()
            r = c.row(align=True)
            r.operator("segway.validate_motion", icon='CHECKMARK')
            if P.autocorrect_mode == 'SEASE':
                r.operator("segway.autocorrect_sease", text="Autocorrect", icon='MOD_CURVE')
            elif P.autocorrect_mode == 'LINEAR':
                r.operator("segway.autocorrect_linear", text="Autocorrect", icon='MOD_SIMPLEDEFORM')
            else:
                r.operator("segway.autocorrect_bake", text="Autocorrect", icon='MODIFIER')
            c.operator("segway.revert_autocorrect", icon='BACK')

        # --- RPM / Drivers / Bake ---
        _section_toggle(layout, P, "show_rpm_calc", "RPM / Drivers / Bake")
        if P.show_rpm_calc:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "max_rpm")
            c.prop(P, "max_ang_accel_rpm_s")
            c.separator()
            r = c.row(align=True)
            r.operator("segway.build_cache", icon='FILE_CACHE')
            r.operator("segway.attach_drivers", icon='DRIVER')
            r.operator("segway.bake_wheels", icon='REC')
            c.operator("segway.clear", icon='TRASH')

        # --- CSV Animation Export ---
        _section_toggle(layout, P, "show_anim_export", "Animation CSV Export")
        if P.show_anim_export:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "csv_path")
            c.prop(P, "sample_mode")
            row = c.row(align=True); row.enabled = (P.sample_mode == 'FIXED'); row.prop(P, "fixed_rate")
            c.prop(P, "length_unit")
            c.prop(P, "angle_unit")
            c.prop(P, "angrate_unit")
            c.separator()
            c.operator("segway.export_csv", icon='EXPORT')

        # --- Keyframe Export (Engineering) ---
        _section_toggle(layout, P, "show_csv_export", "Keyframe/Engineering Export")
        if P.show_csv_export:
            box = layout.box()
            c = box.column(align=True)
            c.prop(P, "other_export_path")
            c.prop(P, "other_export_format")
            c.prop(P, "other_angle_unit")
            c.separator()
            c.operator("segway.export_keyframes", icon='EXPORT')


def _section_toggle(layout, props, attr, title):
    row = layout.row(align=True)
    icon = 'TRIA_DOWN' if getattr(props, attr) else 'TRIA_RIGHT'
    row.prop(props, attr, text=title, icon=icon, emboss=False)
