import click

import formats
from version import v

@click.group(name=f"flora")
def cli():
    pass

cli.add_command(formats.gds.cli, "gds")
cli.add_command(formats.bg.cli, "bg")
cli.add_command(formats.pcm.cli, "pcm")

if __name__ == "__main__":
    print(f"Flora v{v} by patataofcourse\n")
    cli() #TODO: managing exceptions, -v