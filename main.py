import click

import formats
from patcher import main as patcher
from version import v

@click.group(name=f"flora")
def cli():
    pass

cli.add_command(formats.gds.cli, "gds")
cli.add_command(formats.bg.cli, "bg")
cli.add_command(formats.pcm.cli, "pcm")
cli.add_command(formats.puzzle.cli, "puzzle")
patcher.cli.help = "Use Flora Patcher."
cli.add_command(patcher.cli, "patch")

if __name__ == "__main__":
    print(f"Flora v{v} by patataofcourse\n")
    cli() #TODO: managing exceptions, -v