import click
from ndspy import lz10
import os

@click.group(help="Archive/pack format, used to store text files.",options_metavar='')
def cli():
    pass

class PCM:
    def __init__(self, file, names=None):
        if names != None:
            file = self.from_files(file, names)
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
        self.calc_offsets()
    def calc_offsets(self):
        offset = self.header["header_size"]
        self.offsets = {}
        while offset < self.header["file_size"]:
            h_size = int.from_bytes(self.file[offset:offset+4],"little")
            f_head = {
                "header_size": h_size,
                "file_size": int.from_bytes(self.file[offset+4:offset+8], "little"),
                "reserved": int.from_bytes(self.file[offset+8:offset+12], "little"),
                "data_size": int.from_bytes(self.file[offset+12:offset+16], "little"),
                "name": self.file[offset+16:offset+h_size].decode("ascii").strip("\x00")
            }
            if h_size != 0x20:
                ans = input(f"File {f_head['name']} seems to use nonstandard attributes (header_size={h_size})\nDo you wish to continue reading the file? (y/N)")
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
    
    def from_files(self, files, names):
        self.header = {
            "header_size": 0x10,
            "file_size": 0,
            "num_files": len(files),
            "magic": b"LPCK"
        }
        body = b''
        c = 0
        for file in files:
            name = names[c]
            if len(name) > 16:
                raise Exception("File names longer than 16 characters (including extension) are not supported.")
            padding = 16 - (len(file)%16)
            if padding == 16:
                padding = 0
            header = {
                "header_size": 0x20,
                "file_size": 0x20 + len(file) + padding,
                "reserved": 0,
                "data_size": len(file),
                "name": name.encode("ASCII") + b"\x00" * (16 - len(name))
            }
            body += header['header_size'].to_bytes(4, "little")
            body += header['file_size'].to_bytes(4, "little")
            body += header['reserved'].to_bytes(4, "little")
            body += header['data_size'].to_bytes(4, "little")
            body += header['name']
            body += file + b"\x00" * padding
            c += 1
        head = b''
        head += 0x10.to_bytes(4, "little")
        head += (0x10 + len(body)).to_bytes(4, "little")
        head += len(files).to_bytes(4, "little")
        head += b"LPCK"
        out = head + body
        return out

    def replace(self, name, content):
        offset = self.offsets.get(name, None)
        if offset == None:
            raise Exception(f"File {name} doesn't exist inside PCM!")
        end = offset + int.from_bytes(self.file[offset+4:offset+8], "little")
        
        file = b""
        padding = 16 - (len(content)%16)
        if padding == 16:
            padding = 0
        header = {
            "header_size": 0x20,
            "file_size": 0x20 + len(content) + padding,
            "reserved": 0,
            "data_size": len(content),
            "name": name.encode("ASCII") + b"\x00" * (16 - len(name))
        }
        file += header['header_size'].to_bytes(4, "little")
        file += header['file_size'].to_bytes(4, "little")
        file += header['reserved'].to_bytes(4, "little")
        file += header['data_size'].to_bytes(4, "little")
        file += header['name']
        file += content + b"\x00" * padding

        self.file = self.file[:offset] + file + self.file[end:]
        filelen = len(self.file)
        self.file = self.file[:4] + filelen.to_bytes(4, "little") + self.file[8:]
        self.header['file_size'] = filelen

        self.calc_offsets()

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
    try:
        os.mkdir(output)
    except FileExistsError:
        print(f"Directory {output} already exists! Delete it, then try again.")
        quit()

    input = lz10.decompress(input)
    pcm = PCM(input)
    for f in pcm.offsets:
        if file != () and f not in file:
            continue
        fw = open(f"{output}/{f}", "wb")
        fw.write(pcm[f])
        fw.close()

@cli.command(
                name = "create",
                help = "Creates a PCM file from the contents of a directory.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def create(input, output):
    if not os.path.isdir(input):
        raise Exception("Directory does not exist!")
    output = open(output, "wb")
    
    files = []
    names = []
    for f in list(os.walk("./"+input))[0][2]:
        names.append(f)
        files.append(open(f"{input}/{f}", "rb").read())
    pcm = PCM(files, names)

    out = lz10.compress(pcm.file)
    output.write(out)
    output.close()

@cli.command(
                name = "replace",
                help = "Replaces specific files inside a PCM.",
                no_args_is_help = True
            )#TODO: check if help in arguments is a thing
@click.argument("in_file")#, help="The PCM file to replace files of.")
@click.argument("in_dir")#, help="The directory from which to get the replaced files.")
@click.argument("output")#, help="Location for the output PCM file.")
def replace(in_file, in_dir, output):
    in_file = open(in_file, "rb").read()
    if not os.path.isdir(in_dir):
        raise Exception("Directory does not exist!")
    output = open(output, "wb")

    in_file = lz10.decompress(in_file)
    pcm = PCM(in_file)

    for f in list(os.walk("./"+in_dir))[0][2]:
        pcm.replace(f, open(f"{in_dir}/{f}", "rb").read())
        
    out = lz10.compress(pcm.file)
    output.write(out)
    output.close()