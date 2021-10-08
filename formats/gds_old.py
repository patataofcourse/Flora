import click

from version import v

def remove_strings(text): #wow i actually commented this very cool
    #get the start and end of every string
    quotepos = [] #here we'll store the index of every quote that's not been escaped
    for quote in ("'", "\""):
        allpos = [i for i in range(len(text)) if text.startswith(quote, i)] #gets all instances of each type of quotes
        for index in allpos:
            if text[index-1] != "\\":
                quotepos.append(index) #only pass to quotepos the strings that weren't escaped
    opened_quote = ""
    quotes = []
    for index in sorted(quotepos):
        if opened_quote == "": #no open quotes
            opened_quote = text[index]
            quotes.append(index)
        elif opened_quote == text[index]:       #current quote is the same as the open quote -> it closes, and
            quotes[-1] = (quotes[-1], index)    #otherwise it just gets ignored and treated as any other character
            opened_quote = ""
    if opened_quote != "":
        return None, None
    #now, replace them with things that won't be screwed up by the rest of input_format
    quotes.reverse() #this way the index numbers don't get fucked up
    c = 1
    quotetext = []
    for quote in quotes:
        quotetext = [text[quote[0]+1:quote[1]]] + quotetext
        text = text[:quote[0]] + f'"{len(quotes)-c}"' + text[quote[1]+1:] #"0", "1", etc.
        c += 1
    outquotes = [i.replace("\\'", "'").replace('\\"', '"') for i in quotetext] #gets all instances of each type of quotes
    return text, outquotes

@click.command(
                name="extract_gda",
                help="Converts a GDS script to a GDA file (UNSUPPORTED).",
                no_args_is_help = True,
                hidden = True
            )
@click.argument("input")
@click.argument("output")
def unpack(input, output):
    input = open(input, "rb").read()
    output = open(output, "w", encoding="utf-8")

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
                out += hex(int.from_bytes(param[1], "big"))
            else:
                out += repr(param[1])
        out += "\n"

    output.write(out.strip())

@click.command(
                name="create_gda",
                help="Creates a GDS file from a GDA (discontinued Flora format).",
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