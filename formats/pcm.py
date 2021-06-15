import click
from ndspy import lz10

@click.group(help="Archive/pack format used to store text",options_metavar='')
def cli():
    pass

class PCM:
    def __init__(self, file):
        h_size = int.from_bytes(file[:4], "little")
        self.header = {
            "header_size": h_size,
            "file_size": int.from_bytes(file[4:8]),
            "num_files": int.from_bytes(file[8:12]),
            "magic": file[12:16]
        }
        if self.header["magic"] != b"LPCK":
            raise Exception("Not a valid PCM file!")
        if h_size != 0x10:
            ans = input(f"This file seems to use nonstandard attributes (header_size={h_size})\nDo you wish to continue reading the file? (y/N)")
            if ans.lower() != "y":
                print("Aborting.")
                quit()
        self.file = file[self.header:file_size]
        #parse header, get first offset
        #while offset < file_size:
        #   offsets[name] = offset
        #   offset += size
    def open(self, offset):
        h_size = int.from_bytes(self.file[offset:offset+4], "little")
        header = {
            "header_size": h_size,
            "file_size": int.from_bytes(self.file[offset+4:offset+8], "little"),
            "unknown": int.from_bytes(self.file[offset+8:offset+12], "little"),
            "data_size": int.from_bytes(self.file[offset+12:offset+16], "little"),
            "name": self.file[offset+16:offset+h_size].strip("\x00").decode("ascii")
        }
    def __getitem__(self, x):
        return self.open(self.offsets[x])

def from_files(files, names):
    pass

PCM.from_files = from_files

@cli.command(
                name = "extract",
                help = "Extracts the contents of a PCM file into a directory"
            )
@click.argument("input")
@click.argument("output")
@click.option("-f", "--file", prompt="FILENAME", multiple=True, help="If used, extracts only the file(s) specified. Can be used multiple times, one per file.")
def extract(input, output, file):
    input = open(input, "rb").read()
    output = open(output, "wb")

    input = lz10.decompress(input)
    output.write(input)
    output.close()

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