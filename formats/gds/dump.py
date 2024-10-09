"""
Legacy support for writing a read GDS program to JSON or YAML.

This doesn't seem very useful now, since the format and internal
representation have changed drastically. I still wanted to add
it just in case.
"""

import json
from typing import List, Dict

import version
import formats.gds.model as model


def dump_command(cmd: model.GDSInvocation) -> Dict:
    # sourcery skip: remove-redundant-pass
    obj = {
        "command": cmd.command.name or cmd.command.id,
    }

    if isinstance(cmd, (model.GDSIfInvocation, model.GDSLoopInvocation)):
        if cmd.condition is not None:
            if isinstance(cmd.condition, int):
                obj["loop_cnt"] = cmd.condition
            else:
                cond = []

                for c in cmd.condition:
                    if c in model.GDSConditionToken.AND:
                        cond.append({"flag": "and"})
                    elif c in model.GDSConditionToken.OR:
                        cond.append({"flag": "or"})
                    elif c in model.GDSConditionToken.NOT:
                        cond.append({"flag": "not"})
                    elif c in model.GDSConditionToken.command:
                        cond.append(dump_command(c()))
                    else:
                        # unreachable
                        pass

                obj["condition"] = cond
        if cmd.block is not None:
            obj["block"] = dump_block(cmd.block)

    else:
        obj["args"] = [
            {"type": arg.type.describe(), "value": arg.value} for arg in cmd.args
        ]

    return obj


def dump_block(block: List[model.GDSElement]) -> List:
    els = []

    for el in block:
        if el in model.GDSElement.command:
            els.append(dump_command(el()))
        elif el in model.GDSElement.BREAK:
            els.append({"flag": "break"})
        elif el in model.GDSElement.label:
            lbl = {"name": el().name, "present": el().present}
            if el().loc is not None:
                lbl["loc"] = el().loc
            els.append({"label": lbl})

    return els


def dump_json(prog: model.GDSProgram) -> str:
    return json.dumps(
        {"version": version.__version__, "data": dump_block(prog.elements)}
    )


def load_json(json: str) -> model.GDSProgram:
    pass
