import bpy
import sys
import os
import importlib

USAGE = "Usage: blender --background --python fbx-info.py -- <fbx_file>"


def parse_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 1:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        fbx_file = argv[0]

        if not os.path.exists(fbx_file):
            print(f"ERROR: FBX not found: {fbx_file}")
            sys.exit(1)

        return fbx_file
    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)


# NOTE: these options will change how the import works!
def import_fbx(fbx):
    bpy.ops.import_scene.fbx(
        filepath=fbx,
        use_anim=True,
        ignore_leaf_bones=False,
        force_connect_children=False,
        automatic_bone_orientation=False,
        # automatic_bone_orientation=True,
    )


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def debug_skeleton(armature):
    print("\n" + "=" * 60)
    print(f"ARMATURE: {armature.name}")
    print("=" * 60)

    # Check if there's animation data
    has_animation = armature.animation_data and armature.animation_data.action
    if has_animation:
        action = armature.animation_data.action
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        print(f"\nAnimation: {action.name}")
        print(f"Frame range: {frame_start} to {frame_end}")
    else:
        print("\nNo animation data found")
        frame_start = 1
        frame_end = 1

    # Print bone count
    print(f"\nTotal bones: {len(armature.pose.bones)}")

    # Sample a few key bones to check
    sample_bones = ['Hips', 'Spine', 'LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm', 'Head']
    found_bones = [b for b in sample_bones if armature.pose.bones.get(b)]

    if not found_bones:
        # If standard names not found, just use first few bones
        found_bones = [b.name for b in list(armature.pose.bones)[:5]]
        print(f"\nStandard bone names not found, sampling first 5 bones instead")

    print(f"\nAnalyzing bones: {', '.join(found_bones)}")

    # Set to frame 1 if animation exists
    if has_animation:
        bpy.context.scene.frame_set(frame_start)

    print("\n" + "-" * 60)
    print("EDIT MODE (Rest Pose) - Bone World Positions:")
    print("-" * 60)

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_name in found_bones:
        edit_bone = armature.data.edit_bones.get(bone_name)
        if edit_bone:
            head = edit_bone.head
            tail = edit_bone.tail
            print(f"\n{bone_name}:")
            print(f"  Head: ({head.x:.4f}, {head.y:.4f}, {head.z:.4f})")
            print(f"  Tail: ({tail.x:.4f}, {tail.y:.4f}, {tail.z:.4f})")
            print(f"  Roll: {edit_bone.roll:.4f}")

    bpy.ops.object.mode_set(mode='OBJECT')

    print("\n" + "-" * 60)
    print(f"POSE MODE - Frame {frame_start} Local Rotations:")
    print("-" * 60)

    bpy.ops.object.mode_set(mode='POSE')

    if has_animation:
        bpy.context.scene.frame_set(frame_start)

    for bone_name in found_bones:
        pose_bone = armature.pose.bones.get(bone_name)
        if pose_bone:
            print(f"\n{bone_name}:")
            print(f"  Rotation mode: {pose_bone.rotation_mode}")

            if pose_bone.rotation_mode == 'QUATERNION':
                rot = pose_bone.rotation_quaternion
                print(f"  Quaternion: ({rot.w:.4f}, {rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})")
            else:
                rot = pose_bone.rotation_euler
                print(f"  Euler: ({rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})")

            # Also show the matrix
            mat = pose_bone.matrix
            loc = mat.to_translation()
            quat = mat.to_quaternion()
            print(f"  Matrix location: ({loc.x:.4f}, {loc.y:.4f}, {loc.z:.4f})")
            print(f"  Matrix quaternion: ({quat.w:.4f}, {quat.x:.4f}, {quat.y:.4f}, {quat.z:.4f})")

    # If animation exists, also check a middle frame
    if has_animation and frame_end > frame_start + 5:
        mid_frame = (frame_start + frame_end) // 2
        print("\n" + "-" * 60)
        print(f"POSE MODE - Frame {mid_frame} Local Rotations (mid animation):")
        print("-" * 60)

        bpy.context.scene.frame_set(mid_frame)

        for bone_name in found_bones:
            pose_bone = armature.pose.bones.get(bone_name)
            if pose_bone:
                print(f"\n{bone_name}:")
                if pose_bone.rotation_mode == 'QUATERNION':
                    rot = pose_bone.rotation_quaternion
                    print(f"  Quaternion: ({rot.w:.4f}, {rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})")
                else:
                    rot = pose_bone.rotation_euler
                    print(f"  Euler: ({rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})")

    bpy.ops.object.mode_set(mode='OBJECT')
    print("\n" + "=" * 60 + "\n")


def debug_mesh(mesh):
    for mat in mesh.data.materials:
        if not mat:
            print(f"  No Materials found, skipping")
            continue

        print(f"  Material: {mat.name}")

        node_tree = getattr(mat, "node_tree", None)
        if not node_tree:
            print("  No Node Tree found, skipping")
            continue

        for node in node_tree.nodes:
            print(f"  Processing node {node.name}")
            if getattr(node, "image", None) is None:
                print(f"  No image path for {node.type}, skipping...")
                continue

            img_path = node.image.filepath
            print(f"  Image Path: {img_path}")

            if os.path.exists(os.path.abspath(bpy.path.abspath(img_path))):
                print("✅ Found")
            else:
                print("❌ Missing")


def main():
    fbx_file = parse_args()

    clear_scene()

    print(f"Loading: {fbx_file}\n")

    import_fbx(fbx_file)

    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            print(f"Armature Data for {obj.name}:")
            debug_skeleton(obj)
        elif obj.type == 'MESH':
            print(f"Mesh Data for {obj.name}:")
            debug_mesh(obj)
        else:
            print(f"Object Type: {obj.type}")
            print("Skipping this object...")


if __name__ == "__main__":
    main()
