"""
Provides the `read_gda` and `write_gda` methods to read/write a `GDSProgram` (see the `model` module) from/to a a human-readable GDA text file (buffer).

Requires the command definitions provided by `cmddef` for type checking and parameter data, as well as (possibly in the future) documentation features.
"""

from typing import Optional, List
from dataclasses import dataclass

from .model import (
    GDSProgram,
    GDSElement,
    GDSLabel,
    GDSInvocation,
    GDSValue,
    GDSIfInvocation,
    GDSLoopInvocation,
    GDSConditionToken
)


def read_gda(data: str, path: Optional[str] = None) -> GDSProgram:
    pass


@dataclass(kw_only=True)
class WriterContext:
    filename: Optional[str] = None
    result: str = ""
    indent: int = 0

    def write(self, s: str):
        self.result += s
    def nl(self):
        self.result += '\n' + ' '*self.indent
    def insert_comment(self, comment: str):
        self.result, latest_line = self.result.rsplit("\n", 1)
        self.nl()
        self.write(f"# {comment}\n")
        self.write(latest_line)


def write_gda(prog: GDSProgram, filename: Optional[str] = None) -> str:
    ctx = WriterContext(filename=filename)
    version = "0.1"
    ctx.write(f"#!version {version}\n")
    ctx.write(f"# {filename}\n")
    
    for el in prog.elements:
        ctx.nl()
        write_element(ctx, el)
    return ctx.result


def write_element(ctx: WriterContext, el: GDSElement):
    if el in GDSElement.BREAK:
        ctx.write("break")
    elif el in GDSElement.label:
        lbl: GDSLabel = el()
        ctx.write(f'{"@" if lbl.present else "@!"}{lbl.name}')
        if lbl.loc is not None:
            ctx.write(f"({lbl.loc})")
    elif el in GDSElement.command:
        cmd: GDSInvocation = el()
        ctx.write(cmd.command.name or hex(cmd.command.id))
        if cmd.command.complex:
            (
                WRITE_COMPLEX.get(cmd.command.name)
                or WRITE_COMPLEX.get(cmd.command.id)
            )(ctx, cmd)
        else:
            write_simple(ctx, cmd)

def write_simple(ctx: WriterContext, cmd: GDSInvocation):
    if len(cmd.args) == 0:
        return
    ctx.write(" (")
    first = True
    for arg, param in zip(cmd.args, cmd.command.params):
        if first:
            first = False
        else:
            ctx.write(" ")
        if arg in GDSValue.bool:
            val = arg()
            if isinstance(val, str):
                arg = GDSValue.str(val)
            elif isinstance(val, int):
                arg = GDSValue.int(val)
            else:
                ctx.write("true" if arg else "false")
        if arg in GDSValue.int:
            val: int = arg()
            bytelen = (
                4
                if param.type.endswith("int")
                else 2 if param.type.endswith("short") else 1
            )
            if not param.type.startswith("u") and val >= 2 ** (bytelen * 8 - 1):
                val -= 2 ** (bytelen * 8 - 1)
            ctx.write(str(val))
        elif arg in GDSValue.float:
            val: float = arg()
            ctx.write(str(val))
        elif arg in GDSValue.str or arg in GDSValue.longstr:
            val: str = arg()
            if param.type == "longstr":
                ctx.write("l")
            ctx.write(repr(val))
    ctx.write(")")

def write_condition(ctx: WriterContext, cond: List[GDSConditionToken]):
    first = True
    for tok in cond:
        if first:
            first = False
        else:
            ctx.write(" ")
        if tok in GDSConditionToken.NOT:
            ctx.write("not")
        elif tok in GDSConditionToken.AND:
            ctx.write("and")
        elif tok in GDSConditionToken.OR:
            ctx.write("or")
        elif tok in GDSConditionToken.command:
            cmd: GDSInvocation = tok()
            ctx.write(cmd.command.name or hex(cmd.command.id))
            if cmd.command.complex:
                (
                    WRITE_COMPLEX.get(cmd.command.name)
                    or WRITE_COMPLEX.get(cmd.command.id)
                )(ctx, cmd)
            else:
                write_simple(ctx, cmd)

def write_block(ctx: WriterContext, cond: List[GDSElement]):
    ctx.write(" {")
    ctx.indent += 2
    for el in cond:
        ctx.nl()
        write_element(ctx, el)
    ctx.indent -= 2
    ctx.nl()
    ctx.write("}")

def write_if(ctx: WriterContext, cmd: GDSIfInvocation):
    ctx.write(" ")
    write_condition(ctx, cmd.condition)
    ctx.write(":")
    if cmd.target is not None:
        ctx.write(f' {"@" if cmd.target.primary else "@!"}{cmd.target.label}')
    if cmd.block is not None:
        write_block(ctx, cmd.block)

def write_else(ctx: WriterContext, cmd: GDSIfInvocation):
    ctx.write(":")
    if cmd.target is not None:
        ctx.write(f' {"@" if cmd.target.primary else "@!"}{cmd.target.label}')
    if cmd.block is not None:
        write_block(ctx, cmd.block)

def write_repeatN(ctx: WriterContext, cmd: GDSLoopInvocation):
    count: int = cmd.condition
    ctx.write(f" {count}:")
    if cmd.target is not None:
        ctx.write(f' {"@" if cmd.target.primary else "@!"}{cmd.target.label}')
    if cmd.block is not None:
        write_block(ctx, cmd.block)

def write_while(ctx: WriterContext, cmd: GDSLoopInvocation):
    ctx.write(" ")
    write_condition(ctx, cmd.condition)
    ctx.write(":")
    if cmd.target is not None:
        ctx.write(f' {"@" if cmd.target.primary else "@!"}{cmd.target.label}')
    if cmd.block is not None:
        write_block(ctx, cmd.block)


WRITE_COMPLEX = {
    "if": write_if,
    "elif": write_if,
    "else": write_else,
    "repeatN": write_repeatN,
    "while": write_while,
}
