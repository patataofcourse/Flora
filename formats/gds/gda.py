"""
Provides the `read_gda` and `write_gda` methods to read/write a `GDSProgram` (see the `model` module) from/to a a human-readable GDA text file (buffer).

Requires the command definitions provided by `cmddef` for type checking and parameter data, as well as (possibly in the future) documentation features.
"""

import contextlib
from typing import Any, Optional, List, Mapping, Union
from dataclasses import dataclass, field

from parsy import (
    forward_declaration,
    regex,
    seq,
    string,
    generate,
    eof,
    Parser,
    success,
    fail,
    peek,
    Result as ParseResult,
)

import formats.gds.value as value
import formats.gds.cmddef as cmddef
from .model import (
    GDSJumpAddress,
    GDSProgram,
    GDSElement,
    GDSLabel,
    GDSInvocation,
    GDSIfInvocation,
    GDSLoopInvocation,
    GDSConditionToken,
)

# === PARSER ===


@Parser
def peek_parser_state(stream, index):
    print(stream[index:])
    return ParseResult.success(index, None)


ws = regex(r"[^\S\r\n]+")
nl = regex(r"\n\s*") | eof.result("\n")
comment = string("#") >> regex(r".*") << nl


def has_nl(res: str) -> Parser:
    return success(res) if "\n" in res else fail("newline required")


# TODO: make at least one nl required here
ws_nl = (
    ((regex(r"\n\s*") | ws | comment.map(lambda v: v + "\n")).many())
    .concat()
    .bind(has_nl)
)
lexeme = lambda p: p << ws.optional()

lparen = lexeme(string("("))
rparen = lexeme(string(")"))
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
colon = lexeme(string(":"))
comma = lexeme(string(","))
eqsign = lexeme(string("="))

BREAK = lexeme(string("break"))
NOT = lexeme(string("not"))
AND = lexeme(string("and"))
OR = lexeme(string("or"))

meta_comment = (
    lexeme(string("#!"))
    >> (
        string("version")
        >> ws
        >> lexeme(regex(r"[\w\.]+")).map(lambda v: ("version", v))
    )
    | regex(r".*").map(lambda v: (None, v)) << nl
)


command_name = lexeme(
    regex(r"[a-zA-Z_][\w\.]*") | regex(r"0x[0-9a-fA-F]{1,2}").map(lambda i: int(i, 16))
)


@generate
def parse_condition():
    conds = []
    while True:
        kw = yield (
            NOT.result(GDSConditionToken.NOT())
            | AND.result(GDSConditionToken.AND())
            | OR.result(GDSConditionToken.OR())
        ).optional()
        if kw is not None:
            conds.append(kw)
            continue
        cmd = yield parse_command.map(GDSConditionToken.command).optional()
        if cmd is None:
            break
        conds.append(cmd)
    return conds


@generate
def parse_label():
    yield string("@")
    present = yield string("!").result(False).optional(True)
    name = yield lexeme(regex("[\w]+"))
    loc = None
    if (yield lparen.optional()) is not None:
        loc = yield lexeme(
            regex(r"0x[0-9a-fA-F]+").map(lambda v: int(v, 16)) | regex(r"\d+").map(int)
        ).optional()
        yield rparen

    return GDSLabel(name=name, present=present, loc=loc)


@generate
def parse_addr():
    yield string("@")
    primary = yield string("!").result(False).optional(True)
    label = yield lexeme(regex("[\w]+"))
    return GDSJumpAddress(label=label, primary=primary)


@generate
def parse_block():
    yield lbrace
    yield ws_nl.optional()
    block = []
    while True:
        el = yield parse_element | peek(rbrace).result(None) | eof.result(None)
        if el is None:
            break
        block.append(el)
        yield ws_nl
    yield rbrace
    return block


def parse_simple(cmdobj: cmddef.GDSCommand) -> Parser:
    # pylint: disable=redefined-outer-name
    @generate
    def parse_simple():
        if next((p for p in cmdobj.params if not p.optional), None) is None:
            if (yield lparen.result(False).optional(True)):
                return GDSInvocation(command=cmdobj, args=[])
        
        yield lparen

        args = []
        for param in cmdobj.params:
            p = param.type.parser()
            if param.optional:
                p = p.optional()
            value = yield lexeme(p)
            if value is None and not param.optional:
                raise ValueError(f"Could not read parameter {param.name}")
            args.append(value)
        
        yield rparen
        
        return GDSInvocation(command=cmdobj, args=args)

    return parse_simple


def parse_if(cmdobj: cmddef.GDSCommand) -> Parser:
    # pylint: disable=redefined-outer-name
    @generate
    def parse_if():
        condition = yield parse_condition

        yield colon

        target = yield parse_addr.optional()
        block = None
        if target is None:
            block = yield parse_block

        return GDSIfInvocation(
            command=cmdobj,
            args=[],
            condition=condition,
            target=target,
            block=block,
            elseif=cmdobj.id == 0x16,
            elze=False,
        )

    return parse_if


def parse_else(cmdobj: cmddef.GDSCommand) -> Parser:
    # pylint: disable=redefined-outer-name
    @generate
    def parse_else():
        yield colon

        target = yield parse_addr.optional()
        block = None
        if target is None:
            block = yield parse_block

        return GDSIfInvocation(
            command=cmdobj,
            args=[],
            condition=None,
            target=target,
            block=block,
            elseif=False,
            elze=True,
        )

    return parse_else


def parse_repeatN(cmdobj: cmddef.GDSCommand) -> Parser:
    # pylint: disable=redefined-outer-name
    @generate
    def parse_repeatN():
        condition = yield value.GDSIntType(4, True).parser()

        yield colon

        target = yield parse_addr.optional()
        block = None
        if target is None:
            block = yield parse_block

        return GDSLoopInvocation(
            command=cmdobj,
            args=[],
            condition=condition,
            target=target,
            block=block,
        )

    return parse_repeatN


def parse_while(cmdobj: cmddef.GDSCommand) -> Parser:
    # pylint: disable=redefined-outer-name
    @generate
    def parse_while():
        condition = yield parse_condition

        yield colon

        target = yield parse_addr.optional()
        block = None
        if target is None:
            block = yield parse_block

        return GDSLoopInvocation(
            command=cmdobj,
            args=[],
            condition=condition,
            target=target,
            block=block,
        )

    return parse_while


@generate
def parse_command():
    name = yield command_name
    cmdobj = cmddef.COMMANDS_BYNAME.get(name) or cmddef.COMMANDS_BYID.get(name)
    if cmdobj is None:
        raise ValueError(f"Command {name} not defined")

    if cmdobj.complex:
        cmd = yield PARSE_COMPLEX.get(cmdobj.name)(cmdobj) or PARSE_COMPLEX.get(
            cmdobj.id
        )(cmdobj)
    else:
        cmd = yield parse_simple(cmdobj)

    return cmd


PARSE_COMPLEX = {
    "if": parse_if,
    "elif": parse_if,
    "else": parse_else,
    "repeatN": parse_repeatN,
    "while": parse_while,
}


@generate
def parse_element():
    kw = yield BREAK.result(GDSElement.BREAK()).optional()
    if kw is not None:
        return kw
    label = yield parse_label.optional()
    if label is not None:
        return GDSElement.label(label)
    cmd = yield parse_command
    return GDSElement.command(cmd)


@generate
def parse_gda_source():
    version = yield meta_comment.map(
        lambda v: v[1] if v[0] == "version" else None
    ).optional()

    elements = []
    while True:
        yield ws_nl.many()
        yield ws.optional()
        # yield peek_parser_state
        el = yield parse_element | eof.result(None)
        if el is None:
            break
        elements.append(el)
        yield ws_nl | eof
    return (version, elements)


def read_gda(data: str, path: Optional[str] = None) -> GDSProgram:
    version, elements = parse_gda_source.parse(data)
    
    def collect_labels(elements: List[GDSElement], labels: Mapping[str, List[Union[GDSLabel, GDSJumpAddress]]] = None):
        if labels is None:
            labels = {}
        for el in elements:
            if el in GDSElement.label:
                name = el().name
                if name not in labels:
                    labels[name] = []
                labels[name].append(el())
            elif el in GDSElement.command and isinstance(el(), (GDSIfInvocation, GDSLoopInvocation)):
                block_cmd = el()
                if block_cmd.target is not None:
                    name = block_cmd.target.label
                    if name not in labels:
                        labels[name] = []
                    labels[name].append(block_cmd.target)
                    
                collect_labels(block_cmd.block, labels)
        return labels
    
    labels = collect_labels(elements)

    return GDSProgram(path=path, elements=elements, labels=labels)


# === WRITER ===


@dataclass(kw_only=True)
class WriterContext:
    filename: Optional[str] = None
    workdir: Optional[str] = None
    result: str = ""
    indent: int = 0

    def write(self, s: str):
        self.result += s

    def nl(self):
        self.result += "\n" + " " * self.indent

    # pylint: disable=redefined-outer-name
    def insert_comment(self, comment: str):
        self.result, latest_line = self.result.rsplit("\n", 1)
        for line in comment.splitlines():
            self.nl()
            self.write(f"# {line}")
        self.write("\n" + latest_line)


def write_gda(
    prog: GDSProgram, filename: Optional[str] = None, workdir: Optional[str] = None
) -> str:
    ctx = WriterContext(filename=filename, workdir=workdir)
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
            (WRITE_COMPLEX.get(cmd.command.name) or WRITE_COMPLEX.get(cmd.command.id))(
                ctx, cmd
            )
        else:
            write_simple(ctx, cmd)


def write_simple(ctx: WriterContext, cmd: GDSInvocation):
    if len(cmd.args) == 0:
        return
    ctx.write(" (")
    ctx.write(" ".join(arg.write() for arg in cmd.args if arg is not None))
    ctx.write(")")

    if cmd.command.comment is not None:
        ctx.insert_comment(
            format_comment(
                cmd.command.comment,
                CommentContext(
                    args=cmd.args, filename=ctx.filename, workdir=ctx.workdir
                ),
            )
        )


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

import os

@dataclass
class CommentContext:
    filename: Optional[str] = None
    workdir: Optional[str] = None
    args: List[value.GDSValue] = field(default_factory=list)
    omit_file_contents: bool = False
    lang: Optional[str] = "en"


# pylint: disable=redefined-outer-name
def format_comment(comment: str, ctx: CommentContext):
    if ctx.filename is not None and os.path.isabs(ctx.filename):
        ctx.filename = os.path.relpath(ctx.filename, "/")
    # sourcery skip: assign-if-exp
    import re

    def get_var(name: str) -> Any:
        if name.lower() == "lang":
            return ctx.lang or "??"
        if name.lower() == "eventid":
            if ctx.filename is None:
                return "?"
            match: re.Match = re.match(r"data/script/event/e(\d+).gd[as]", ctx.filename)
            if match:
                return int(match.group(1))
            return "?"
        with contextlib.suppress(ValueError):
            arg_id = int(name) - 1
            if arg_id < 0 or arg_id >= len(ctx.args):
                return "?"

            arg: value.GDSValue = ctx.args[arg_id]
            return arg.value

        return "?"

    def format_value(val: Any, modifiers: List[str]) -> str:
        for m in modifiers:
            if not m.startswith("r"):
                continue
            step, max_, *_ = m[1:].split("<=") + [None]
            if not isinstance(val, int):
                val = "?"
                break
            step = int(step)
            val = (val // step) * step
            if max_ is not None:
                val = min(val, int(max_))

        for m in modifiers:
            if not m.startswith("0"):
                continue
            l = int(m[1:])
            if not isinstance(val, int):
                val = "?" * l
                break
            val = str(val)
            val = "0" * max(0, l - len(val)) + val

        return str(val)

    def readfile(path: str) -> str:
        if path is None or ctx.workdir is None or ctx.omit_file_contents:
            return "<...>"
        if os.path.isabs(path):
            path = os.path.relpath(path, "/")
        realpath = os.path.join(ctx.workdir, path)
        try:
            with open(realpath, encoding="utf8") as f:
                return f.read()
        except FileNotFoundError:
            return "<FILE NOT FOUND>"

    str_part = regex(r"[^$]")
    str_esc = string(r"$$")
    # str_part_fvar = regex(r"[^$}:]")
    str_part_expr = regex(r"[^$)]")
    # fvar_esc = string(r"}}") | string(r"::")
    expr_esc = string(r"))")

    format_args = regex(r"0\d+") | regex(r"r\d+(<=\d+)?")
    fvar = forward_declaration()
    expr = forward_declaration()
    str_var = string("$") >> (
        string("{") >> fvar << string("}") | string("(") >> expr << string(")")
    )

    varname = regex(r"\w+")

    # fvar_expr = (str_part_fvar | fvar_esc | str_var).many().concat()
    fvar.become(
        seq(varname.map(get_var), (string(":") >> format_args).many()).map(
            lambda a: format_value(a[0], a[1])
        )
    )
    expr.become((str_part_expr | expr_esc | str_var).many().concat().map(readfile))

    str_ = (str_part | str_esc | str_var).many().concat()

    return str_.parse(comment)
