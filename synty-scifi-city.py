"""
This is a Blender script to take assets from the Synty SciFi City pack and set them up for easy import into Godot.

This script was tested against POLYGON_SciFi_City_SourceFiles_v4

Notes:
    - We import/export Characters and Objects with different options (animation, bones, etc.)
    - We output individual Characters as well as a "shared" object with all Character meshes (like the original file)
    - This doesn't fix all files in the asset pack - skipped files are listed at the end of the script run
    - We're only reading the FBX and Textures dirs (that covers everything, right?)

Changes:
    - Resize armatures to match meshes
    - De-dupe materials and fix broken material links
    - Copy textures to textures/ dir and reference from files
    - Rename some child objects for clarity (material names, etc.)
    - Apply transforms for GLB/GLTF (to fix mesh facing issue in Godot import)
    - Removing vertex colors from Characters on FBX export (causing Godot import issues)
    - Maybe other stuff I missed

Issues:
    - Some characters appear to have import corruption in Godot (issue is present with original Synty Characters.fbx?)
"""
import bpy
import shutil
import sys
import os
from collections import defaultdict

USAGE = "Usage: blender --background --python synty-scifi-city.py -- <input_dir> <output_dir>"

# NOTE: debug these further, let's just see what we can get working easily
SM_FILES_TO_SKIP = [
    "SM_LightRayCube.fbx",  # TODO: look at this - has an armature?
]

# TODO: validate all of these are correct
FILE_REPLACEMENTS = {
    "PolygonScifi_Texture.psd": "PolygonScifi_01_A.png",
    "Building_Window_Emissive.psd": "PolygonScifi_Background_Building_Emissive.png",
    "PolygonScifi_.psd": "PolygonScifi_01_A.png",
    "BillboardsGraffiti_01.psd": "Billboards.png",
    "PolygonCity_Road_01.png": "PolygonSciFi_Road_01.png",
    "PolygonCity_Texture_01_A.png": "PolygonScifi_01_A.png",
    "Signs_Emission.psd": "PolygonScifi_Emissive_01.png",  # TODO: wrong? they don't seem to line up
    "Neon_Animation.psd": "Billboards.png",
    "PolygonScifi_Texture_Mike.psd": "PolygonScifi_01_A.png",
    "PolygonSciFiCity_Texture_01_A.png": "PolygonScifi_01_A.png",  # Characters
}


def parse_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 2:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        input_path = argv[0]
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path does not exist: {input_path}")

        output_path = argv[1]
        if not os.path.isdir(output_path):
            os.mkdir(output_path)

    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)

    return input_path, output_path


def select_object_and_children(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)


def get_root_object(collection):
    # after import all objects are selected in no particular order, find the root object
    roots = [obj for obj in collection if obj.parent is None]
    if len(roots) != 1:
        raise RuntimeError(f"Expected exactly 1 root object, found {len(roots)}: {[o.name for o in roots]}")

    return roots[0]


def export_fbx(obj, output_path):
    select_object_and_children(obj)
    # FBX exporter does this automatically (?)
    # bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        bake_anim=False,
        # # Embedding textures
        # embed_textures=True,
        # path_mode='COPY',
        # Referencing textures
        embed_textures=False,
        path_mode='RELATIVE',
        # # These are for armatures
        # bake_anim_use_all_actions=False,
        # bake_anim_use_nla_strips=True,
        add_leaf_bones=False,
        # # Not sure if we need these to fix facing
        # apply_scale_options='FBX_SCALE_UNITS',
        # axis_forward='-Z',
        # axis_up='Y',
    )


def export_gltf(obj, output_path):
    select_object_and_children(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.export_scene.gltf(
        filepath=output_path.replace(".fbx", ".gltf"),
        use_selection=True,
        export_format='GLTF_SEPARATE',
        export_animations=False,
        export_lights=False,
        export_materials='EXPORT',
        export_texture_dir='textures',
    )


def export_glb(obj, output_path):
    select_object_and_children(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.export_scene.gltf(
        filepath=output_path.replace(".fbx", ".glb"),
        use_selection=True,
        export_format='GLB',
        export_animations=False,
        export_lights=False,
        export_materials='EXPORT',
    )


def debug_image_datablocks():
    print("\n=== Current Blender Images")
    seen = {}
    for image in bpy.data.images:
        key = bpy.path.abspath(image.filepath) if image.filepath else image.name
        if key in seen:
            print(f"⚠️ Duplicate image detected: {image.name} (same as {seen[key].name}) -> {key}")
        else:
            seen[key] = image
            print(f"✅ Image: {image.name}, filepath: {image.filepath}, packed: {bool(image.packed_file)}")
    print("=== End of Images\n")


def fix_missing_mesh_materials(mesh, output_path):
    print(f"\nProcessing mesh: {mesh.name}")

    textures_dir = os.path.join(output_path, "textures")
    for mat in mesh.data.materials:
        if not mat:
            continue

        node_tree = getattr(mat, "node_tree", None)
        if not node_tree:
            continue

        for node in node_tree.nodes:
            if node.type != "TEX_IMAGE":
                print(f"   Skipping node type {node.type}")
                continue

            if not node.image:
                print(f"   ⚠️ Node {node.name} has no image")
                continue

            tex_filename = os.path.basename(node.image.filepath)
            fs_path = os.path.join(textures_dir, tex_filename)

            if os.path.exists(fs_path):
                print(f"   ✅ Found on disk: {fs_path}")
                # Assign absolute path so Blender can load it
                node.image.filepath = fs_path
                node.image.filepath_raw = fs_path
                node.image.reload()
            else:
                found_replacement = False
                for old_name, new_name in FILE_REPLACEMENTS.items():
                    if old_name in tex_filename:
                        fs_path = os.path.join(textures_dir, new_name)
                        if os.path.exists(fs_path):
                            print(f"   🔄 Replaced {tex_filename} -> {new_name}")
                            node.image.filepath = fs_path
                            node.image.filepath_raw = fs_path
                            node.image.reload()
                            tex_filename = new_name
                            found_replacement = True
                            break

                if not found_replacement:
                    raise FileNotFoundError(f"Could not find texture for object {mesh.name}: {fs_path}")

            mat.name = tex_filename
            node.image.filepath_raw = node.image.filepath
            node.image.reload()
            print(f"   Texture node: {node.name} | Filepath (relative): {node.image.filepath}")

    return mesh


def deduplicate_images():
    """Deduplicate images that point to the same filepath."""
    seen = {}
    for img in bpy.data.images[:]:
        key = bpy.path.abspath(img.filepath) if img.filepath else img.name
        if key in seen:
            original = seen[key]
            duplicate_name = img.name

            for mat in bpy.data.materials:
                if not mat.node_tree:
                    continue
                for node in mat.node_tree.nodes:
                    if getattr(node, "image", None) == img:
                        node.image = original

            bpy.data.images.remove(img)
            print(f"Removed duplicate image: {duplicate_name}, reassigned to {original.name}")
        else:
            seen[key] = img


def deduplicate_materials():
    """Deduplicate materials that have the same texture/image setup."""
    materials_by_texture = defaultdict(list)

    # Group materials by their primary texture
    for mat in bpy.data.materials[:]:
        if not mat.node_tree:
            continue

        # Find the image texture node
        texture_path = None
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                texture_path = node.image.filepath
                break

        if texture_path:
            materials_by_texture[texture_path].append(mat)

    # For each group of materials with the same texture, keep only one
    for texture_path, mats in materials_by_texture.items():
        if len(mats) <= 1:
            continue

        # Keep the material without any .00x suffix
        primary = None
        for m in mats:
            # Check if name doesn't contain .00x pattern
            if not any(m.name.endswith(f'.{i:03d}') for i in range(1, 1000)):
                primary = m
                break

        # Fallback to first material if none found without suffix
        if primary is None:
            primary = mats[0]

        duplicates = [m for m in mats if m != primary]

        print(f"Found {len(duplicates)} duplicate materials for texture: {texture_path}")
        print(f"  Keeping: {primary.name}")

        # Reassign all objects using duplicate materials to use the primary
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue

            for slot_idx, slot in enumerate(obj.material_slots):
                if slot.material in duplicates:
                    print(f"  Reassigning {obj.name} slot {slot_idx} from {slot.material.name} to {primary.name}")
                    obj.material_slots[slot_idx].material = primary

        # Remove duplicate materials
        for dup in duplicates:
            print(f"  Removing duplicate material: {dup.name}")
            bpy.data.materials.remove(dup)


def scale_bones(armature):
    # scale bones to match meshes without scaling meshes (fixes tiny skeleton)
    SCALE_FACTOR = 10.0

    print(f"Scaling bones for armature: {armature.name} by factor {SCALE_FACTOR}")

    # Temporarily unparent meshes
    meshes = [c for c in armature.children_recursive if c.type == 'MESH']

    mesh_parents = {m: m.parent for m in meshes}
    for m in meshes:
        m.parent = None

    # Enter edit mode to scale bones
    select_object_and_children(armature)
    bpy.ops.object.mode_set(mode='EDIT')

    for bone in armature.data.edit_bones:
        bone.head *= SCALE_FACTOR
        bone.tail *= SCALE_FACTOR

    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Restore mesh parenting
    for m, parent in mesh_parents.items():
        m.parent = armature


def process_characters(fbx_file, output_path):
    print(f"\n=== Processing {fbx_file}")

    # clear Blender scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.import_scene.fbx(
        filepath=fbx_file,
        use_anim=False,
        ignore_leaf_bones=False,
        force_connect_children=False,
        automatic_bone_orientation=False,
    )

    # after import all objects are selected in no particular order, find the root object
    root_obj = get_root_object(bpy.context.selected_objects)
    print(f"Root object: {root_obj.name}")

    scale_bones(root_obj)

    mesh_children = [c for c in root_obj.children_recursive if c.type == 'MESH']
    if not mesh_children:
        raise RuntimeError(f"No meshes found under armature {root_obj.name}")

    for mesh in mesh_children:
        fix_missing_mesh_materials(mesh, output_path)

    for mesh in mesh_children:
        print(f"   Exporting mesh: {mesh.name}")
        # print(f"   Material slots: {len(mesh.material_slots)}")
        # for idx, slot in enumerate(mesh.material_slots):
        #     print(f"     Slot {idx}: {slot.material.name if slot.material else 'EMPTY'}")

        # Select the armature + this mesh only
        bpy.ops.object.select_all(action='DESELECT')
        root_obj.select_set(True)
        mesh.select_set(True)

        out_file = os.path.join(output_path, f"Character-{mesh.name}.fbx")
        bpy.ops.export_scene.fbx(
            filepath=out_file,
            use_selection=True,
            bake_anim=False,
            embed_textures=False,
            path_mode='RELATIVE',
            add_leaf_bones=False,
            colors_type='NONE',
        )

        print(f"✅ Exported: {out_file}")

    select_object_and_children(root_obj)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(output_path, f"Character-AllMeshes.fbx"),
        use_selection=True,
        bake_anim=False,
        embed_textures=False,
        path_mode='RELATIVE',
        add_leaf_bones=False,
        colors_type='NONE',
    )


def process_files(fbx_files, output_path):
    # Process files
    skipped_files = []
    for fbx_file in fbx_files:
        # NOTE: debug testing - syr has multiple meshes
        # if "sm_wep_syr" not in fbx_file.lower():
        #     continue

        if os.path.basename(fbx_file) == "Characters.fbx":
            process_characters(fbx_file, output_path)
            continue

        if not os.path.basename(fbx_file).lower().startswith("sm_"):
            print(f"\n=== Skipping file that does not start with sm_: {fbx_file}")
            skipped_files.append(fbx_file)
            continue

        if os.path.basename(fbx_file) in SM_FILES_TO_SKIP:
            print(f"\n=== Skipping file in FILES_TO_SKIP: {fbx_file}")
            skipped_files.append(fbx_file)
            continue

        print(f"\n=== Processing {fbx_file}")

        # clear Blender scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

        print(f"Scene objects: {len(bpy.context.scene.objects)}")

        # NOTE: these options will change how the import works!
        bpy.ops.import_scene.fbx(
            filepath=fbx_file,
            use_anim=False,
            ignore_leaf_bones=False,
            force_connect_children=False,
            automatic_bone_orientation=True,
        )

        print(f"Scene objects: {len(bpy.context.scene.objects)}")

        # after import all objects are selected in no particular order, find the root object
        root_obj = get_root_object(bpy.context.selected_objects)
        print(f"Root object: {root_obj.name}")

        # select root and all children for export
        select_object_and_children(root_obj)

        # collect all objects under root
        all_objects = [root_obj] + list(root_obj.children_recursive)

        # verify they are all meshes
        non_meshes = [obj for obj in all_objects if obj.type != 'MESH']
        if non_meshes:
            names = [obj.name for obj in non_meshes]
            raise RuntimeError(f"Non-mesh objects found under root '{root_obj.name}': {names}")

        debug_image_datablocks()

        # fix materials for every mesh
        for mesh in all_objects:
            print(f"Fixing materials for: {mesh.name}")
            fix_missing_mesh_materials(mesh, output_path)

        deduplicate_images()
        deduplicate_materials()

        debug_image_datablocks()

        # export object
        export_fbx(root_obj, os.path.join(output_path, os.path.basename(fbx_file)))
        # export_gltf(root_obj, os.path.join(output_path, os.path.basename(fbx_file)))
        # export_glb(root_obj, os.path.join(output_path, os.path.basename(fbx_file)))

    print("\n=== Skipped Files:")
    for s_file in skipped_files:
        print(s_file)


def main():
    input_path, output_path = parse_args()

    print(f"=== Input path: {input_path}")
    print(f"=== Output path: {output_path}")

    # check paths
    fbx_path = os.path.join(input_path, "Source_Files", "FBX")
    if not os.path.isdir(fbx_path):
        raise FileNotFoundError(f"FBX path not found")

    textures_path = os.path.join(input_path, "Source_Files", "Textures")
    if not os.path.isdir(textures_path):
        raise FileNotFoundError(f"Textures path not found")

    # copy textures to output dir so our relative paths will work
    output_textures_path = os.path.join(output_path, "textures")
    if os.path.exists(output_textures_path):
        shutil.rmtree(output_textures_path)
    shutil.copytree(textures_path, output_textures_path)

    # get all FBX files
    fbx_files = []
    for filename in os.listdir(fbx_path):
        if filename.lower().endswith(".fbx"):
            full_path = os.path.join(fbx_path, filename)
            fbx_files.append(full_path)

    print(f"\n=== Found {len(fbx_files)} FBX files to process")

    fbx_files.sort()
    process_files(fbx_files, output_path)

    print("\n\n=== Finished processing")


if __name__ == "__main__":
    main()
