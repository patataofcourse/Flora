import click

@click.group(help="'Background'/texture format",options_metavar='')
def cli():
    pass

@cli.command(
                name = "extract",
                help="Converts a texture ARC file into a PNG"
            )
@click.argument("input")
@click.argument("output")
def extract(input, output):
    pass

@cli.command()
def create():
    pass