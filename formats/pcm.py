import click
from ndspy import lz10
import os

@click.group(help="Archive/pack format, used to store text files.",options_metavar='')
def cli():
    pass

class PCM:
    def __init__(self, file):
        h_size = int.from_bytes(file[:4], "little")
        self.header = {
            "header_size": h_size,
            "file_size": int.from_bytes(file[4:8], "little"),
            "num_files": int.from_bytes(file[8:12], "little"),
            "magic": file[12:16]
        }
        
        if self.header["magic"] != b"LPCK":
            raise Exception("Not a valid PCM file!")
        if h_size != 0x10:
            ans = input(f"This PCM file seems to use nonstandard attributes (header_size={h_size})\nDo you wish to continue reading the file? (y/N)")
            if ans.lower() != "y":
                print("Aborting.")
                quit()

        self.file = file[:self.header['file_size']]
        
        offset = self.header["header_size"]
        self.offsets = {}
        while offset < self.header["file_size"]:
            h_size_ = int.from_bytes(self.file[offset:offset+4],"little")
            f_head = {
                "header_size": h_size_,
                "file_size": int.from_bytes(self.file[offset+4:offset+8], "little"),
                "reserved": int.from_bytes(self.file[offset+8:offset+12], "little"),
                "data_size": int.from_bytes(self.file[offset+12:offset+16], "little"),
                "name": self.file[offset+16:offset+h_size_].decode("ascii").strip("\x00")
            }
            if h_size_ != 0x20:
                ans = input(f"File {f_head['name']} seems to use nonstandard attributes (header_size={h_size_})\nDo you wish to continue reading the file? (y/N)")
                if ans.lower() != "y":
                    print("Aborting.")
                    quit()
            if f_head['reserved'] != 0x00:
                ans = input(f"File {f_head['name']} seems to use nonstandard attributes (reserved={f_head['reserved']})\nDo you wish to continue reading the file? (y/N)")
                if ans.lower() != "y":
                    print("Aborting.")
                    quit()
            if f_head["file_size"] % 0x10 != 0:
                print(f"Warning: file {f_head['name']} seems to have improper padding.")
            self.offsets[f_head["name"]] = offset
            offset += f_head["file_size"]
    def open(self, offset):
        h_size = int.from_bytes(self.file[offset:offset+4], "little")
        data_size = int.from_bytes(self.file[offset+12:offset+16], "little")
        return self.file[offset + h_size: offset + h_size + data_size]
    def __getitem__(self, x):
        return self.open(self.offsets[x])

def from_files(files, names):
    pass

PCM.from_files = from_files

@cli.command(
                name = "extract",
                help = "Extracts the contents of a PCM file into a directory.",
                no_args_is_help = True,
                options_metavar = "[options]"
            )
@click.argument("input")
@click.argument("output")
@click.option("--file", "-f", metavar="FILENAME", multiple=True, help="If used, extracts only the file(s) specified. Can be used multiple times, one per file.")
def extract(input, output, file):
    input = open(input, "rb").read()
    os.mkdir(output)

    input = lz10.decompress(input)
    pcm = PCM(input)
    for f in pcm.offsets:
        if file != [] and f not in file:
            continue
        fw = open(f"{output}/{f}", "wb")
        fw.write(pcm[f])
        fw.close

@cli.command(
                name = "create",
                help = "Creates a PCM file from the contents of a directory.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def create(input, output):
    pass

@cli.command(
                name = "replace",
                help = "Replaces specific files inside a PCM.",
                no_args_is_help = True
            )
@click.argument("in_file")
@click.argument("in_dir")
@click.argument("output")
def replace(in_file, in_dir, output):
    pass