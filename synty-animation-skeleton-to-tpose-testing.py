import bpy
import sys
import os

def parse_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]
        if len(argv) < 3:
            print("Usage: blender --background --python synty-animation-to-skeletion.py -- <tpose_fbx> <animation_fbx> <output_fbx>")
            sys.exit(1)
        return argv[0], argv[1], argv[2]
    except ValueError:
        print("ERROR: No arguments found after '--'")
        sys.exit(1)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def import_fbx(filepath):
    bpy.ops.import_scene.fbx(filepath=filepath)
    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            return obj
    return None

def get_animation_range(armature):
    if armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        return int(action.frame_range[0]), int(action.frame_range[1])
    return 1, 250

def retarget_preserve_current(source_arm, target_arm, frame_start, frame_end):
    """
    Retarget source animation onto target skeleton.
    - Only maps bones that exist in both skeletons.
    - Keeps frame 1 exactly at source pose.
    - Applies animation relative to target rest pose.
    """
    bpy.context.view_layer.objects.active = target_arm
    bpy.ops.object.mode_set(mode='POSE')

    # Only bones existing in both source and target
    common_bones = [bn.name for bn in source_arm.data.bones if bn.name in target_arm.data.bones]
    print(f"Mapping {len(common_bones)} bones")

    # Precompute per-bone delta at frame 1
    bpy.context.scene.frame_set(frame_start)
    deltas = {}
    for bn in common_bones:
        src_pose_b = source_arm.pose.bones[bn]
        src_rest_world = source_arm.matrix_world @ source_arm.data.bones[bn].matrix_local
        src_pose_world = source_arm.matrix_world @ src_pose_b.matrix
        deltas[bn] = src_rest_world.inverted() @ src_pose_world  # pose relative to source rest

    # Apply animation frame by frame
    for frame in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame)

        for bn in common_bones:
            src_pose_b = source_arm.pose.bones[bn]
            tgt_pose_b = target_arm.pose.bones[bn]
            tgt_rest_world = target_arm.matrix_world @ target_arm.data.bones[bn].matrix_local

            # Desired world = target rest * delta from source
            src_pose_world = source_arm.matrix_world @ src_pose_b.matrix
            delta = deltas[bn]  # delta computed at frame 1
            desired_world = tgt_rest_world @ (source_arm.data.bones[bn].matrix_local.inverted() @ src_pose_world)

            # Convert world -> target armature-local
            tgt_pose_b.matrix = target_arm.matrix_world.inverted() @ desired_world

            # Keyframe rotation, location, scale
            tgt_pose_b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            tgt_pose_b.keyframe_insert(data_path="location", frame=frame)
            tgt_pose_b.keyframe_insert(data_path="scale", frame=frame)

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Retarget complete: frames {frame_start}-{frame_end}")


def main():
    tpose_fbx, animation_fbx, output_fbx = parse_args()
    print("Clearing scene...")
    clear_scene()

    print(f"Importing T-pose: {tpose_fbx}")
    target_arm = import_fbx(tpose_fbx)
    if not target_arm:
        print("ERROR: Could not find T-pose armature"); sys.exit(1)
    target_arm.name = "Target_TPose"

    print(f"Importing animation: {animation_fbx}")
    source_arm = import_fbx(animation_fbx)
    if not source_arm:
        print("ERROR: Could not find animation armature"); sys.exit(1)
    source_arm.name = "Source_Animation"

    frame_start, frame_end = get_animation_range(source_arm)
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end
    print(f"Animation frames: {frame_start} to {frame_end}")

    print("Retargeting animation while preserving frame 1...")
    retarget_preserve_current(source_arm, target_arm, frame_start, frame_end)

    print("Removing source armature...")
    bpy.data.objects.remove(source_arm, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    target_arm.select_set(True)
    bpy.context.view_layer.objects.active = target_arm

    print(f"Exporting retargeted animation to: {output_fbx}")
    os.makedirs(os.path.dirname(output_fbx) if os.path.dirname(output_fbx) else ".", exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=True,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False
    )

    print("Retargeting complete.")

if __name__ == "__main__":
    main()
