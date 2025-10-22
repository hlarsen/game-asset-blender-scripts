# Game Asset Blender Scripts

This is a small collection of scripts to work with 3D assets in Blender. It exists because I wanted to learn more about
3D files while playing around with Godot and Blender using both free and purchased assets. The scripts do things that
may or may not be useful, like fixing material paths or combining meshes and animations.

No assets are included in this repo.

## Scripts

These scripts run via blender: `blender --background --python <script>.py -- <options>`. You can review the script or
run `blender --background --python <script>.py` for usage help.

- `fbx-info.py`: Reads an FBX and outputs some of its data
- `mixamo-add-animations-to-character.py`: Adds an animation file to a Mixamo character
- `mixamo-combine-animations.py`: Combines multiple Mixamo animations into a single file
- `synty-kaiju.py`: Processes the Synty Kaiju pack to fix materials and other cleanup
- `synty-scifi-city.py`: Processes the Synty Sci-Fi City pack to fix materials and other cleanup

## Assets and Goals

I've been working with some Synty asset packs I have licenses for, as well as some Mixamo models and animations. Besides
getting more familiar with the file formats in general, another initial goal was to see if I could mix Mixamo and Synty
characters/animations.

### Feedback and Future Work

The bone maps in my [godot-synty-tools](https://github.com/hlarsen/godot-synty-tools) repo are an indication of what packs I
have licenses for - if anyone wants to say thanks by gifting me licenses for other packs I can add those as
well ;)

If there are any issues, please let me know.

## Notes

I am not a 3D modeler or game developer, so if I'm doing anything obviously wrong please feel free to let me know. I've
been talking with Claude and ChatGPT to help learn the 3D space, but there shouldn't be any blocks of weird opaque
LLM-generated code anywhere.

My repo [godot-synty-tools](https://github.com/hlarsen/godot-synty-tools) may be useful, it's an addon to work with and
import Synty assets directly into Godot.

## License

MIT, but if your commercial project does well please consider making a donation =)
