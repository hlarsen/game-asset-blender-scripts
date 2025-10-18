# Asset Scripts

This is a small collection of scripts to work with 3D assets. It exists because I wanted to learn more about 3D files
while playing around with Godot and Blender using both free and purchased assets.

The scripts do things that may or may not be useful, like fixing material paths or combining meshes and animations.

Please check all output before using!

## Scripts

These scripts run via blender: `blender --background --python fbx-info.py -- path/to/file.fbx`

- `fbx-info.py`: Reads an FBX and outputs some of its data
- `synty-scifi-city.py`: Processes the Synty Sci-Fi City pack to fix materials and other stuff

## Assets

These scripts have been used with both Mixamo and Synty assets.

No assets are included in this repo.

## Notes

I am not a 3D modeler or game developer, so if I'm doing anything obviously wrong feel free to let me know.

I've been talking with Claude and ChatGPT to help learn the 3D space. I have not been trying to keep this tidy or set up
for reuse.

Synty has talked about better Godot support in the future, so that will be nice.

## TODO

- Set up with uv (haven't done much python since it came out, need to check it out)
- Clean up and add the other scripts
