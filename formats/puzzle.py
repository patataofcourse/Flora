import click
import json
from ndspy import rom

@click.group(help="Simplify puzzle editing: extract or import the files related to a certain puzzle.",options_metavar='')
def cli():
    pass

@cli.command(
                name="extract",
                help="Extracts all the files related to a certain puzzle from the ROM into a specific directory",
                no_args_is_help = True
            )
@click.argument("romfile")
@click.argument("puzzle")
@click.argument("out_dir")
@click.option("--long", is_flag=True, default = False)
def extract(romfile, puzzle, out_dir, long):
    print("Loading ROM...")
    romfile = rom.NintendoDSRom.fromFile(romfile)
    print("ROM loaded!")
    
    id = romfile.idCode.decode("ASCII")
    if id not in titles.roms:
        print(f"Game supplied ({id}) is not a Professor Layton DS game!")
        quit()
    title = ""
    if long:
        title = titles.roms_long[id]
    else:
        title = titles.roms[id]
    print(f"Game: {title}")
    
    if id not in titles.supported_roms:
        print("Currently, this game is not supported by Flora!")
        quit()
    elif "" not in titles.tested_roms:
        print("Warning: this game has not been tested properly with Flora, so errors may arise.")
        ans = input("Continue? (y/N) ")
        if ans.lower() != "y":
            quit()
    print("a")
    # extract all files related to the puzzle into out_dir
    pass