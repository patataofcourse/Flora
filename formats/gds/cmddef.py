#!/usr/bin/env python3

from typing import Optional, List, Union, Set
import os
from dataclasses import dataclass, field

import logging

import yaml
from dacite import from_dict

from utils import RESOURCES


logger = logging.getLogger("flora.debug.gds.cmddef")


@dataclass
class GDSCommandParam:
    cmd: int
    """The command for which this is a parameter"""
    idx: int
    """The index of the parameter in order"""
    type: str
    """
    The data type of the command. Real builtin GDS datatypes are:
    int (1)
    (also usable as uint, short, ushort, byte, ubyte; TODO: document which parameters use which)
    float (2)
    string (3)
    longstr (4, never used)
    
    Our GDA framework also defines some auxiliary datatypes:
    bool: backed by either an int (true = nonzero) or a string (true = "true")
    bool|int: backed by an int (true = nonzero)
    bool|string: backed by a string (true = "true")
    
    TODO: Compound datatypes may make the code more understandable, by combining semantically
    related parameters into a single one:
    pt(x: int, y: int)
    rect(x: int, y: int, w: int, h: int)
    ...
    """
        
    name: Optional[str] = None
    """A descriptive name for the parameter. Can optionally be written in the script."""
    desc: Optional[str] = None
    """
    Description of what the parameter means.
    """
    uncertain: bool = False
    """
    Purely informative: whether research is conclusive about the meaning of the parameter.
    The fact that the parameter exists is NOT uncertain, but its meaning may not be clear yet.
    Parameters without a name are normally uncertain, even when they don't mark it explicitly.
    """
    optional: bool = False
    """
    A small number of commands have optional parameters at the end of their argument list:
    they check if the next token (see general info about GDS) has the expected type, and if
    not stops reading the argument list.
    """


@dataclass
class GDSCommand:
    id: int
    """ID of the command, as it appears in binary scripts"""

    name: Optional[str] = None
    """Human-readable name, as it would appear in the decompiled assembly"""
    aliases: list[str] = field(default_factory=lambda: [])
    """
    Other names this command may be recognized by when compiling scripts,
    for example a naming convention from a previous decompiler version
    """

    desc: Optional[str] = None
    """
    Description of what the command does, where it's used etc.
    """
    uncertain: bool = False
    """
    Purely informative: whether the research is conclusive about the meaning, purpose, functionality
    etc of this command. Note that the structural properties below are obvious to read off from
    disassembly, and are therefore not subject to this; it purely qualifies our understanding
    of the command's meaning and usage.
    """

    condition: bool = False
    """
    True if the command sets the condition flag. Those commands usually don't have side effects.
    """
    context: Set[str] = field(default_factory=lambda: {"all"})
    """
    (list of) context name(s) where the command is defined. The game contains many different
    script engines called in different contexts, and while they all run the same type of script,
    most commands are noops in engines they weren't meant to be used in.
    
    The special string "all" denotes that a command is implemented everywhere (for example,
    if it doesn't proxy through the script engine itself but directly to the sound system etc.)
    """

    params: list[GDSCommandParam] = field(default_factory=lambda: [])
    """
    List of parameters the command accepts, if it's a simple command with a fixed parameter list.
    """
    complex: bool = False
    """
    Set to true for special structural commands that don't have a fixed parameter list,
    but instead need to be parsed in a more complex way. The logic for that will be looked
    up in Python code.
    """

    file: Optional[str] = None
    """
    The file path where the command is defined; for debug purposes
    """


CONTEXTS = ["all", "event", "room", "puzzle"]


def load_group(
    data: dict,
    group_name: str = None,
    parent_prefix: str = None,
    parent_context: Union[str, List[str]] = None,
    filename: str = None,
) -> List[GDSCommand]:  # sourcery skip: remove-pass-body
    """
    Reads a single group object from the command definition YAML files. That group might be the top-level file itself.
    """
    if "prefix" in data:
        prefix = data["prefix"]
    else:
        prefix = parent_prefix or ""
        if group_name is not None:
            prefix += f"{group_name}."

    context = data["context"] if "context" in data else parent_context
    commands = data["commands"]
    if isinstance(commands, dict):

        def command_kv(k, v):
            if v is None:
                v = {}
            cid = v.get("id")
            name = v.get("name")
            if isinstance(k, int):
                if cid is not None:
                    if k != cid:
                        raise ValueError(
                            "id field specified in a GDSCommand listed by id, and the two values didn't match"
                        )
                    logger.warning(
                        "id field specified in a GDSCommand listed by id is redundant"
                    )
                cid = k
            elif isinstance(k, str):
                if name is not None:
                    if k != name:
                        raise ValueError(
                            "name field specified in a GDSCommand listed by name, and the two values didn't match"
                        )
                    logger.warning(
                        "name field specified in a GDSCommand listed by name is redundant"
                    )
                # TODO: handle hex ID in string?
                name = k
            else:
                raise ValueError(
                    "GDSCommands can only be listed by their name or numeric id"
                )
            v["id"] = cid
            v["name"] = name
            return v

        commands = [command_kv(k, v) for k, v in commands.items()]

    def process_command(c):
        if c.get("id") is None:
            raise ValueError("GDSCommand must define an id")

        if "context" not in c:
            c["context"] = context or "all"
        if isinstance(c["context"], str):
            c["context"] = [c["context"]]
        c["context"] = set(c["context"])
        if "prefix" not in c:
            c["prefix"] = prefix
        if c["prefix"] is not None and c["name"] is not None:
            c["name"] = c["prefix"] + c["name"]

        params = c.get("params") or []
        if isinstance(params, dict):

            def param_kv(k, v):
                # have to do that here already, otherwise I don't have any object to put the name into
                if isinstance(v, str):
                    v = {"type": v}
                if isinstance(k, int):
                    # specifying a number here means we don't want a name
                    pass
                else:
                    if "name" in v:
                        # pylint: disable=logging-not-lazy
                        logger.warning(
                            "name field specified in a parameter that was listed by name"
                            + (", and did not match" if k != v["name"] else "")
                        )

                    v["name"] = k
                return v

            params = [param_kv(k, v) for k, v in params.items()]

        def process_param(idx, p):
            if isinstance(p, str):
                p = {"type": p}
            p["cmd"] = c["id"]
            p["idx"] = idx

            return from_dict(data_class=GDSCommandParam, data=p)

        c["params"] = [process_param(i, p) for i, p in enumerate(params)]

        c["file"] = filename

        return from_dict(data_class=GDSCommand, data=c)

    commands = [process_command(v) for v in commands]

    groups = data.get("groups")
    if isinstance(groups, dict):
        for k, v in groups.items():
            commands.extend(load_group(v, k, prefix, context, filename))
    elif groups is not None:
        logger.warning(
            "groups key has to be a dictionary mapping a group name to a command list"
        )

    return commands


def load_file(filename: str, root: str) -> list[GDSCommand]:
    """
    Reads a single command definition YAML file. Default prefix is the directory structure relative to the root, if specified.
    """
    with open(filename, encoding="utf8") as f:
        data = yaml.safe_load(f)

    # version = data.get("version")

    if root is not None:
        cur = os.path.splitext(os.path.relpath(filename, root))[0]
        cur, group_name = os.path.split(cur)
        parent_prefix = ""
        while cur != "":
            cur, seg = os.path.split(cur)
            parent_prefix = f"{seg}.{parent_prefix}"
    else:
        parent_prefix = None
        group_name = None

    return load_group(data, group_name, parent_prefix, None, filename)


def load_cmdrepo(root: str) -> list[GDSCommand]:
    """
    Reads all the command definitions from the YAML files in the specified directory, and returns them as a list of data objects.
    Only very basic sanity checking internal to each command definition is performed by this point.
    """
    commands = []
    for r, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith("yml") or f.lower().endswith("yaml"):
                path = os.path.join(r, f)
                commands.extend(load_file(path, root))
    return commands


def build_maps(
    cmds: list[GDSCommand],
) -> tuple[dict[int, GDSCommand], dict[str, GDSCommand]]:
    """
    Structures a list of commands into a bidirectional lookup table by command ID and human-readable name.
    """
    by_id = {}
    by_name = {}

    for cmd in cmds:
        if cmd.id in by_id:
            raise ValueError(f"Command id {hex(cmd.id)} defined twice")
        by_id[cmd.id] = cmd

        if cmd.name in by_name:
            existing = by_name[cmd.name]
            if not isinstance(existing, GDSCommand):
                other = '", "'.join(c.name for c in existing["ALIAS_CONFLICT"])
                logger.warning(
                    'Command name "%s" is already used as alias by commands "%s". '
                    "The former will take precedence. Please make sure to update any GDA files decompiled "
                    "with a previous version of Flora.",
                    cmd.name,
                    other,
                )
            elif existing.name != cmd.name:
                logger.warning(
                    'Command "%s" has alias "%s", which is also a command name. '
                    "The latter will take precedence. Please make sure to update any GDA files decompiled "
                    "with a previous version of Flora.",
                    existing.name,
                    cmd.name,
                )
            else:
                raise ValueError(f'Command name "{cmd.name}" defined twice')

        if cmd.name is None:
            continue
        by_name[cmd.name] = cmd
        for alias in cmd.aliases:
            if alias in by_name:
                existing = by_name[alias]
                if not isinstance(existing, GDSCommand):
                    existing["ALIAS_CONFLICT"].append(cmd)
                elif existing.name == alias:
                    logger.warning(
                        'Command "%s" has alias "%s", which is also a command name. '
                        "The latter will take precedence. Please make sure to update any GDA files decompiled "
                        "with a previous version of Flora.",
                        cmd.name,
                        alias,
                    )
                else:
                    by_name[alias] = {"ALIAS_CONFLICT": [existing, cmd]}
            else:
                by_name[alias] = cmd

    for k, v in by_name.items():
        if not isinstance(v, GDSCommand):
            other = '", "'.join(c.name for c in existing["ALIAS_CONFLICT"])
            logger.warning(
                'Commands "{other}" all define alias "%s"; none of them will be registered.',
                k,
            )
            del by_name[k]

    return (by_id, by_name)


COMMANDS_BYNAME = {}
COMMANDS_BYID = {}

CMDDEF_ROOT = os.path.join(RESOURCES, "gds_commands")


def init_commands(root: str = None):
    global COMMANDS_BYID, COMMANDS_BYNAME  # pylint: disable=global-statement
    if root is None:
        root = CMDDEF_ROOT
    try:
        commands = load_cmdrepo(root)
        COMMANDS_BYID, COMMANDS_BYNAME = build_maps(commands)
    except ValueError as e:
        logger.error(e)
        print(
            "An error occured when reading command definitions from metadata. Your installation of Flora might be corrupted. If you're sure it's not, "
            "you can file an issue on GitHub: https://github.com/patataofcourse/Flora"
        )
        return

    if undefined_commands := [i for i in range(0x100) if i not in COMMANDS_BYID]:
        logger.warning(
            "The definition for the following commands is missing:\n%s\nThis may cause significant soundness issues in the (de)compiler!"
            "Please make sure to correctly identify and define the parameter counts for these commands.",
            ", ".join(hex(i) for i in undefined_commands),
        )
        print(
            "An error occured when reading command definitions from metadata. Your installation of Flora might be corrupted. If you're sure it's not, "
            "you can file an issue on GitHub: https://github.com/patataofcourse/Flora"
        )


# sourcery skip: hoist-statement-from-if
if __name__ == "__main__":
    logging.basicConfig()

    # TODO: unit tests just to make sure this function's understanding of syntax is still correct
    # init_commands("formats/gds/_test")
    init_commands()

    import pprint

    pprint.pp(COMMANDS_BYID)
    pprint.pp(COMMANDS_BYNAME)
else:
    init_commands()