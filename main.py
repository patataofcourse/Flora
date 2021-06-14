import click

import formats
from version import v

@click.group(name=f"flora")
def cli():
    pass

cli.add_command(formats.gds.cli, "gds")

@cli.group(name="arc", help="Texture/animation file converter", )
def arc():
    pass

arc.add_command(formats.bg.cli, "bg")

if __name__ == "__main__":
    cli()