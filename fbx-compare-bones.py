"""
Blender script to compare two FBX armatures and their bones
"""

USAGE = "Usage: blender --background --python fbx-compare-bones.py -- <fbx_file> <fbx_file>"

import bpy
import os
import sys
import math

from mathutils import Quaternion


def parse_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 2:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        fbx_a = argv[0]
        if not os.path.exists(fbx_a):
            raise FileNotFoundError(f"Input file does not exist: {fbx_a}")

        fbx_b = argv[1]
        if not os.path.exists(fbx_b):
            raise FileNotFoundError(f"Input file does not exist: {fbx_b}")

    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)

    return fbx_a, fbx_b


def main():
    fbx_a, fbx_b = parse_args()

    # --- Clear scene --- #
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # --- Import character --- #
    bpy.ops.import_scene.fbx(filepath=fbx_a, use_anim=False)
    fbx_a_arm = next(o for o in bpy.context.selected_objects if o.type == 'ARMATURE')

    # --- Import animation --- #
    bpy.ops.import_scene.fbx(filepath=fbx_b, use_anim=True)
    fbx_b_arm = next(o for o in bpy.context.selected_objects if o.type == 'ARMATURE')

    # --- Compare bone names --- #
    bones_fbx_a = {b.name: b for b in fbx_a_arm.data.bones}
    bones_fbx_b = {b.name: b for b in fbx_b_arm.data.bones}

    missing_in_fbx_a = set(bones_fbx_b.keys()) - set(bones_fbx_a.keys())
    missing_in_fbx_b = set(bones_fbx_a.keys()) - set(bones_fbx_b.keys())

    print("\n=== Bone Name Comparison ===")
    print("Bones present in FBX B but missing in FBX A:")
    if missing_in_fbx_a:
        for b in sorted(missing_in_fbx_a):
            print("  ", b)
    else:
        print("None missing")

    print("\nBones present in FBX A but missing in FBX B:")
    if missing_in_fbx_b:
        for b in sorted(missing_in_fbx_b):
            print("  ", b)
    else:
        print("None missing")

    if not missing_in_fbx_b and not missing_in_fbx_a:
        print("\n✅ All bones match by name between the FBX files.")

    # --- Rotation differences for matching bones --- #
    THRESHOLD_DEG = 0.01  # degrees
    common_bones = set(bones_fbx_a.keys()) & set(bones_fbx_b.keys())
    printed_any = False

    if common_bones:
        print("\n=== Rotation Differences (frame 0) ===")
        for name in sorted(common_bones):
            b_char = bones_fbx_a[name]
            b_anim = bones_fbx_b[name]

            q_char = b_char.matrix_local.to_quaternion()
            q_anim = b_anim.matrix_local.to_quaternion()
            delta_q = q_anim.rotation_difference(q_char)
            delta_euler = delta_q.to_euler('XYZ')

            dx, dy, dz = map(lambda r: math.degrees(r), (delta_euler.x, delta_euler.y, delta_euler.z))
            if abs(dx) < THRESHOLD_DEG and abs(dy) < THRESHOLD_DEG and abs(dz) < THRESHOLD_DEG:
                continue  # skip nearly identical bones

            printed_any = True
            print(f"  {name}: ΔRotation = ({dx:.2f}, {dy:.2f}, {dz:.2f})")

        if not printed_any:
            print("✅ No significant rotation differences found.")

        # print("Customer user properties:")
        # for obj in bpy.context.scene.objects:
        #     if obj.keys():
        #         print(f"\nObject: {obj.name}")
        #         for key in obj.keys():
        #             if key not in "_RNA_UI":
        #                 print(f"  User property: {key} = {obj[key]}")


if __name__ == "__main__":
    main()
