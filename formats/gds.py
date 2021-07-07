import binascii
import click
import json

from func import remove_strings
from version import v

@click.group(help="Script-like format, also used to store puzzle parameters.",options_metavar='')
def cli():
    pass

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
        self.cmds = json.loads(file)
        print(self.cmds)
        #TODO: reject non-compatible json files
    
    def __getitem__ (self, index):
        index = int(index)
        return self.cmds[index]
    
    def to_json (self):
        return json.dumps({"version": v, "data": self.cmds}, indent=4)

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
def b(input, output):
    input = open(input).read()
    GDS(input, "json")

#@cli.command(
#                name="unpack",
#                help="Converts a GDS script to a readable format.",
#                no_args_is_help = True
#            )
#@click.argument("input")
#@click.argument("output")
def unpack(input, output):
    input = open(input, "rb").read()
    output = open(output, "w")

    length = int.from_bytes(input[0:4], "little")
    cmd_data = input[6:length+4]
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
            if cmd == None:
                raise Exception("uh what")
            # elif cmd == 0x1b: #TODO: automate hex <-> words
            #     cmd = "engine"
            # elif cmd == 0x1f:
            #     cmd = "img_win"
            else:
                cmd = hex(cmd)
            cmds.append((cmd, params))
            cmd = None
            params = []
            c += 2
        elif p_type == 1:
            params.append((1, int.from_bytes(cmd_data[c+2:c+6], "little")))
            c += 6
        elif p_type == 2:
            params.append((2, cmd_data[c+2:c+6]))
            c += 6
        elif p_type == 3:
            str_len = int.from_bytes(cmd_data[c+2:c+4], "little")
            params.append((3, cmd_data[c+4:c+4+str_len].decode("ascii").replace("\x00", "")))
            c += str_len+4
        elif p_type == 0xc:
            if cmd == 0x1b:
                cmd = "engine"
            elif cmd == 0x1f:
                cmd = "img_win"
            else:
                cmd = hex(cmd)
            cmds.append((cmd, params))
            break
        else:
            raise Exception(f"Invalid or unsupported parameter type {hex(p_type)}!")

    out = f"#Exported with Flora v{v}\n"

    for cmd in cmds:
        out += cmd[0]
        for param in cmd[1]:
            out += " "
            if param[0] == 2:
                out += "0x" + binascii.hexlify(param[1]).decode("ascii")
            else:
                out += repr(param[1])
        out += "\n"

    output.write(out.strip())

#@cli.command(
#                name="pack",
#                help="Creates a GDS file from a readable script.",
#                no_args_is_help = True
#            )
#@click.argument("input")
#@click.argument("output")
def pack(input, output):
    input = open(input).read().split("\n")
    output = open(output, "wb")

    out = bytearray(b'\x00\x00')

    for line in input:
        if line.startswith("#") or line == "":
            continue
        
        line, strings = remove_strings(line)
        line = line.split(" ")
        
        cmd = line[0]
        if cmd == "engine": #TODO: automate hex <-> words
            cmd = "0x1b"
        elif cmd == "img_win":
            cmd = "0x1f"
        
        try:
            cmd = bytearray.fromhex(("0" if len(cmd)%2 == 1 else "") + cmd[2:])
        except ValueError:
            raise Exception(f"Invalid command {cmd}")
        cmd.reverse()
        if len(cmd) < 2:
            cmd += b"\x00"
        out += cmd

        for param in line[1:]:
            if param.isdigit():
                out += b"\x01\x00" + int(param).to_bytes(4, "little")
            elif param.startswith("0x"):
                out += b"\x02\x00" + bytes.fromhex(param[2:])
            elif param.startswith('"') and param.endswith('"'):
                param = strings[int(param[1:-1])]
                out += b"\x03\x00" + (len(param) + 1).to_bytes(2, "little") + param.encode("ASCII") + b"\x00"
            else:
                raise Exception(f"Invalid parameter - {param}")
        out += b'\x00\x00'
    out[-2] = 0xc
    
    output.write(len(out).to_bytes(4, "little"))
    output.write(out)
    output.close()