# <img src="flora.png" width=28> Flora
## A modding tool for Professor Layton games

### Supported games
* Professor Layton and the Curious Village (all versions: JP, JP Friendly Version, US, EU/AUS, KO)
    + Warning: the only version with guaranteed compatibility is EU/AUS. Please specify the region of your ROM when reporting a bug or opening an issue.

### Current utilities
* GDS script extracting and repacking to a custom readable format.
    + Currently, the parameters supported are those of types 1 (int), 2 (double int) and 3 (string). Since some scripts use other parameter types, this will be fixed in the future.
* Exporting BG ARC files to PNG, and creating them from PNGs.
    + Currently, the PNG's color mode must be set to indexed. This will be changed in future versions.
    + The image must have at most 256 different colors. This is a limitation of the format.
* Extracting the contents of a PCM file into a folder, and building a PCM file from the contents of a folder.
* Replacing certain files inside a PCM file.

For a full roadmap of the features that will be added to Flora in the near future, check out [Roadmap.md](Roadmap.md)

### Usage
Flora is a CLI tool, which means that it must be ran from a command line (cmd/bash).<br>
Go to Flora's main directory and use `python main.py` to see all available commands.

### Objectives
Currently, Flora development is focused on simplifiying puzzle editing, making it possibly a one-step process. After that goal is achieved, Flora 1.0 will be released, and focus will shift to a different goal (notably, editing the actual main game).

### Game titles
British/Australian titles (Pandora's Box / Lost Future / Spectre's Call) will take precedence over American titles (Diabolical Box / Unwound Future / Last Specter) due to the first being the title for all EU versions, only translated to their respective languages (and, not gonna lie, a lil' bit of spite). Exception: the US region versions of said games.

### Puzzles:
To use the puzzle command, you should use either the number of the puzzle (1) if it's a standard puzzle, or the weekly puzzle's EU/AUS number preceded by 'W' (W16). Full support for weekly puzzles exclusive to the US and JP ROMs will arrive at a future update.

You can also extract the match puzzle tutorial (from puzzle #10) using "match_tutorial" and, in the EU and KO versions, the unused puzzle using "1_unused".

Some unused variants of puzzles can't be extracted yet through Flora, as well as some Japanese-exclusive weekly puzzles, however, this will be fixed in a future update.

### Requirements
* Python 3
* [click](https://pypi.org/project/click/)
* [pillow](https://pypi.org/project/pillow/)
* [ndspy](https://pypi.org/project/ndspy/)
* [pypreprocessor](https://pypi.org/project/pypreprocessor/)

To install all modules, use: `pip install click pillow ndspy` &nbsp;/ &nbsp;`py -m pip install click pillow ndspy pypreprocessor`

### Special thanks to:
* [pleonex](https://github.com/pleonex/) for his tool [Tinke](https://github.com/pleonex/Tinke), which gave me a base for file formats
* [Professor Layton and the Curious Village Walkthrough](http://professorlaytonwalkthrough.blogspot.com), a Blogger guide for this game that supplied an accurate puzzle list for both the US and the EU/AUS versions.
* Duel for dealing with my bullshit (srry) and cheering me on!