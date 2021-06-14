import click

import formats
from version import v

@click.group(name=f"Flora CLI v{v}")
def cli():
    pass

cli.add_command(formats.gds.cli, "gds")

if __name__ == "__main__":
    cli()