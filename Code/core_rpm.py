# core_rpm.py
import bpy

_DRIVER_KEY = "roboanim_cache"

def register_driver_functions():
    # install placeholders into driver namespace if you use scripted expressions later
    ns = bpy.app.driver_namespace
    ns.setdefault("sg_theta", lambda side, frame: 0.0)
    ns.setdefault("sg_quat_comp_obj", lambda side, frame, comp, axis, rw, rx, ry, rz: (1.0,0.0,0.0,0.0)[comp])

def driver_key_available():
    return _DRIVER_KEY in bpy.app.driver_namespace

def build_cache(context):
    # TODO: compute and stash arrays (thetaL, thetaR, etc.)
    bpy.app.driver_namespace[_DRIVER_KEY] = {
        "f0": context.scene.frame_start,
        "fps": context.scene.render.fps / context.scene.render.fps_base,
        "thetaL": [0.0]*(context.scene.frame_end-context.scene.frame_start+1),
        "thetaR": [0.0]*(context.scene.frame_end-context.scene.frame_start+1),
        "max_rpm_L": 0.0, "max_rpm_R": 0.0,
        "radius": getattr(context.scene.sg_props, "wheel_radius", 0.0),
        "track":  getattr(context.scene.sg_props, "track_width", 0.0),
    }
    return bpy.app.driver_namespace[_DRIVER_KEY]

def attach_drivers(context):
    # TODO: wire real scripted drivers
    return True

def bake_wheels(context):
    # TODO: write rotations as keyframes
    return True

def clear_wheels(context):
    # TODO: remove drivers + rotation keyframes; return bool if anything removed
    return False
