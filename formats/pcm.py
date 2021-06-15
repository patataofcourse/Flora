import click

@click.group(help="Archive/pack format used to store text",options_metavar='')
def cli():
    pass

@cli.command(
                name = "extract",
                help = "Extracts the contents of a PCM file into a directory"
            )
@click.argument("input")
@click.argument("output")
def extract(input, output):
    pass

@cli.command(
                name = "create",
                help = "Creates a PCM file from the contents of a directory"
            )
@click.argument("input")
@click.argument("output")
def create(input, output):
    pass

@cli.command(
                name = "replace",
                help = "Replaces specific files inside a PCM"
            )
@click.argument("in_file")
@click.argument("in_dir")
@click.argument("output")
def replace(in_file, in_dir, output):
    pass