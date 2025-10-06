# export.py
def write_animation_csv(context):
    # TODO: sample chassis + wheels and write CSV
    path = context.scene.sg_props.csv_path
    return 0, path

def write_keyframe_csv(context):
    # TODO: collect keyed transforms and write CSV
    path = context.scene.sg_props.other_export_path
    return 0, path
