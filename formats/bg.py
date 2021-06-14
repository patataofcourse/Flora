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
        tiles.append(curr_tile)

    # outtiles = [[], [], [], [], [], [], [], []]
    # for tile in tiles:
    #     for n in range(8):
    #         outtiles[n] += tile[n]
    # o = []
    # for h in outtiles:
    #     o+=h
    # p = []
    # for h in p_colors:
    #     p+=h
    # o = bytes(o)
    # print(len(o), num_tiles, 64*num_tiles)
    # img = Image.frombytes("P",(8*num_tiles,8),o)
    # img.putpalette(p)
    # img.save("o.png")

    data = data[4+0x40*num_tiles:]
    width = int.from_bytes(data[:2], "little")
    height = int.from_bytes(data[2:4], "little")
    c = 0
    map = []
    while True:
        if c >= width * height:
            break
        tile = int.from_bytes(data[4+c*2:6+c*2], "little")
        flip_x = bool(tile>>11 & 1)
        flip_y = bool(tile>>10 & 1)
        tile_num = tile & 0x7ff
        if c == 35: print(tile, tile_num, tiles[tile_num])
        map.append((tile_num, flip_x, flip_y))
        c += 1
    
    c = 0
    out = []
    rows = [[],[],[],[],[],[],[],[]]
    for t in map:
        tile = tiles[t[0]]
        if t[2]:
            tile.reverse() #Flip Y
        if t[1]:
            for row in tile:
                row.reverse() #Flip X

        d = 0
        for row in rows:
            rows[d] += tile[d]
            d += 1
        
        c += 1

        if c % width == 0:
            for row in rows:
                out += row
            rows = [[],[],[],[],[],[],[],[]]
    p = []
    for h in p_colors:
        p+=h
    out = bytes(out)
    print(len(out))
    img = Image.frombytes("P",(width*8, height*8),out)
    img.putpalette(p)
    img.save(output)

@cli.command(
                name = "create",
                help = "Makes a texture ARC file from a PNG"
            )
@click.argument("input")
@click.argument("output")
def create(input, output):
    img = Image.open(input)
    output = open(output, "wb")

    palette = list(img.palette.getdata()[1])
    pal = []
    color = []
    for c in range(len(palette)):
        col = palette[c] // 8
        if c % 3 == 2:
            pal.append(color+[col])
            color = []
        else:
            color.append(col)
    print(pal)

    output.write(len(pal).to_bytes(4,"little"))
    for color in pal:
        val = 0
        val += color[2]<<10
        val += color[1]<<5
        val += color[0]
        output.write(val.to_bytes(2, "little"))

    output.close()