import click
from ndspy import rom

@click.group(help="Simplify puzzle editing: extract or import the files related to a certain puzzle.",options_metavar='')
def cli():
    pass

@cli.command(
                name="extract",
                help="Extracts all the files related to a certain puzzle from the ROM into a specific directory",
                no_args_is_help = True
            )
@click.argument("rom")
@click.argument("puzzle")
@click.argument("out_dir")
def extract(rom, puzzle, out_dir):
    # check it's a Layton ROM
    # check it's a CV ROM
    # warning if not EU
    # extract all files related to the puzzle into out_dir
    pass