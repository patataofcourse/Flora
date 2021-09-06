import click
from pypreprocessor import pypreprocessor

from version import v

@click.group(name=f"flora-patch")
def cli():
    pass

if __name__ == "__main__":
    print(f"Flora Patcher version {v} by patataofcourse\n")
    pypreprocessor.parse()
    cli() #TODO: managing exceptions, -v