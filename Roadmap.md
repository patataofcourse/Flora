# Flora roadmap
- [x] 0.1
    - Pack and unpack GDS files
- [x] 0.2
    - Extract BG files to PNG and create BG files from indexed PNGs
- [x] 0.3
    - Extract the contents of a PCM file into a folder and make a PCM file from the contents of a folder
- [x] 0.4
    - Replace files inside a PCM file with those given in a folder
    - Extract <s>and import</s> files specific to a certain puzzle, for ease of puzzle editing
        + (Importing will be added to mod files on 0.5)
- [ ] 0.5
    - Make classes for BG and GDS files, so that they can be used in other commands
    - GDS overhaul
        + Make it read to and from JSON instead of GDA
        + Add proper command names
- [ ] 0.6
    - Flora mod files: Create and load mods based on the files that they edit, so that multiple mods can be loaded at the same time if they are compatible.
    - Flora Patcher: a standalone program for creating, updating, and loading Flora mod files
    - First release as executable
- [ ] 1.0
    - Extract all data related to a puzzle to formats such as JSON, PNG, etc. for ease of editing, and later on load as a Flora mod. Includes simplifying the script into a format that can easily be understood.
    - Flora mod file support for puzzles
    - ANI file support (extract the images as PNGs and the animation data into a JSON)