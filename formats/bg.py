import click
from nlzss.lzss3 import decompress
from nlzss.compress import compress
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

    data = decompress(input[4:])
    p_len = int.from_bytes(data[0:4], "little")
    c = 0
    p_colors = []
    while c < p_len*2:
        inf = int.from_bytes(data[c+4:c+6], "little")
        b = (inf>>10 & 0x1f) * 8
        g = (inf>>5 & 0x1f) * 8
        r = (inf & 0x1f) * 8
        p_colors.append([r, g, b])
        c += 2

    data = data[4+c:]

    while len(p_colors) < 256:
        p_colors.append([255,255,255])
    outcolors = b''
    for c in range(256):
        outcolors += bytes(p_colors[c])
    Image.frombytes("RGB",[16,16],outcolors).save("palette.png")

    num_tiles = int.from_bytes(data[:4], "little")
    tiles = []
    for tile in range(num_tiles):
        curr_tile = []
        for row in range(8):
            curr_row = []
            pos = 4+tile*0x40+row*8
            for pixel in data[pos:pos+8]:
                curr_row.append(pixel)
            curr_tile.append(curr_row)

@cli.command()
def create():
    pass