import click
import contextlib
import json
import yaml
import os
import sys
import collections

import struct
import parse
import ast
from utils import cli_file_pairs, foreach_file_pair, RESOURCES
from version import v


@click.group(
    help="Script-like format, also used to store puzzle parameters.", options_metavar=""
)
def cli():
    pass

commands = json.load(open(os.path.join(RESOURCES,"commands.json"), encoding="utf-8"))
commands_i = {
    val["id"]: key for key, val in commands.items() if "id" in val
}  # Inverted version of commands

class GDS:
    def __init__(self, cmds=None):
        if cmds is None:
            cmds = []
        self.cmds = cmds

    @classmethod
    def from_gds(Self, file):
        length = int.from_bytes(file[0:4], "little")
        if file[4:6] == b"\x0c\x00":
            return Self([])
        cmd_data = file[6 : length + 4]
        cmds = []

        cmd = None
        params = []
        c = 0
        while True:
            if c >= length:
                raise Exception(
                    "GDS file error: End of file reached with no 0xC command!"
                )
            if cmd == None:
                cmd = int.from_bytes(cmd_data[c : c + 2], "little")
                if cmd in commands_i:
                    cmd = commands_i[cmd]
                c += 2
                continue

            p_type = int.from_bytes(cmd_data[c : c + 2], "little")

            if p_type == 0:
                cmds.append({"command": cmd, "parameters": params})
                cmd = None
                params = []
                c += 2
            elif p_type == 1:
                params.append(
                    {
                        "type": "int",
                        "data": struct.unpack('>f', cmd_data[c + 2 : c + 6])[0],
                    }
                )
                c += 6
            elif p_type == 2:
                params.append(
                    {
                        "type": "float",
                        "data": int.from_bytes(cmd_data[c + 2 : c + 6], "little"),
                    }
                )
                c += 6
            elif p_type == 3:
                str_len = int.from_bytes(cmd_data[c + 2 : c + 4], "little")
                params.append(
                    {
                        "type": "string",
                        "data": cmd_data[c + 4 : c + 4 + str_len]
                        .decode("ascii")  # TODO: JP/KO compatibility
                        .rstrip("\x00"),
                    }
                )
                c += str_len + 4
            elif p_type == 6:
                # address within the gds file range. usually fits in a short, but can be an int.
                params.append(
                    {
                        "type": "taddr",
                        "data": int.from_bytes(cmd_data[c + 2 : c + 6], "little"),
                    }
                )
                c += 6
            elif p_type == 7:
                params.append(
                    {
                        "type": "saddr",
                        "data": int.from_bytes(cmd_data[c + 2 : c + 6], "little"),
                    }
                )
                c += 6
            elif p_type == 8:
                params.append({"type": "not"})
                c += 2
            elif p_type == 9:
                params.append({"type": "and"})
                c += 2
            elif p_type == 0xA:
                params.append({"type": "or"})
                c += 2
            elif p_type == 0xB:
                # break
                params.append({"type": "break"})
                c += 2
            elif p_type == 0xC:
                # eof
                cmds.append({"command": cmd, "parameters": params})
                break
            else:
                raise Exception(
                    f"GDS file error: Invalid or unsupported parameter type {hex(p_type)}!"
                )

        return Self(cmds)

    @classmethod
    def from_json(Self, file):
        cmds = json.loads(file)["data"]
        # TODO: reject non-compatible json files
        return Self(cmds)

    @classmethod
    def from_yaml(Self, file):
        cmds = yaml.safe_load(file)["data"]
        # TODO: reject non-compatible yaml files
        return Self(cmds)

    @classmethod
    def from_gda(Self, file):  # TODO: make this, so gds_old can be completely removed
        cmds = []

        for line in file.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if line == "":
                continue

            line, strings = parse.remove_strings(line)
            line = line.rstrip().split(" ")
            cmd = line[0]

            # TODO: handle inline comments, maybe

            if cmd in commands:
                cmd = commands[cmd]
                if "alias" in cmd:
                    cmd = commands[cmd["alias"]]
            elif cmd.startswith("cmd_") or cmd.startswith("unk_"):
                cmd = int(cmd[4:])
            elif cmd.startswith("0x"):
                cmd = int(cmd[2:], base=16)
            else:
                raise Exception(f"Unknown GDA command: {cmd}")

            params = []

            for param in line[1:]:
                if param.isdigit():
                    params.append({"type": "int", "data": int(param)})
                elif param.startswith("0x"):
                    params.append({"type": "float", "data": float(param)})
                elif param.startswith('"') and param.endswith('"'):
                    param = ast.literal_eval(f'"{strings[int(param[1:-1])]}"')
                    params.append({"type": "string", "data": param})
                elif param.startswith("@"):
                    params.append({"type": "taddr", "data": int(param[1:], 16)})
                elif param.startswith("$"):
                    params.append({"type": "saddr", "data": int(param[1:], 16)})
                elif param.startswith("NOT"):
                    params.append({"type": "not"})
                elif param.startswith("AND"):
                    params.append({"type": "and"})
                elif param.startswith("OR"):
                    params.append({"type": "or"})
                elif param.startswith("BREAK"):
                    params.append({"type": "break"})
                else:
                    raise Exception(f"Invalid GDA parameter: {param}")

            cmds.append({"command": cmd, "parameters": params})

        return Self(cmds)

    def __getitem__(self, index):
        index = int(index)
        return self.cmds[index]

    def to_json(self):
        return json.dumps({"version": v, "data": self.cmds}, indent=4)

    def to_yaml(self):
        return yaml.safe_dump({"version": v, "data": self.cmds})

    def to_gds(self):
        out = b"\x00" * 2
        for command in self.cmds:
            if type(command["command"]) == int:
                out += command["command"].to_bytes(2, "little")
            else:
                out += command["command"]["id"].to_bytes(2, "little")
            for param in command["parameters"]:
                if param["type"] == "int":
                    out += b"\x01\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "float":
                    out += b"\x02\x00"
                    out += struct.pack('>f', param["data"])
                elif param["type"] == "string":
                    out += b"\x03\x00"
                    out += (len(param["data"]) + 1).to_bytes(2, "little")
                    out += (
                        param["data"].encode("ASCII") + b"\x00"
                    )  # TODO: JP/KO compatibility
                elif param["type"] == "taddr":
                    out += b"\x06\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "saddr":
                    out += b"\x07\x00"
                    out += param["data"].to_bytes(4, "little")
                elif param["type"] == "not":
                    out += b"\x08\x00"
                elif param["type"] == "and":
                    out += b"\x09\x00"
                elif param["type"] == "or":
                    out += b"\x0a\x00"
                elif param["type"] == "break":
                    out += b"\x0b\x00"
                else:
                    raise Exception(
                        f"GDS JSON error: Invalid or unsupported parameter type '{param['type']}'!"
                    )
            out += b"\x00\x00"
        out = out[:-2] + b"\x0c\x00"

        return len(out).to_bytes(4, "little") + out

    def to_bin(self):  # alias
        return self.to_gds()

    def to_gda(self):
        out = ""
        for command in self.cmds:
            if type(command["command"]) == int:
                out += "0x" + command["command"].to_bytes(1, "little").hex()
            else:
                out += command["command"]
            for param in command["parameters"]:
                out += " "
                if param["type"] == "int":
                    out += str(param["data"])
                elif param["type"] == "string":
                    out += repr(param["data"])
                elif param["type"] == "float":
                    out += str(param["data"])
                elif param["type"] == "taddr":
                    out += f"@{param['data'].hex()}"
                elif param["type"] == "saddr":
                    out += f"${param['data'].hex()}"
                elif param["type"] == "not":
                    out += "NOT"
                elif param["type"] == "and":
                    out += "AND"
                elif param["type"] == "or":
                    out += "OR"
                elif param["type"] == "break":
                    out += "BREAK"
                else:
                    raise Exception(
                        f"GDA error: invalid or unsupported parameter type '{param['type']}'!"
                    )
            out += "\n"
        return out


@cli.command(name="compile", no_args_is_help=True)
@click.argument("input", required=False, type=click.Path(exists=True))
@click.argument("output", required=False, type=click.Path(exists=False))
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recurse into subdirectories of the input directory to find more applicable files.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output. By default, operations involving multiple files will show a progressbar.",
)
@click.option(
    "--overwrite/--no-overwrite",
    "-o/-O",
    default=True,
    help="Whether existing files should be overwritten. Default: true",
)
@click.option(
    "--format",
    "-f",
    required=False,
    default=None,
    multiple=False,
    help="The format of the input file. Will be inferred from the file ending or content if unset. "
    "If multiple file types would compile to the same output (but may not necessarily have the same content), "
    "specify this to disambigute. Possible values: gda, json, yaml",
)
def compile(
    input=None, output=None, recursive=False, quiet=False, format=None, overwrite=None
):
    """
    Compiles the human-readable script(s) at INPUT into the game's binary script files at OUTPUT.

    INPUT can be a single file or a directory (which obviously has to exist). In the latter case subfiles with the correct file ending will be processed.
    If unset, defaults to the current working directory.

    The meaning of OUTPUT may depend on INPUT:
    - If INPUT is a file, then OUTPUT is expected to be a file, unless it explicitly ends with a slash indicating a directory.
      In this case, if unset OUTPUT will default to the INPUT filename with `.gds` exchanged/appended.
    - Otherwise OUTPUT has to be a directory as well (or an error will be shown).
      In this case, if unset OUTPUT will default to the INPUT directory (which may itself default to the current working directory).

    In the file-to-file case, the paths are explicitly used as they are. Otherwise, if multiple input files were collected, or OUTPUT is a directory,
    an output path is inferred for each input file by exchanging the input format's file ending for, or otherwise appending the `.gds` file ending.

    In the case where INPUT is a directory, if no format is specified, this command will collect files of all compatible types. Note that this can lead
    to situations where multiple files would compile to the same output (e.g. `test.json` and `test.gda` would both be candidates for `test.gds`);
    this command will NOT make a choice in this case, and instead ask to explicitly specify the format to be used.
    """

    in_endings = []
    if format is None:
        in_endings = [".gda", ".json", ".yaml", ".yml"]
    elif format == "gda":
        in_endings = [".gda"]
    elif format == "json":
        in_endings = [".json"]
    elif format in ["yaml", "yml"]:
        in_endings = [".yaml", ".yml"]
    else:
        raise Exception(f"Unsupported input format: '{format}'")

    def process(input, output):
        inpath = input
        input = open(inpath, "r", encoding="utf-8").read()

        format2 = format
        if format2 is None:
            if inpath.lower().endswith(".gda"):
                format2 = "gda"
            elif inpath.lower().endswith(".json"):
                format2 = "json"
            elif inpath.lower().endswith(".yml") or inpath.lower().endswith(".yaml"):
                format2 = "yaml"

        gds = None
        with contextlib.suppress(Exception):
            if format2 == "gda":
                gds = GDS.from_gda(input)
            elif format2 == "json":
                gds = GDS.from_json(input)
            elif format2 in ["yaml", "yml"]:
                gds = GDS.from_yaml(input)

        if gds is None:
            if format2 is not None:
                # TODO: should this abort instead?
                print(
                    f"WARNING: Input file '{inpath}' did not have expected format '{format2}'",
                    file=sys.stderr,
                )
            # format not specified and couldn't be inferred, or file turns out not to have the correct format
            # => try all the formats & see which one works (only one should be possible)
            for f in ["gda", "json", "yaml"]:
                with contextlib.suppress(Exception):
                    if f == "gda":
                        gds = GDS.from_gda(input)
                    elif f == "json":
                        gds = GDS.from_json(input)
                    elif f == "yaml":
                        gds = GDS.from_yaml(input)
                    if gds is not None:
                        break
            if gds is None:
                raise Exception(
                    f"File '{inpath}' couldn't be read: not a known file format"
                    + (f" (expected '{format2}')" if format2 is not None else "")
                )

        output = open(output, "wb")
        output.write(gds.to_bin())
        output.close()

    pairs = cli_file_pairs(
        input, output, in_endings=in_endings, out_ending=".gds", recursive=recursive
    )

    duplicates = collections.defaultdict(list)
    for ip, op in pairs:
        duplicates[op].append(ip)
    duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    if len(duplicates) > 0:
        print(
            f"ERROR: {len(duplicates)} {'files have' if len(duplicates) > 1 else 'file has'} multiple conflicting source files; please explicitly specify a format to determine which should be used.",
            file=sys.stderr,
        )
        for op, ips in duplicates.items():
            pathlist = ", ".join("'" + ip + "'" for ip in ips)
            print(f"'{op}' could be compiled from {pathlist}", file=sys.stderr)
        sys.exit(-1)

    if not overwrite:
        new_pairs = []
        existing = []
        for ip, op in pairs:
            if os.path.exists(op):
                existing.append(op)
            else:
                new_pairs.append((ip, op))

        if not quiet:
            print(f"Skipping {len(existing)} existing output files.")

        pairs = new_pairs

    foreach_file_pair(pairs, process, quiet=quiet)


@cli.command(name="decompile", no_args_is_help=True)
@click.argument("input", required=False, type=click.Path(exists=True))
@click.argument("output", required=False, type=click.Path(exists=False))
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recurse into subdirectories of the input directory to find more applicable files.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output. By default, operations involving multiple files will show a progressbar.",
)
@click.option(
    "--overwrite/--no-overwrite",
    "-o/-O",
    default=True,
    help="Whether existing files should be overwritten. Default: true",
)
@click.option(
    "--format",
    "-f",
    required=False,
    multiple=False,
    help="The format used for output. Possible values: gda (default), json, yaml",
)
def decompile(
    input=None, output=None, recursive=False, quiet=False, format=None, overwrite=None
):
    """
    Decompiles the GDS script(s) at INPUT into a human-readable text format at OUTPUT.

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
    out_ending = ""
    if format == "gda" or format is None:
        out_ending = ".gda"
    elif format == "json":
        out_ending = ".json"
    elif format in ["yaml", "yml"]:
        out_ending = ".yml"
    else:
        raise Exception(f"Unsupported output format: '{format}'")

    def process(input, output):
        input = open(input, "rb").read()
        gds = GDS.from_gds(input)

        nonlocal format
        if format is None:
            if output.lower().endswith(".gda"):
                format = "gda"
            elif output.lower().endswith(".json"):
                format = "json"
            elif output.lower().endswith(".yml") or output.lower().endswith(".yaml"):
                format = "yaml"
            else:
                print(
                    f"WARNING: output format couldn't be inferred from filename '{output}'; using default (gda). To remove this warning, please explicitly specify a format.",
                    file=sys.stderr,
                )

        with open(output, "w", encoding="utf-8") as output:
            if format == "gda":
                output.write(gds.to_gda())
            elif format == "json":
                output.write(gds.to_json())
            elif format in ["yaml", "yml"]:
                output.write(gds.to_yaml())

    pairs = cli_file_pairs(
        input, output, in_endings=[".gds"], out_ending=out_ending, recursive=recursive
    )
    if not overwrite:
        new_pairs = []
        existing = []
        for ip, op in pairs:
            if os.path.exists(op):
                existing.append(op)
            else:
                new_pairs.append((ip, op))

        if not quiet:
            print(f"Skipping {len(existing)} existing output files.")

        pairs = new_pairs
    foreach_file_pair(pairs, process, quiet=quiet)
