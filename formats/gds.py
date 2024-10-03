import click
import json
import os

import parse
import ast
from utils import cli_file_pairs, foreach_file_pair
from version import v

@click.group(help="Script-like format, also used to store puzzle parameters.",options_metavar='')
def cli():
    pass

dir_path = "/".join(os.path.dirname(os.path.realpath(__file__).replace("\\", "/")).split("/")[:-1])
commands = json.load(open(f"{dir_path}/data/commands.json", encoding="utf-8"))
commands_i = {val["id"]: key for key, val in commands.items() if "id" in val} # Inverted version of commands

class GDS:
    def __init__(self, cmds = []): #modes: "bin"/"b", "json"/"j", "gda"/"a"
        self.cmds = cmds

    @classmethod
    def from_gds(Self, file):
        length = int.from_bytes(file[0:4], "little")
        if file[4:6] == b"\x0c\x00":
            return Self([])
        cmd_data = file[6:length+4]
        cmds = []

        cmd = None
        params = []
        c = 0
        while True:
            if c >= length:
                raise Exception("GDS file error: End of file reached with no 0xC command!")
            if cmd == None:
                cmd = int.from_bytes(cmd_data[c:c+2], "little")
                if cmd in commands_i:
                    cmd = commands_i[cmd]
                c += 2
                continue

            p_type = int.from_bytes(cmd_data[c:c+2], "little")
            
            if p_type == 0:
                cmds.append({"command":cmd, "parameters":params})
                cmd = None
                params = []
                c += 2
            elif p_type == 1:
                params.append({"type": "int", "data": int.from_bytes(cmd_data[c+2:c+6], "little")})
                c += 6
            elif p_type == 2:
                params.append({"type": "unknown-2", "data": int.from_bytes(cmd_data[c+2:c+6], "little")})
                c += 6
            elif p_type == 3:
                str_len = int.from_bytes(cmd_data[c+2:c+4], "little")
                params.append({"type": "string", "data": cmd_data[c+4:c+4+str_len].decode("ascii").rstrip("\x00")})  #TODO: JP/KO compatibility
                c += str_len+4
            elif p_type == 6:
                params.append({"type": "unknown-6", "data": int.from_bytes(cmd_data[c+2:c+6], "little")})
                c += 6
            elif p_type == 7:
                params.append({"type": "unknown-7", "data": int.from_bytes(cmd_data[c+2:c+6], "little")})
                c += 6
            elif p_type == 8:
                params.append({"type": "unknown-8"})
                c += 2
            elif p_type == 9:
                params.append({"type": "unknown-9"})
                c += 2
            elif p_type == 0xb:
                params.append({"type": "unknown-b"})
                c += 2
            elif p_type == 0xc:
                #cmd = hex(cmd)
                cmds.append({"command":cmd, "parameters":params})
                break
            else:
                raise Exception(f"GDS file error: Invalid or unsupported parameter type {hex(p_type)}!")
        
        return Self(cmds)
    
    @classmethod
    def from_json (Self, file):
        cmds = json.loads(file)
        #TODO: reject non-compatible json files
        return Self(cmds)
    
    @classmethod
    def from_gda (Self, file): #TODO: make this, so gds_old can be completely removed
        cmds = []
        
        for line in file.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if line == '':
                continue

            data = {}

            line, strings = parse.remove_strings(line)
            line = line.rstrip().split(" ")
            cmd = line[0]

            # TODO: handle inline comments, maybe

            if cmd in commands:
                cmd = commands[cmd]
                if "alias" in cmd:
                    cmd = commands[cmd["alias"]]
            elif cmd.startswith("cmd_"):
                cmd = int(cmd[4:])
            elif cmd.startswith("0x"):
                cmd = int(cmd[2:], base=16)
            else:
                raise Exception(f"Unknown GDA command: {cmd}")
            
            params = []

            for param in line[1:]:
                if param.isdigit():
                    params.append({"type":"int", "data":int(param)})
                elif param.startswith("0x"):
                    params.append({"type":"unknown-2", "data":int(param[2:], 16)})
                elif param.startswith('"') and param.endswith('"'):
                    param = ast.literal_eval(f'"{strings[int(param[1:-1])]}"')
                    params.append({"type":"string", "data":param})
                elif param.startswith("!6("):
                    params.append({"type":"unknown-6", "data":int(param[3:-1], 16)})
                elif param.startswith("!7("):
                    params.append({"type":"unknown-7", "data":int(param[3:-1], 16)})
                elif param.startswith("!8"):
                    params.append({"type":"unknown-8"})
                elif param.startswith("!9"):
                    params.append({"type":"unknown-9"})
                elif param.startswith("!b"):
                    params.append({"type":"unknown-b"})
                else:
                    raise Exception(f"Invalid GDA parameter: {param}")
            
            cmds.append({"command":cmd, "parameters":params})

        return Self(cmds)

    def __getitem__ (self, index):
        index = int(index)
        return self.cmds[index]
    
    def to_json (self):
        return json.dumps({"version": v, "data": self.cmds}, indent=4)
    
    def to_gds (self):
        out = b"\x00" * 2
        for command in self.cmds:
            if type(command["command"]["id"]) == int:
                out += command["command"]["id"].to_bytes(2, "little")
            else:
                out += commands[command["command"]["id"]].to_bytes(2, "little")
            for param in command["parameters"]:
                if param["type"] == "int":
                    out += b"\x01\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "unknown-2":
                    out += b"\x02\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "string":
                    out += b"\x03\x00"
                    out += (len(param["data"])+1).to_bytes(2, "little")
                    out += param["data"].encode("ASCII") + b"\x00" #TODO: JP/KO compatibility
                elif param["type"] == "unknown-6":
                    out += b"\x06\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "unknown-7":
                    out += b"\x07\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "unknown-8":
                    out += b"\x08\x00"
                elif param["type"] == "unknown-9":
                    out += b"\x09\x00"
                elif param["type"] == "unknown-b":
                    out += b"\x0b\x00"
                else:
                    raise Exception(f"GDS JSON error: Invalid or unsupported parameter type '{param['type']}'!")
            out += b"\x00\x00"
        out = out[:-2] + b"\x0c\x00"

        return len(out).to_bytes(4, "little") + out
    
    def to_bin (self): #alias
        return self.to_gds()
    
    def to_gda(self):
        out = ""
        for command in self.cmds:
            if type(command["command"]) == int:
                out += "0x"+command["command"].to_bytes(1, "little").hex()
            else:
                out += command['command']
            for param in command["parameters"]:
                out += " "
                if param["type"] == "int":
                    out += str(param["data"])
                elif param["type"] == "string":
                    out += repr(param["data"])
                elif param["type"] == "unknown-2":
                    out += hex(param["data"])
                elif param["type"] == "unknown-6":
                    b = param["data"].to_bytes(4, "little")
                    out += f"!6({b.hex()})"
                elif param["type"] == "unknown-7":
                    b = param["data"].to_bytes(4, "little")
                    out += f"!7({b.hex()})"
                elif param["type"] == "unknown-8":
                    out += "!8"
                elif param["type"] == "unknown-9":
                    out += "!9"
                elif param["type"] == "unknown-b":
                    out += "!b"
                else:
                    raise Exception(f"GDA error: invalid or unsupported parameter type '{param['type']}'!")
            out += "\n"
        return out

@cli.command(
                name="extract",
                no_args_is_help = False
            )
@click.argument("input", required=False, type=click.Path(exists=True))
@click.argument("output", required=False, type=click.Path(exists=False))
@click.option("--recursive", "-r", is_flag=True, help="Recurse into subdirectories of the input directory to find more applicable files.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output. By default, operations involving multiple files will show a progressbar.")
def unpack_json(input = None, output = None, recursive = False, quiet = False):
    """
    Converts the GDS script(s) at INPUT to JSON files at OUTPUT.

    INPUT can be a single file or a directory (which obviously has to exist). In the latter case subfiles with the correct file ending will be processed.
    If unset, defaults to the current working directory.

    The meaning of OUTPUT may depend on INPUT:
    - If INPUT is a file, then OUTPUT is expected to be a file, unless it explicitly ends with a slash indicating a directory.
      In this case, if unset OUTPUT will default to the INPUT filename with `.json` exchanged/appended.
    - Otherwise OUTPUT has to be a directory as well (or an error will be shown).
      In this case, if unset OUTPUT will default to the INPUT directory (which may itself default to the current working directory).

    In the file-to-file case, the paths are explicitly used as they are. Otherwise, if multiple input files were collected, or OUTPUT is a directory,
    an output path is inferred for each input file by exchanging the `.gds` file ending for `.json`, or otherwise appending the `.json` file ending.
    """
    def process(input, output):
        input = open(input, "rb").read()
        output = open(output, "w", encoding="utf-8")
        gds = GDS(input)
        output.write(gds.to_json())
        output.close()

    pairs = cli_file_pairs(input, output, in_ending=".gds", out_ending=".json", recursive=recursive)
    foreach_file_pair(pairs, process, quiet=quiet)


@cli.command(
                name="compilejson",
                help="Converts a JSON document created by 'compilejson' to a GDS script file.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def create_json(input, output):
    input = open(input, encoding="utf-8").read()
    output = open(output, "wb")

    gds = GDS.from_json(input)
    output.write(gds.to_bin())
    output.close()

@cli.command(
                name="compile",
                help="Generates a GDS binary script file from human-readable GDA files.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def create_from_gda(input, output):
    input = open(input, encoding="utf-8").read()
    output = open(output, "wb")

    gds = GDS.from_gda(input)
    output.write(gds.to_bin())
    output.close()

@cli.command(
                name="decompile",
                help="Converts a GDS file into a human-readable GDA script format.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output", required=False)
def create_to_gda(input, output = None):
    if output is None:
        output = input
        if output.lower().endswith(".gds"):
            output = output[:-4]
        output = output + ".gda"
    
    input = open(input, "rb").read()
    output = open(output, "w", encoding="utf-8")
    gds = GDS.from_gds(input)
    output.write(gds.to_gda())
    output.close()
