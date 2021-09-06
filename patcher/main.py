import click
import os

from patcher.version import v

@click.group(name=f"flora-patch")
def cli():
    pass

def main():
    print(f"Flora Patcher version {v} by patataofcourse\n")
    cli() #TODO: managing exceptions, -v