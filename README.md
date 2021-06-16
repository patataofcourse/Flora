# <img src="flora.png" width=28> Flora
## A modding tool for Professor Layton games

### Supported games
* Professor Layton and the Curious Village (only tested in the EU version)

### Current utilities
* GDS script extracting and repacking to a custom readable format.
    + Currently, the parameters supported are those of types 1 (int), 2 (double int) and 3 (string). Since some scripts use other parameter types, this will be fixed in the future.
* Exporting BG ARC files to PNG, and creating them from PNGs.
    + Currently, the PNG's color mode must be set to indexed. This will be changed in future versions.
    + The image must have at most 256 different colors. This is a limitation of the format.
* Extracting the contents of a PCM file into a folder, and building a PCM file from the contents of a folder.

### Usage
Flora is a CLI tool, which means that it must be ran from a command line (cmd/bash).<br>
Go to Flora's main directory and use `python main.py` to see all available commands.

### Objectives
Currently, Flora development is focused on simplifiying puzzle editing, making it possibly a one-step process. After that goal is achieved, Flora 1.0 will be released, and focus will shift to a different goal (notably, editing the actual main game).

### Requirements
* Python 3
* [click](https://pypi.org/project/click/)
* [pillow](https://pypi.org/project/pillow/)
* [ndspy](https://pypi.org/project/ndspy/)

To install all modules, use:  `pip install click pillow ndspy` &nbsp;/ &nbsp;`py -m pip install click pillow ndspy`

### Special thanks to:
* [pleonex](https://github.com/pleonex/) for his tool [Tinke](https://github.com/pleonex/Tinke), which gave me a base for file formats
* Villa for dealing with my bullshit (srry) and cheering me on!