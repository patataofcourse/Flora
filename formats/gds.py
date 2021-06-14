import binascii
import click

from func import remove_strings
from version import v

@click.group(help="GDS file converter",options_metavar='')
def cli():
    pass

@cli.command(
                name="unpack",
                help="converts a GDS script to a readable format",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
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
            raise Exception("End of file reached with no C0 command!")
        if cmd == None:
            cmd = int.from_bytes(cmd_data[c:c+2], "little")
            c += 2
            continue
        p_type = int.from_bytes(cmd_data[c:c+2], "little")
        if p_type == 0:
            if cmd == None:
                raise Exception("uh what")
            elif cmd == 0x1b: #TODO: automate hex <-> words
                cmd = "engine"
            elif cmd == 0x1f:
                cmd = "img_win"
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

@cli.command(
                name="pack",
                help="creates a GDS file from a readable script",
                no_args_is_help = True
            )
@click.argument("input")
@click.argument("output")
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
            cmd = bytearray.fromhex(cmd[2:])
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