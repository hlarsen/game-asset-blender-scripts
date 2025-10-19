# Game Asset Blender Scripts

This is a small collection of scripts to work with 3D assets in Blender. It exists because I wanted to learn more about
3D files while playing around with Godot and Blender using both free and purchased assets. The scripts do things that
may or may not be useful, like fixing material paths or combining meshes and animations.

No assets are included in this repo.

## Scripts

These scripts run via blender: `blender --background --python <script>.py -- <options>`. You can review the script or
run `blender --background --python <script>.py` for usage help.

- `fbx-info.py`: Reads an FBX and outputs some of its data
- `synty-scifi-city.py`: Processes the Synty Sci-Fi City pack to fix materials and other cleanup

## Assets and Goals

I've been working with some Synty asset packs I have licenses for, as well as some Mixamo models and animations. Besides
getting more familiar with the file formats in general, another initial goal was to see if I could mix Mixamo and Synty
characters/animations.

### Future Work

I'll likely continue looking at the other packs I have licenses for as time/interest permits:

- Base Locomotion (The biggest issue is the Rest Pose is not T-pose on these - I have some test code)
- Casino
- City
- Mech
- Nature Biomes: Arid Desert

## Notes

I am not a 3D modeler or game developer, so if I'm doing anything obviously wrong please feel free to let me know. I've
been talking with Claude and ChatGPT to help learn the 3D space, but there shouldn't be any blocks of weird opaque
LLM-generated code anywhere.
