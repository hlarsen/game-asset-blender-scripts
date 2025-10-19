"""
Combine multiple Mixamo animations into a single file

TODO:
    - General Review/Cleanup
    - Don't use collections
"""

import bpy
import glob
import os
import sys

USAGE = "Usage: blender --background --python mixamo-combine-animations.py -- <animation_dir> <output_dir>"


def process_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 2:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        animation_path = argv[0]
        if not os.path.exists(animation_path):
            raise FileNotFoundError(f"Animation path does not exist: {animation_path}")

        output_path = argv[1]
        if not os.path.isdir(output_path):
            os.mkdir(output_path)

    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)

    return animation_path, output_path


def bones_match(char_arm, anim_arm):
    bones_char = {b.name for b in char_arm.data.bones}
    bones_anim = {b.name for b in anim_arm.data.bones}

    # if we are missing animation bones in the character it will not work properly
    missing_in_anim = bones_anim - bones_char
    if missing_in_anim:
        # print(f"Bones in anim_arm but not in char_arm: {missing_in_anim}")
        raise ValueError(f"Bones in anim_arm but not in char_arm: {missing_in_anim}")

    # if we are missing character bones in the animation it _may_ not be too bad
    missing_in_char = bones_char - bones_anim
    if missing_in_char:
        print(f"Bones in char_arm but not in anim_arm: {missing_in_char}")
        # raise ValueError(f"Bones in char_arm but not in anim_arm: {missing_in_char}")

    return bones_char == bones_anim


def get_animations(fbx_path):
    if os.path.isdir(fbx_path):
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
            print(f"collections: {obj.users_collection}")

            obj["source_path"] = input_file_path
            obj["source_file"] = os.path.basename(input_file_path)

            # Unlink from all current collections
            for col in obj.users_collection:
                col.objects.unlink(obj)

            # Link to target collection
            animation_collection.objects.link(obj)

        print(f"Imported {len(imported_objects)} objects from {os.path.basename(input_file_path)}")

    return animation_collection


def combine_animations_into_skeleton(animations, target_name="Armature"):
    """
    Create a new armature and combine all animations from animation armatures.
    Returns the new armature with all actions as NLA tracks.
    No meshes are included.
    """

    # Find a template armature (just use the first animation skeleton)
    template_arm = next((obj for obj in animations.objects if obj.type == 'ARMATURE'), None)
    if not template_arm:
        raise ValueError("No armature found in animations collection!")

    # Duplicate the armature to create a new skeleton
    bpy.ops.object.select_all(action='DESELECT')
    template_arm.select_set(True)
    bpy.ops.object.duplicate()
    combined_arm = bpy.context.selected_objects[0]
    combined_arm.name = target_name

    # Clear animation data on the new skeleton
    if combined_arm.animation_data:
        combined_arm.animation_data_clear()
    combined_arm.animation_data_create()

    # Copy all actions from animations into NLA tracks
    for anim_arm in animations.objects:
        if anim_arm.type != 'ARMATURE':
            continue

        if not bones_match(combined_arm, anim_arm):
            raise ValueError(f"WARNING: Skeleton mismatch between {combined_arm.name} and {anim_arm.name}")

        if not anim_arm.animation_data or not anim_arm.animation_data.action:
            continue

        action = anim_arm.animation_data.action
        folder_name = os.path.basename(os.path.dirname(anim_arm['source_path']))
        file_name = os.path.splitext(anim_arm['source_file'])[0]
        if folder_name == 'animations':
            anim_name = f"None - {file_name.title()}"
        else:
            anim_name = f"{folder_name} - {file_name.title()}"

        # Duplicate action to avoid linking issues
        new_action = action.copy()
        new_action.name = anim_name

        # Create NLA track & strip
        track = combined_arm.animation_data.nla_tracks.new()
        track.name = anim_name
        strip = track.strips.new(name=anim_name, start=0, action=new_action)
        strip.action_frame_start = int(new_action.frame_range[0])
        strip.action_frame_end = int(new_action.frame_range[1])
        strip.extrapolation = 'NOTHING'

        print(f"Added NLA track '{track.name}' -> Action '{new_action.name}'")

    print(
        f"Combined skeleton created: {combined_arm.name} with {len(combined_arm.animation_data.nla_tracks)} NLA tracks")

    bpy.ops.object.select_all(action='DESELECT')

    return combined_arm


def export_fbx(combined_arm, output_path):
    if combined_arm.type != 'ARMATURE':
        raise ValueError(f"Expected an armature, got {combined_arm.type}")

    # Temporarily rename all OTHER armatures to avoid conflicts
    other_armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != combined_arm]
    temp_names = {}
    for other in other_armatures:
        temp_names[other] = other.name
        other.name = f"_temp_{other.name}"

    combined_arm.name = "Armature"

    bpy.ops.object.select_all(action='DESELECT')
    combined_arm.select_set(True)
    for child in combined_arm.children_recursive:
        child.select_set(True)

    output_fn = os.path.join(output_path, "combined_animations.fbx")
    bpy.ops.export_scene.fbx(
        filepath=output_fn,
        use_selection=True,
        bake_anim=True,
        bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=True,
        add_leaf_bones=False,
        apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Z',
        axis_up='Y',
    )

    print(f"Exported combined skeleton '{combined_arm.name}' to {output_fn}")


def main():
    animations_path, output_path = process_args()

    # clear blender scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    print("\nImporting animations...")
    animations = get_animations(animations_path)

    print("\nProcessing...")
    combined_animations = combine_animations_into_skeleton(animations)

    print("\nExporting...")
    export_fbx(combined_animations, output_path)

    print("Complete!")


if __name__ == "__main__":
    main()
