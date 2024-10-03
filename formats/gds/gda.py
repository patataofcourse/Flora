"""
Provides the `read_gda` and `write_gda` methods to read/write a `GDSProgram` (see the `model` module) from/to a a human-readable GDA text file (buffer).

Requires the command definitions provided by `cmddef` for type checking and parameter data, as well as (possibly in the future) documentation features.
"""

import contextlib
from typing import Any, Optional, List
from dataclasses import dataclass


from utils import round_perfect
from .cmddef import GDSCommand
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
        for line in comment.splitlines():
            self.nl()
            self.write(f"# {line}")
        self.write("\n"+latest_line)


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
            ctx.write(str(round_perfect(val)))
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



def format_comment(comment: str, filename: str, args: List[GDSValue], cmd: GDSCommand):
    import re
    def get_var(name: str) -> Any:
        if name.lower() == "lang":
            return "en"
        if name.lower() == "eventid":
            match: re.Match = re.match(r"/data/script/event/e(\d+).gd[as]", filename)
            if match:
                return int(match.group(1))
            else:
                return "?"
        with contextlib.suppress(ValueError):
            arg_id = int(name) - 1
            if arg_id < 0 or arg_id >= len(args):
                return "?"
            
            arg = args[arg_id]

            
        
        return "?"

    def format_value(value: Any, modifiers: List[str]) -> str:
        for m in modifiers:
            if not m.startswith("r"):
                continue
            step, max_, *_ = m[1:].split("<=") + [None]
            if not isinstance(value, int):
                value = "?"
                break
            step = int(step)
            value = (value // step) * step
            if max_ is not None:
                value = min(value, int(max_))
        
        for m in modifiers:
            if not m.startswith("0"):
                continue
            l = int(m[1:])
            if not isinstance(value, int):
                value = "?" * l
                break
            value = str(value)
            value = "0" * max(0, l - len(value)) + value
        
        return str(value)

    def readfile(path: str) -> str:
        return f"test file content\n({path})"

    from parsy import forward_declaration, regex, seq, string
    
    str_part = regex(r'[^$]')
    str_esc = string(r'$$')
    str_part_fvar = regex(r'[^$}:]')
    str_part_expr = regex(r'[^$)]')
    fvar_esc = string(r'}}') | string(r'::')
    expr_esc = string(r'))')
    
    format_args = regex(r"0\d+") | regex(r"r\d+(<=\d+)?")
    fvar = forward_declaration()
    expr = forward_declaration()
    str_var = string('$') >> (
        string('{') >> fvar << string('}')
        | string('(') >> expr << string(')')
    )
    
    varname = regex(r"\w+")
    
    fvar_expr = (str_part_fvar | fvar_esc | str_var).many().concat()
    fvar.become( seq ( varname.map(get_var) , (string(":") >> format_args).many() ).map(lambda a: format_value(a[0], a[1])) )
    expr.become( (str_part_expr | expr_esc | str_var).many().concat().map(readfile) )
    
    str_ = (str_part | str_esc | str_var).many().concat()
    
    # TODO: parse variables like $TEST or ${1:03} and $(filepath)
    return str_.parse(comment)

if __name__ == "__main__":
    EXAMPLE = """
    /data/etext/${lang}/e${eventid:r100<=300:03}{pcm}/e${eventid}_t${1}.txt:

    $(/data/etext/${lang}/e${eventid:r100<=300:03}{pcm}/e${eventid}_t${1}.txt)
    """
    print(format_comment(EXAMPLE, "/data/script/event/e324.gds", [], None))