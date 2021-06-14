import click
from nlzss.lzss3 import decompress
import os
from PIL import Image

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
    input = open(input, "rb").read()
    output = open(output, "wb")

    data = decompress(input[4:])
    p_len = int.from_bytes(data[0:4], "little")
    c = 0
    p_colors = []
    while c < p_len*2:
        inf = int.from_bytes(data[c+4:c+6], "big")
        b = inf%2**15//2**10 * 8 
        g = inf%2**10//32 * 8
        r = inf%32 *8
        p_colors.append([r, g, b])
        c += 2
    
    while len(p_colors) < 256:
        p_colors.append([255,255,255])
    outcolors = b''
    for c in range(256):
        outcolors += bytes(p_colors[c])
    Image.frombytes("RGB",[16,16],outcolors).save("palette.png")
    return #TODO: export the other stuff
    data = data[4+c:]
    num_tiles = int.from_bytes(data[:4], "little")

@cli.command()
def create():
    pass