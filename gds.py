import binascii
from version import v

def unpack(file, outfile):
    file = open(file, "rb").read()
    outfile = open(outfile, "w")

    length = int.from_bytes(file[0:4], "little")
    cmd_data = file[6:length+4]
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
            elif cmd == 0x1b:
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

    outfile.write(out.strip())

def pack(file, outfile):
    file = open(file).read().split("\n")
    outfile = open(outfile, "wb")

    length = 0
    out = b''

    for line in file:
        line = line.split(" ")
        out += b'\x00\x00'


for f in range(163):
    print(f)
    unpack(f"CV_out/data/qscript/q{f}_param.gds", f"CV_out/data/script/qscript/q{f}_param.gdo")