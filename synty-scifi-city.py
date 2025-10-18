"""
Blender script to take assets from the Synty SciFi City pack and set them up for easy import into Godot
"""
import bpy
import shutil
import sys
import os
from collections import defaultdict

USAGE = "Usage: blender --background --python fbx-scifi_city.py -- <fbx_dir>"

# TODO: debug these further, let's just see what we can get working easily
FILES_TO_SKIP = [
    "SM_LightRayCube.fbx"
]

# TODO: validate all of these are correct
FILE_REPLACEMENTS = {
    "PolygonScifi_Texture.psd": "PolygonScifi_01_A.png",
    "Building_Window_Emissive.psd": "PolygonScifi_Background_Building_Emissive.png",
    "PolygonScifi_.psd": "PolygonScifi_01_A.png",
    "BillboardsGraffiti_01.psd": "Billboards.png",
    "PolygonCity_Road_01.png": "PolygonSciFi_Road_01.png",
    "PolygonCity_Texture_01_A.png": "PolygonScifi_01_A.png",
    "Signs_Emission.psd": "PolygonScifi_Emissive_01.png",  # TODO: wrong?
    "Neon_Animation.psd": "Billboards.png",
    "PolygonScifi_Texture_Mike.psd": "PolygonScifi_01_A.png",
}


def parse_args():
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]

        if len(argv) < 1:
            print("ERROR: Not enough arguments provided")
            print(USAGE)
            sys.exit(1)

        input_path = argv[0]
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Path does not exist: {input_path}")

    except ValueError:
        print("ERROR: No arguments found after '--'")
        print(USAGE)
        sys.exit(1)

    if not os.path.normpath(input_path).endswith("POLYGON_SciFi_City_SourceFiles_v4"):
        raise ValueError(f"Path does not end in POLYGON_SciFi_City_SourceFiles_v4, pack/version not supported")

    return input_path


def export_fbx(obj, output_path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)

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
        # add_leaf_bones=False,
        # # Not sure if we need these to fix facing
        # apply_scale_options='FBX_SCALE_UNITS',
        # axis_forward='-Z',
        # axis_up='Y',
    )


def export_gltf(obj, output_path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path.replace(".fbx", ""),
        use_selection=True,
        export_format='GLTF_SEPARATE',
        export_animations=False,
        export_lights=False,
        export_materials='EXPORT',
        export_texture_dir='textures',
    )


def export_glb(obj, output_path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path.replace(".fbx", ""),
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


def fix_missing_mesh_materials(mesh):
    for mat in mesh.data.materials:
        if not mat:
            continue

        node_tree = getattr(mat, "node_tree", None)
        if not node_tree:
            continue

        for node in node_tree.nodes:
            if not node.type == "TEX_IMAGE":
                print(f"   Skipping node type {node.type}")
                continue

            img_path = node.image.filepath if node.image else "(no path set)"
            print(f"   Image Path: {img_path}")

            if os.path.exists(os.path.abspath(bpy.path.abspath(img_path))) if node.image else False:
                print("   ✅ Found")
                node.image.name = mesh.name
                texture_path = img_path
                node.image.filepath = os.path.join("textures", os.path.basename(texture_path))
                node.image.filepath_raw = node.image.filepath
            else:
                print("   ❌ Missing, attempting to fix...")

                for old_name, new_name in FILE_REPLACEMENTS.items():
                    if old_name in img_path:
                        img_path = img_path.replace(old_name, new_name)

                # try to find the right one
                texture_path = os.path.join(
                    os.getcwd(),
                    "assets",
                    "synty",
                    "POLYGON_SciFi_City_SourceFiles_v4",
                    "Source_Files",
                    "Textures",
                    os.path.basename(img_path)
                )

                if not os.path.exists(texture_path):
                    if not os.path.exists(texture_path):
                        raise FileNotFoundError(f"Could not find texture for object {mesh.name}: {texture_path}")

                node.image.name = os.path.basename(img_path)
                node.image.filepath = os.path.join("textures", os.path.basename(texture_path))
                node.image.filepath_raw = node.image.filepath

            mat.name = os.path.basename(img_path)
            node.image.reload()
            print(f"   Texture node: {node.name}  | Filepath: {texture_path}")

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


def main():
    input_path = parse_args()

    print(f"=== Input path: {input_path}")

    # Get paths
    fbx_path = os.path.join(input_path, "Source_Files", "FBX")
    if not os.path.isdir(fbx_path):
        raise FileNotFoundError(f"FBX path not found")

    textures_path = os.path.join(input_path, "Source_Files", "Textures")
    if not os.path.isdir(textures_path):
        raise FileNotFoundError(f"Textures path not found")

    output_path = os.path.join("output", "synty-scifi-city_objects")
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
        if not os.path.isdir(output_path):
            raise FileNotFoundError(f"Output path not found")

    # copy textures to output dir so our relative paths will work
    output_textures_path = os.path.join(output_path, "textures")
    if os.path.exists(output_textures_path):
        shutil.rmtree(output_textures_path)
    shutil.copytree(textures_path, output_textures_path)

    # Get all matching files
    fbx_files = []
    for filename in os.listdir(fbx_path):
        if filename.lower().endswith(".fbx"):
            full_path = os.path.join(fbx_path, filename)
            fbx_files.append(full_path)

    fbx_files.sort()
    print(f"\n=== Found {len(fbx_files)} FBX files to process")

    # Process files
    skipped_files = []
    for fbx_file in fbx_files:
        # NOTE: debug testing
        # if "sm_wep_syr" not in fbx_file.lower():
        #     continue

        if not os.path.basename(fbx_file).lower().startswith("sm_"):
            print(f"\n=== Skipping file that does not start with sm_: {fbx_file}")
            skipped_files.append(fbx_file)
            continue

        if os.path.basename(fbx_file) in FILES_TO_SKIP:
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
        roots = [obj for obj in bpy.context.selected_objects if obj.parent is None]
        if len(roots) != 1:
            raise RuntimeError(f"Expected exactly 1 root object, found {len(roots)}: {[o.name for o in roots]}")

        root_obj = roots[0]
        print(f"Root object: {root_obj.name}")

        # select root and all children for export
        root_obj.select_set(True)
        for child in root_obj.children_recursive:
            child.select_set(True)

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
            fix_missing_mesh_materials(mesh)

        deduplicate_images()
        deduplicate_materials()

        debug_image_datablocks()

        # export object
        export_fbx(root_obj, os.path.join(output_path, os.path.basename(fbx_file)))
        # export_gltf(updated_obj, os.path.join(output_path, os.path.basename(fbx_file)))
        # export_glb(updated_obj, os.path.join(output_path, os.path.basename(fbx_file)))

    print("\n\n=== Finished processing")

    print("\n=== Skipped Files:")
    for s_file in skipped_files:
        print(s_file)


if __name__ == "__main__":
    main()
