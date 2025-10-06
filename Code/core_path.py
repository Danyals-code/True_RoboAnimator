# core_path.py
# Path feasibility, autocorrect scaffolds, and keyframe backup/restore.
import bpy
from math import sin, cos, pi

_BACKUP_KEY = "SG_BACKUP"

# ---------------------- small helpers ----------------------
def _axis_unit(axis_char: str):
    ax = axis_char.upper()
    if ax == 'X': return (1.0, 0.0, 0.0)
    if ax == 'Y': return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)

def _col_for_side(P, side):
    # Mirrors your L/R + swap logic.
    return (P.left_collection if side == 'L' else P.right_collection) if not P.swap_lr else \
           (P.right_collection if side == 'L' else P.left_collection)

def _iter_side(P, side):
    col = _col_for_side(P, side)
    if not col:
        return []
    return [o for o in col.objects if o.type in {'MESH', 'EMPTY'}]

def _body_basis_from_yaw(theta, forward_axis):
    # Matches your forward-axis mapping to unit forward and lateral. :contentReference[oaicite:2]{index=2}
    c = cos(theta); s = sin(theta)
    if   forward_axis == '+Y': fwd = (-s,  c)
    elif forward_axis == '-Y': fwd = ( s, -c)
    elif forward_axis == '-X': fwd = (-c, -s)
    else:                      fwd = ( c,  s)  # +X
    lat = (-fwd[1], fwd[0])
    return fwd, lat

# ---------------------- feasibility (no sideways slip per frame) ----------------------
def analyze_motion(context):
    """
    Check per-frame lateral slip of chassis vs tolerance.
    Returns dict: {'violations': int, 'violation_frames': [..], 'side_tol': float, 'fps': float}
    """
    scn = context.scene
    P = scn.sg_props
    ch = P.chassis
    if not ch:
        raise RuntimeError("Assign the Chassis.")
    if P.track_width <= 0:
        raise RuntimeError("Track width must be > 0.")
    if scn.frame_end <= scn.frame_start:
        raise RuntimeError("Scene frame range invalid.")

    fps = scn.render.fps / scn.render.fps_base
    dt = 1.0 / float(fps)
    f0, f1 = scn.frame_start, scn.frame_end
    deps = context.evaluated_depsgraph_get()

    # sample first frame
    scn.frame_set(f0); deps.update()
    mw = ch.matrix_world
    prev_loc = mw.translation.copy()
    prev_yaw = mw.to_euler('XYZ').z

    side_tol = float(P.side_tol)
    v_frames = []
    violations = 0

    for f in range(f0 + 1, f1 + 1):
        scn.frame_set(f); deps.update()
        mw = ch.matrix_world
        loc = mw.translation
        yaw = mw.to_euler('XYZ').z

        # body basis at previous frame
        _, lat = _body_basis_from_yaw(prev_yaw, P.body_forward_axis)

        # lateral displacement per second
        dx = float(loc.x - prev_loc.x)
        dy = float(loc.y - prev_loc.y)
        lat_v = (dx * lat[0] + dy * lat[1]) / dt

        if abs(lat_v) > side_tol:
            violations += 1
            v_frames.append(f)

        prev_loc = loc.copy()
        prev_yaw = yaw

    return {
        "violations": violations,
        "violation_frames": v_frames,
        "side_tol": side_tol,
        "fps": float(fps),
        "f0": int(f0),
        "f1": int(f1),
    }

# ---------------------- keyframe backup / restore ----------------------
def _ensure_xyz_euler(obj):
    try:
        obj.rotation_mode = 'XYZ'
    except Exception:
        pass

def backup_chassis_keys(context):
    P = context.scene.sg_props
    ch = P.chassis
    if not ch:
        return False
    key = f"{_BACKUP_KEY}_{context.scene.name}_{ch.name}"
    data = {}
    ad = ch.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path in ("location", "rotation_euler"):
                rows = [(int(round(kp.co[0])), float(kp.co[1])) for kp in fc.keyframe_points]
                data[f"{fc.data_path}[{fc.array_index}]"] = rows
    # store in a Text datablock for easy undo/redo parity
    txt = bpy.data.texts.get(key) or bpy.data.texts.new(key)
    txt.clear()
    import json
    txt.write(json.dumps(data))
    return True

def restore_chassis_backup(context):
    # Mirrors your _restore_chassis_keys flow. :contentReference[oaicite:3]{index=3}
    P = context.scene.sg_props
    ch = P.chassis
    if not ch:
        return False
    key = f"{_BACKUP_KEY}_{context.scene.name}_{ch.name}"
    txt = bpy.data.texts.get(key)
    if not txt or len(txt.as_string()) == 0:
        return False
    import json
    try:
        data = json.loads(txt.as_string())
    except Exception:
        return False

    if not ch.animation_data:
        ch.animation_data_create()
    if not ch.animation_data.action:
        ch.animation_data.action = bpy.data.actions.new(name="ChassisAction")

    ad = ch.animation_data
    if ad and ad.action:
        # remove existing location/euler fcurves
        for fc in list(ad.action.fcurves):
            if fc.data_path in ("location", "rotation_euler"):
                try:
                    ad.action.fcurves.remove(fc)
                except Exception:
                    pass

    _ensure_xyz_euler(ch)
    for key, rows in data.items():
        if key.startswith("location["):
            path = "location"; idx = int(key.split("[")[1][0])
        elif key.startswith("rotation_euler["):
            path = "rotation_euler"; idx = int(key.split("[")[1][0])
        else:
            continue
        fc = ch.animation_data.action.fcurves.new(data_path=path, index=idx)
        for fr, val in rows:
            fc.keyframe_points.insert(frame=int(fr), value=float(val), options={'FAST'})
    txt.clear()
    return True

# ---------------------- autocorrect + bake scaffolds ----------------------
def build_s_ease_curve_and_bake(context):
    """
    Autocorrect using smooth S-Ease curves then bake to keyframes.
    Returns number of frames baked.
    TODO: Move your V8 S-Ease generator here and call backup_chassis_keys(context) before edits.
    """
    # placeholder: just validate and report zero frames if violations exist
    a = analyze_motion(context)
    if a["violations"] > 0:
        raise RuntimeError(f"Violations present: {a['violations']} (first at frame {a['violation_frames'][0]})")
    # If no violations, nothing to fix. Return current frame span.
    return (a["f1"] - a["f0"] + 1)

def build_linear_path_and_bake(context):
    """
    Autocorrect using rotate-move-rotate scheme then bake.
    Returns number of frames baked.
    TODO: Move your V8 Linear autocorrect here and call backup_chassis_keys(context) before edits.
    """
    a = analyze_motion(context)
    if a["violations"] > 0:
        # In real implementation you will generate linear segments that meet the constraint,
        # overwrite chassis keyframes, then return baked frame count.
        pass
    return (a["f1"] - a["f0"] + 1)
