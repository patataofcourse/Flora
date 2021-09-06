import click
from version import v

@click.group(name=f"flora-patch")
def cli():

if __name__ == "__main__":
    print(f"Flora Patcher v{v} by patataofcourse\n")
    cli() #TODO: managing exceptions, -v