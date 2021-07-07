import click
import json

from formats import gds_old
from version import v

@click.group(help="Script-like format, also used to store puzzle parameters.",options_metavar='')
def cli():
    pass

cli.add_command(gds_old.unpack)
cli.add_command(gds_old.pack)

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
        cmd_data = file[6:length+4]
        cmds = []

        cmd = None
        params = []
        c = 0
        while True:
            if c >= length:
                raise Exception("End of file reached with no 0xC command!")
            if cmd == None:
                cmd = int.from_bytes(cmd_data[c:c+2], "little")
                c += 2
                continue
            p_type = int.from_bytes(cmd_data[c:c+2], "little")
            if p_type == 0:
                #cmd = hex(cmd)
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
                params.append({"type": "string", "data": cmd_data[c+4:c+4+str_len].decode("ascii").rstrip("\x00")})
                c += str_len+4
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
        out = b""
        for command in self.cmds:
            print(command["command"])
    
    def to_bin (self): #alias
        return to_gds (self)

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
    GDS(input, "json")