# Flora
## A modding tool for Professor Layton games

### Supported games
* Professssor Layton and the Curious Village: EU

### Current utilities
* GDS script extracting and repacking to a custom readable format - Parameter types 1-3 only
* Exporting BG (background/single texture) ARC files to PNG, and creating them from PNGs
    + Currently, not all PNG files work
    + The image must have at most 256 different colors.

### Requirements
* Python 3
* [click](https://pypi.org/project/click/)
* [pillow](https://pypi.org/project/pillow/)
* [ndspy](https://pypi.org/project/ndspy/)
To install all modules, use `pip install click pillow ndspy` / `py -m pip install click pillow ndspy`

### Special thanks to:
* [pleonex](https://github.com/pleonex/) for his tool [Tinke](https://github.com/pleonex/Tinke), which gave a base for documentation
* Villa for dealing with my bullshit (srry) and cheering me on!