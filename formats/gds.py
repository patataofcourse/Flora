import click
import json
import os

from formats import gds_old
from version import v

@click.group(help="Script-like format, also used to store puzzle parameters.",options_metavar='')
def cli():
    pass

cli.add_command(gds_old.unpack)
cli.add_command(gds_old.pack)

dir_path = "/".join(os.path.dirname(os.path.realpath(__file__).replace("\\", "/")).split("/")[:-1])
commands = json.load(open(f"{dir_path}/data/commands.json", encoding="utf-8"))
commands_i = {val: key for key, val in commands.items()}

class GDSModeException (Exception):
    def __init__(self, mode):
        self.args = (f"'{mode}' is not a valid mode for GDS.__init__(): must be one of 'bin', 'json', 'gda'",)

class GDS:
    def __init__(self, file, mode="bin"): #modes: "bin"/"b", "json"/"j", "gda"/"a"
        if mode == "bin":
            self.from_gds(file)
        elif mode == "json":
            self.from_json(file)
        elif mode == "gda":
            self.from_old(file)
        else:
            raise GDSModeException(mode)

    def from_gds(self, file):
        length = int.from_bytes(file[0:4], "little")
        if file[4:6] == b"\x0c\x00":
            self.cmds = []
            return
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
        
        self.cmds = cmds
    
    def from_json (self, file):
        self.cmds = json.loads(file)["data"]
        #TODO: reject non-compatible json files
    
    def __getitem__ (self, index):
        index = int(index)
        return self.cmds[index]
    
    def to_json (self):
        return json.dumps({"version": v, "data": self.cmds}, indent=4)
    
    def to_gds (self):
        out = b"\x00" * 2
        for command in self.cmds:
            if type(command["command"]) == int:
                out += command["command"].to_bytes(2, "little")
            else:
                out += commands[command["command"]].to_bytes(2, "little")
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

@cli.command(
                name="extract",
                help="Converts a GDS script to JSON.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def unpack_json(input, output):
    input = open(input, "rb").read()
    output = open(output, "w")
    gds = GDS(input)
    output.write(gds.to_json())
    output.close()

@cli.command(
                name="create",
                help="Converts a JSON to GDS.",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
def create_json(input, output):
    input = open(input).read()
    output = open(output, "wb")

    gds = GDS(input, "json")
    output.write(gds.to_bin())
    output.close()