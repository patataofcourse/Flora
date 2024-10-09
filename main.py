import click

import formats
import version

CONTEXT_SETTINGS = dict(help_option_names = ['--help', '-h', '-?'])

@click.group(name="flora", context_settings=CONTEXT_SETTINGS)
@click.version_option(version.__version__, '--version', '-v', prog_name="flora", message=f"Flora v{version.__version__} by patataofcourse")
def cli():
    pass

cli.add_command(formats.gds.cli, "gds")
cli.add_command(formats.bg.cli, "bg")
cli.add_command(formats.pcm.cli, "pcm")
cli.add_command(formats.puzzle.cli, "puzzle")

if __name__ == "__main__":
    cli() #TODO: managing exceptions