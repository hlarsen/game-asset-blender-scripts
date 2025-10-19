"""
Script to add Mixamo animations onto a Mixamo character

TODO:
    - General Review/Cleanup
    - Don't use collections
"""

import bpy
import glob
import os
import sys

import math
from mathutils import Vector, Quaternion, Matrix

USAGE = "Usage: blender --background --python mixamo-add-animations-to-character.py -- <input_dir> <output_dir>"


def process_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 3:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        characters_path = argv[0]
        if not os.path.exists(characters_path):
            raise FileNotFoundError(f"Characters path does not exist: {characters_path}")

        animations_path = argv[1]
        if not os.path.exists(animations_path):
            raise FileNotFoundError(f"Animations path does not exist: {animations_path}")

        output_path = argv[2]
        if not os.path.isdir(output_path):
            os.mkdir(output_path)

    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)

    return characters_path, animations_path, output_path


def find_root_objects(objects):
    return [obj for obj in objects if obj.parent is None]


def bones_match(char_arm, anim_arm):
    bones_char = {b.name for b in char_arm.data.bones}
    bones_anim = {b.name for b in anim_arm.data.bones}

    # if we are missing animation bones in the character it will not work properly
    missing_in_anim = bones_anim - bones_char
    if missing_in_anim:
        print(f"Bones in anim_arm but not in char_arm: {missing_in_anim}")
        # raise ValueError(f"Bones in anim_arm but not in char_arm: {missing_in_anim}")

    # if we are missing character bones in the animation it _may_ not be too bad
    missing_in_char = bones_char - bones_anim
    if missing_in_char:
        print(f"Bones in char_arm but not in anim_arm: {missing_in_char}")
        # raise ValueError(f"Bones in char_arm but not in anim_arm: {missing_in_char}")

    return bones_char == bones_anim


def get_character(fbx_file):
    """Import a single character FBX file"""
    collection_name = "characters"
    character_collection = bpy.data.collections.get(collection_name)
    if not character_collection:
        character_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(character_collection)

    pre_import_objects = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(
        filepath=fbx_file,
        use_anim=False,
        ignore_leaf_bones=False,
        force_connect_children=False,
        automatic_bone_orientation=True,
    )

    imported_objects = set(bpy.data.objects) - pre_import_objects
    character_armature = None

    for obj in imported_objects:
        print(f"Importing object name: {obj.name} of type {obj.type} with parent {obj.parent} from file {fbx_file}")

        obj["source_path"] = fbx_file
        obj["source_file"] = os.path.basename(fbx_file)
        obj["is_root"] = False
        if obj.parent is None:
            obj["is_root"] = True

        # Track the armature
        if obj.type == 'ARMATURE':
            character_armature = obj

        # move to collection
        for col in obj.users_collection:
            col.objects.unlink(obj)
        character_collection.objects.link(obj)

        if not len(find_root_objects(imported_objects)) == 1:
            raise ValueError(f"Not a single root object: {find_root_objects(imported_objects)}")

    # Rename the character armature to "Armature"
    if character_armature:
        print(f"Renaming armature from '{character_armature.name}' to 'Armature'")
        character_armature.name = "Armature"

    print(f"Imported {len(imported_objects)} objects from {os.path.basename(fbx_file)}")
    return character_collection


def get_animations(fbx_path):
    if os.path.isdir(fbx_path):
        # Recursively find all .fbx files
        fbx_files = glob.glob(os.path.join(fbx_path, "**", "*.fbx"), recursive=True)
    else:
        fbx_files = [fbx_path]

    if not fbx_files:
        raise FileNotFoundError(f"No .fbx files found in {fbx_path}")

    print(f"Found {len(fbx_files)} FBX files to process")

    # Get or create collection
    collection_name = "animations"
    animation_collection = bpy.data.collections.get(collection_name)
    if not animation_collection:
        animation_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(animation_collection)

    for input_file_path in fbx_files:
        # Track what was in scene before import
        pre_import_objects = set(bpy.data.objects)

        bpy.ops.import_scene.fbx(
            filepath=input_file_path,
            use_anim=True,
            ignore_leaf_bones=False,
            force_connect_children=False,
            automatic_bone_orientation=True,
        )

        # Find newly imported objects
        imported_objects = set(bpy.data.objects) - pre_import_objects

        # Move to collection
        for obj in imported_objects:
            print(
                f"Importing object name: {obj.name} of type {obj.type} with parent {obj.parent} from file {input_file_path}")

            obj["source_path"] = input_file_path
            obj["source_file"] = os.path.basename(input_file_path)
            obj["is_root"] = False
            if obj.parent is None:
                obj["is_root"] = True

            # rename animation armatures and data containers to avoid conflicts
            if obj.type == 'ARMATURE':
                obj.name = f"Anim_{os.path.splitext(os.path.basename(input_file_path))[0]}"
                # obj.data.name = obj.name

            # Unlink from all current collections
            for col in obj.users_collection:
                col.objects.unlink(obj)

            # Link to target collection
            animation_collection.objects.link(obj)

        print(f"Imported {len(imported_objects)} objects from {os.path.basename(input_file_path)}")

    return animation_collection


def combine_characters_and_animations(characters, animations):
    for char_arm in characters.objects:
        if not char_arm.type == 'ARMATURE':
            continue

        print(f"Processing Object: {char_arm.name} from file {char_arm['source_file']}")

        if not char_arm.animation_data:
            char_arm.animation_data_create()

        for anim_arm in animations.objects:
            if not anim_arm.type == 'ARMATURE':
                continue

            if not bones_match(char_arm, anim_arm):
                raise ValueError(f"WARNING: Skeleton mismatch between {char_arm.name} and {anim_arm.name}")
                # NOTE: testing, skip for now (hard)
                # retarget_synty_to_mixamo_bones(anim_arm)
                bones_match(char_arm, anim_arm)
                pass

            if not char_arm.scale == anim_arm.scale:
                raise ValueError(f"** Character and Animation Scale Mismatch: #{char_arm.scale} vs {anim_arm.scale}")

            print(f"Adding animation from file {anim_arm['source_file']}")

            if anim_arm.animation_data and anim_arm.animation_data.action:
                folder_name = os.path.basename(os.path.dirname(anim_arm['source_path']))
                file_name = os.path.splitext(anim_arm['source_file'])[0]
                if folder_name == 'animations':
                    anim_name = f"None - {file_name.title()}"
                else:
                    anim_name = f"{folder_name} - {file_name.title()}"

                if char_arm.animation_data and any(
                        t.name.lower() == anim_name.lower() for t in char_arm.animation_data.nla_tracks):
                    raise ValueError(f"Duplicate NLA track name detected for {char_arm.name}: {anim_name}")

                # Rename the action
                action = anim_arm.animation_data.action
                action.name = anim_name

                track = char_arm.animation_data.nla_tracks.new()
                track.name = anim_name
                strip = track.strips.new(name=anim_name, start=0, action=action)

                if action.users == 0:
                    raise ValueError(f"WARNING: Action {action.name} has no users, skipping")

                if action.frame_range[0] >= action.frame_range[1]:
                    raise ValueError(f"WARNING: Action {action.name} has invalid frame range {action.frame_range}")

                strip.name = anim_name
                strip.action_frame_start = int(action.frame_range[0])
                strip.action_frame_end = int(action.frame_range[1])
                strip.extrapolation = 'NOTHING'

                print(f"  Created track '{track.name}' with action '{action.name}'")

        for t in char_arm.animation_data.nla_tracks:
            print(f"NLA Track: {t.name}, strips: {[s.name for s in t.strips]}")

    print("\n=== All NLA Tracks ===")
    for char_arm in characters.objects:
        if char_arm.type == 'ARMATURE':
            print(f"\nArmature: {char_arm.name}")
            if char_arm.animation_data:
                for i, track in enumerate(char_arm.animation_data.nla_tracks):
                    print(f"  Track {i}: '{track.name}'")
                    for j, strip in enumerate(track.strips):
                        print(
                            f"    Strip {j}: '{strip.name}' -> Action: '{strip.action.name if strip.action else None}'")
            else:
                print("  No animation data")

    return characters


def debug_character_materials(chars):
    for mesh in chars.all_objects:
        if mesh.type != "MESH":
            continue

        print(f"\nMesh: {mesh.name}")
        for mat in mesh.data.materials:
            if not mat:
                continue

            print(f"  Material: {mat.name}")
            node_tree = getattr(mat, "node_tree", None)
            if not node_tree:
                continue

            for node in node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    img = node.image

                    if img.packed_file:
                        print(f"    ✅ Embedded texture: {img.name} (packed in FBX) #{img.filepath}")
                        # print(f"       Updating file paths to relative filenames")
                        # img.filepath = f"//{img.name}"
                        # img.filepath_raw = f"//{img.name}"
                    elif os.path.exists(bpy.path.abspath(img.filepath)):
                        print(f"    ✅ External texture found: {img.filepath}")
                    else:
                        print(f"    ⚠️ Missing external texture: {img.filepath}")
                elif node.type == "TEX_IMAGE" and not node.image:
                    print(f"    ⚠️ Image node has no image assigned.")


def normalize_and_deduplicate_images():
    """
    Ensures all images are packed internally and deduplicates images
    that reference the same source file.
    """
    from collections import defaultdict

    # Step 1: Pack all images
    for img in bpy.data.images:
        # Skip generated/render result images
        if img.type in ('RENDER_RESULT', 'COMPOSITING'):
            continue

        if img.packed_file:
            # Already packed
            img.filepath = f"//{img.name}"
            img.filepath_raw = f"//{img.name}"
            print(f"✅ Already packed: {img.name}")
        elif img.filepath:
            abs_path = bpy.path.abspath(img.filepath)
            if os.path.exists(abs_path):
                img.pack()
                img.filepath = f"//{img.name}"
                img.filepath_raw = f"//{img.name}"
                print(f"✅ Packed external image: {img.name} from {img.filepath}")
            else:
                raise FileNotFoundError(f"❌ Missing external texture: {img.filepath} for image '{img.name}'")
        else:
            if img.size[0] > 0 and img.size[1] > 0:
                print(f"⚠️  Generated/procedural image (skipping): {img.name}")
            else:
                raise RuntimeError(f"❌ Image '{img.name}' has no data and no filepath")

    # Step 2: Deduplicate images
    file_to_images = defaultdict(list)
    for img in bpy.data.images:
        if img.filepath:
            # normalize path
            abs_path = bpy.path.abspath(img.filepath)
            file_to_images[abs_path].append(img)

    for abs_path, images in file_to_images.items():
        if len(images) <= 1:
            continue

        canonical = images[0]
        duplicates = images[1:]

        for dup_img in duplicates:
            # Reassign all node references to canonical image
            for user in dup_img.users:
                if hasattr(user, 'node_tree'):
                    for node in user.node_tree.nodes:
                        if getattr(node, 'image', None) == dup_img:
                            node.image = canonical
            # Remove duplicate image
            bpy.data.images.remove(dup_img)
            print(f"♻️ Removed duplicate image datablock: {dup_img.name}, kept: {canonical.name}")

    print("\n✅ All images packed and deduplicated")


def export_fbx_collection_with_animations(collection, output_path):
    for obj in collection.objects:
        if not obj.type == 'ARMATURE':
            continue

        print(f"Exporting Object: {obj.name} from file {obj['source_file']}")

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        for child in obj.children_recursive:
            child.select_set(True)

        output_fn = os.path.join(output_path, obj["source_file"].replace(".fbx", "-with-animations.fbx"))
        bpy.ops.export_scene.fbx(filepath=output_fn,
                                 use_selection=True,
                                 embed_textures=True,
                                 path_mode='COPY',  # Explicitly copy textures
                                 bake_anim=True,
                                 bake_anim_use_all_actions=False,
                                 bake_anim_use_nla_strips=True,
                                 add_leaf_bones=False,
                                 apply_scale_options='FBX_SCALE_UNITS',
                                 axis_forward='-Z',
                                 axis_up='Y',
                                 )


def debug_image_datablocks():
    print("\n=== Current Blender Images ===")
    seen = {}
    for img in bpy.data.images:
        key = bpy.path.abspath(img.filepath) if img.filepath else img.name
        if key in seen:
            print(f"⚠️ Duplicate image detected: {img.name} (same as {seen[key].name}) -> {key}")
        else:
            seen[key] = img
            print(f"✅ Image: {img.name}, filepath: {img.filepath}, packed: {bool(img.packed_file)}")
    print("=== End of Images ===\n")


def is_in_t_pose(char_collection, deviation_threshold=1.0, fix=False):
    """
    Detect and (optionally) correct A-pose to T-pose by leveling shoulder+arm bones.
    """
    any_deviation = False

    for obj in char_collection.objects:
        if obj.type != 'ARMATURE':
            continue

        print(f"Checking armature: {obj.name}")
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='POSE')

        for side in ['Left', 'Right']:
            # Try clavicle (shoulder) and arm in that order
            for bone_key in [f"mixamorig:{side}Arm"]:  # f"mixamorig:{side}Shoulder", shoulder seems to be too much
                bone = obj.pose.bones.get(bone_key)
                if not bone:
                    continue

                vec = bone.tail - bone.head
                if vec.length == 0:
                    continue
                vecn = vec.normalized()
                vertical_angle = math.degrees(math.acos(abs(vecn.z)))
                deviation = 90.0 - vertical_angle
                print(f"  {bone.name}: vertical angle {vertical_angle:.2f}°, deviation {deviation:.2f}°")

                if abs(deviation) > deviation_threshold:
                    any_deviation = True
                    # if fix:
                    #     vec_h = Vector((vecn.x, vecn.y, 0.0))
                    #     if vec_h.length < 1e-6:
                    #         continue
                    #     vec_h.normalize()
                    #     rot_q = vecn.rotation_difference(vec_h)
                    #     rot_mat = rot_q.to_matrix().to_4x4()
                    #     head = bone.head.copy()
                    #     bone.matrix = (
                    #         Matrix.Translation(head)
                    #         @ rot_mat
                    #         @ Matrix.Translation(-head)
                    #         @ bone.matrix
                    #     )
                    #     print(f"    ✅ Corrected {bone.name} by {deviation:.2f}° to horizontal")

        bpy.ops.object.mode_set(mode='OBJECT')

    return not any_deviation


# NOTE: testing/not ready/not working
def retarget_synty_to_mixamo_bones(armature):
    """Rename Synty bone names to match Mixamo convention"""

    bone_map = {
        # Core/Spine
        # 'Root': '',
        'Hips': 'mixamorig:Hips',
        'Spine_01': 'mixamorig:Spine',
        'Spine_02': 'mixamorig:Spine1',
        'Spine_03': 'mixamorig:Spine2',
        'Neck': 'mixamorig:Neck',
        'Head': 'mixamorig:Head',

        # Left Arm
        'Clavicle_L': 'mixamorig:LeftShoulder',
        'Shoulder_L': 'mixamorig:LeftArm',
        'Elbow_L': 'mixamorig:LeftForeArm',
        'Hand_L': 'mixamorig:LeftHand',

        # Right Arm
        'Clavicle_R': 'mixamorig:RightShoulder',
        'Shoulder_R': 'mixamorig:RightArm',
        'Elbow_R': 'mixamorig:RightForeArm',
        'Hand_R': 'mixamorig:RightHand',

        # Left Hand Fingers
        'Thumb_01': 'mixamorig:LeftHandThumb1',
        'Thumb_02': 'mixamorig:LeftHandThumb2',
        'Thumb_03': 'mixamorig:LeftHandThumb3',
        # '': 'mixamorig:LeftHandThumb4',
        'IndexFinger_01': 'mixamorig:LeftHandIndex1',
        'IndexFinger_02': 'mixamorig:LeftHandIndex2',
        'IndexFinger_03': 'mixamorig:LeftHandIndex3',
        'IndexFinger_04': 'mixamorig:LeftHandIndex4',
        # '': 'mixamorig:LeftHandMiddle1',
        # '': 'mixamorig:LeftHandMiddle2',
        # '': 'mixamorig:LeftHandMiddle3',
        # '': 'mixamorig:LeftHandMiddle4',
        # '': 'mixamorig:LeftHandRing1',
        # '': 'mixamorig:LeftHandRing2',
        # '': 'mixamorig:LeftHandRing3',
        # '': 'mixamorig:LeftHandRing4',
        'Finger_01': 'mixamorig:LeftHandPinky1',
        'Finger_02': 'mixamorig:LeftHandPinky2',
        'Finger_03': 'mixamorig:LeftHandPinky3',
        'Finger_04': 'mixamorig:LeftHandPinky4',

        # Right Hand Fingers
        'Thumb_01_1': 'mixamorig:RightHandThumb1',
        'Thumb_02_1': 'mixamorig:RightHandThumb2',
        'Thumb_03_1': 'mixamorig:RightHandThumb3',
        # '': 'mixamorig:RightHandThumb4',
        'IndexFinger_01_1': 'mixamorig:RightHandIndex1',
        'IndexFinger_02_1': 'mixamorig:RightHandIndex2',
        'IndexFinger_03_1': 'mixamorig:RightHandIndex3',
        'IndexFinger_04_1': 'mixamorig:RightHandIndex4',
        # '': 'mixamorig:RightHandMiddle1',
        # '': 'mixamorig:RightHandMiddle2',
        # '': 'mixamorig:RightHandMiddle3',
        # '': 'mixamorig:RightHandMiddle4',
        # '': 'mixamorig:RightHandRing1',
        # '': 'mixamorig:RightHandRing2',
        # '': 'mixamorig:RightHandRing3',
        # '': 'mixamorig:RightHandRing4',
        'Finger_01_1': 'mixamorig:RightHandPinky1',
        'Finger_02_1': 'mixamorig:RightHandPinky2',
        'Finger_03_1': 'mixamorig:RightHandPinky3',
        'Finger_04_1': 'mixamorig:RightHandPinky4',

        # Left Leg
        'UpperLeg_L': 'mixamorig:LeftUpLeg',
        'LowerLeg_L': 'mixamorig:LeftLeg',
        'Ankle_L': 'mixamorig:LeftFoot',
        'Ball_L': 'mixamorig:LeftToeBase',
        'Toes_L': 'mixamorig:LeftToe_End',

        # Right Leg
        'UpperLeg_R': 'mixamorig:RightUpLeg',
        'LowerLeg_R': 'mixamorig:RightLeg',
        'Ankle_R': 'mixamorig:RightFoot',
        'Ball_R': 'mixamorig:RightToeBase',
        'Toes_R': 'mixamorig:RightToe_End',

        # Face (optional - Mixamo may not have these)
        # 'Jaw': 'mixamorig:Jaw',
        # 'Eyes': 'mixamorig:HeadTop_End',
        # 'Eyebrows': 'mixamorig:HeadTop_End',

        # Props (optional - skip if Mixamo doesn't have these)
        # 'Prop_L': None,  # Skip
        # 'Prop_R': None,  # Skip
    }

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    renamed_count = 0
    skipped = []

    for old_name, new_name in bone_map.items():
        bone = armature.data.edit_bones.get(old_name)
        if bone:
            if new_name:  # Only rename if we have a target
                bone.name = new_name
                renamed_count += 1
                print(f"  Renamed: {old_name} → {new_name}")
            else:
                skipped.append(old_name)

    bpy.ops.object.mode_set(mode='OBJECT')

    if skipped:
        print(f"⚠️  Skipped bones (no Mixamo equivalent): {skipped}")

    print(f"✅ Renamed {renamed_count} bones in {armature.name}")

    return renamed_count > 0


def main():
    characters_path, animations_path, output_path = process_args()
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # Get list of character files
    character_files = [
        os.path.join(characters_path, f)
        for f in os.listdir(characters_path)
        if f.lower().endswith(".fbx")
    ]

    if not character_files:
        raise FileNotFoundError(f"No .fbx files found in {characters_path}")

    print(f"Found {len(character_files)} character(s) to process")

    character_files.sort()

    # Process each character separately
    for char_file in character_files:
        print(f"\n{'=' * 60}")
        print(f"Processing character: {os.path.basename(char_file)}")
        print(f"{'=' * 60}\n")

        # Clear blender scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # Import animations (shared across all characters)
        print("\nImporting animations...")
        animations = get_animations(animations_path)

        # Import this character
        print("\nImporting character...")
        character = get_character(char_file)

        debug_character_materials(character)

        if not is_in_t_pose(character):
            # raise ValueError('Not in T-Pose')
            print("Character not in T-Pose, not exporting")
            continue

        normalize_and_deduplicate_images()
        debug_image_datablocks()

        # Combine and export with animations
        print("\nProcessing...")
        combined_characters = combine_characters_and_animations(character, animations)

        print("\nExporting...")
        export_fbx_collection_with_animations(combined_characters, output_path)

    print("\nComplete!")


if __name__ == "__main__":
    main()
