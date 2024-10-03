from typing import Tuple, List, Optional, Callable, TypeVar, Mapping, Union
from dataclasses import dataclass, field
import struct
import functools

# pylint: disable=unused-wildcard-import,wildcard-import
from utils import tagged_union, TU, match

from .model import (
    GDSProgram,
    GDSElement,
    GDSInvocation,
    GDSLoopInvocation,
    GDSIfInvocation,
    GDSValue,
    GDSAddress,
    GDSConditionToken,
    GDSLabel,
    GDSJumpAddress,
    GDSContext,
)
from .cmddef import COMMANDS_BYID, GDSCommand


@tagged_union
class GDSTokenValue:
    """
    Raw token
    """

    command: TU[int]
    int: TU[int]
    float: TU[float]
    str: TU[str]
    longstr: TU[str]
    unused5: TU[None]
    # the source address is the one pointing to the target
    saddr: TU[GDSAddress]
    taddr: TU[GDSAddress]
    NOT: TU[None]
    AND: TU[None]
    OR: TU[None]
    BREAK: TU[None]
    fileend: TU[None]


@dataclass(kw_only=True)
class BinaryLocalized:
    loc: int


@dataclass(kw_only=True)
class GDSToken(BinaryLocalized):
    val: GDSTokenValue


@dataclass(kw_only=True)
class LabelUse(BinaryLocalized):
    loc: int
    addr: int
    use: Optional[str] = None
    primary: bool = False


@dataclass(kw_only=True)
class LabelToken(BinaryLocalized):
    loc: int
    addr: Optional[int]
    pointsto: Optional[LabelUse] = None


@dataclass(kw_only=True)
class BinaryCommand(GDSInvocation, BinaryLocalized):
    loc: int = None


@dataclass(kw_only=True)
class BinaryIfCommand(GDSIfInvocation, BinaryLocalized):
    loc: int = None


@dataclass(kw_only=True)
class BinaryLoopCommand(GDSLoopInvocation, BinaryLocalized):
    loc: int = None


F = TypeVar("F", bound=Callable)


def prevcursor(fn: F) -> F:
    """
    For the CompilerState methods, records the cursor before the function call
    so it can be restored for peeking functionality
    """

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        prev = self.cursor
        val = fn(self, *args, **kwargs)
        self.prev_cursor = prev
        return val

    return wrapper


@dataclass(kw_only=True)
class DecompilerState:
    data: bytes
    len: int
    cursor: int
    prev_cursor: int
    elements: List[GDSElement] = field(default_factory=lambda: [])
    labels: Mapping[int, List[Union[LabelUse, LabelToken]]] = field(
        default_factory=dict
    )
    context: GDSContext = field(default_factory=GDSContext)

    def __init__(self, data: bytes):
        self.data = data
        self.len = int.from_bytes(data[:4], "little")
        self.cursor = 4
        self.prev_cursor = 4
        self.elements = []
        self.labels = {}
        self.context = GDSContext()

    @prevcursor
    def read_bytes(self, l: int) -> bytes:
        val = self.data[self.cursor : self.cursor + l]
        self.cursor += l
        return val

    @prevcursor
    def read_int(self, l: int) -> int:
        return int.from_bytes(self.read_bytes(l), "little")

    @prevcursor
    def read_token(self) -> GDSToken:
        loc = self.cursor
        p_type = self.read_int(2)
        val = None
        if p_type == 0:
            cmd = self.read_int(2)
            val = GDSTokenValue.command(cmd)
        elif p_type == 1:
            val = self.read_int(4)
            val = GDSTokenValue.int(val)
        elif p_type == 2:
            val = struct.unpack("<f", self.read_bytes(4))[0]
            val = GDSTokenValue.float(val)
        elif p_type == 3:
            str_len = self.read_int(2)
            # TODO: max string length depends on the command
            # if str_len > 64:
            #     print(
            #         "WARN: string literal is too long (max is 64 bytes); this may lead to errors in the game."
            #     )
            val = (
                self.read_bytes(str_len)
                .decode("ascii")  # TODO: JP/KO compatibility
                .rstrip("\x00")
            )
            val = GDSTokenValue.str(val)
        elif p_type == 4:
            str_len = self.read_int(2)
            val = (
                self.read_bytes(str_len)
                .decode("ascii")  # TODO: JP/KO compatibility
                .rstrip("\x00")
            )
            val = GDSTokenValue.longstr(val)
        elif p_type == 6:
            addr = self.read_int(4)
            val = GDSTokenValue.saddr(addr)
        elif p_type == 7:
            addr = self.read_int(4)
            val = GDSTokenValue.taddr(addr)
        elif p_type == 8:
            val = GDSTokenValue.NOT()
        elif p_type == 9:
            val = GDSTokenValue.AND()
        elif p_type == 10:
            val = GDSTokenValue.OR()
        elif p_type == 11:
            val = GDSTokenValue.BREAK()
        elif p_type == 12:
            val = GDSTokenValue.fileend()
        elif p_type == 5:
            val = GDSTokenValue.unused5()
        else:
            raise ValueError("Invalid GDS token type")
        return GDSToken(loc=loc, val=val)

    def read_label(self, token: GDSToken) -> LabelToken:
        if token.val not in GDSTokenValue.taddr:
            raise ValueError("Not a target label")
        ltoken = LabelToken(loc=token.loc, addr=GDSAddress(token.val()))

        if (ltoken.loc + 2) not in self.labels:
            self.labels[ltoken.loc + 2] = []
        self.labels[ltoken.loc + 2].append(ltoken)
        self.elements.append(GDSElement.label(ltoken))

        return ltoken

    def read_address(self, token: GDSToken, use: str = "") -> LabelUse:
        if token.val not in GDSTokenValue.saddr:
            raise ValueError("Not a jump address")
        luse = LabelUse(loc=token.loc, addr=GDSAddress(token.val()), use=use)

        if luse.addr not in self.labels:
            self.labels[luse.addr] = []
        self.labels[luse.addr].append(luse)

        return luse

    def name_labels(self):
        label_names = {}
        label_prefix_counter: Mapping[str, int] = {}

        for addr, labels in self.labels.items():
            target = None
            sources = []
            use = None
            for l in labels:
                if isinstance(l, LabelToken):
                    target = l
                else:
                    sources.append(l)
                    use = l.use if use is None or use == l.use else ""
            if use is None:
                use = ""
            if target is None:
                i = 0
                for x in self.elements:
                    if x.loc >= addr + 4:
                        break
                    i += 1
                target = LabelToken(loc=addr - 2, addr=None)
                labels.insert(target)
                self.elements.insert(i, target)

            # name the label according to its use
            prefix = f"{use}_" if use != "" else ""
            if prefix not in label_prefix_counter:
                label_prefix_counter[prefix] = 1
            counter = label_prefix_counter[prefix]
            label_prefix_counter[prefix] += 1
            name = prefix + str(counter)
            label_names[addr] = name

            # set which address is the primary one, if any
            for s in sources:
                if s.loc + 2 == target.addr:
                    s.primary = True
                    target.pointsto = s
                    break

            # # Fold if/elif/else and loop blocks if possible
            # # i.e. the corresponding label is only used by the one ifelseloop jump,
            # # and it jumps forward so a block even makes sense
            # # TODO: I need to combine all the labels before a statement together
            # if len(sources) == 1 and sources[0].addr >= sources[0].loc+6:
            #     pass
        return label_names


def read_gds(data: bytes, path: str = None) -> GDSProgram:
    ctx = DecompilerState(data)

    cur_token = ctx.read_token()
    # TODO
    while cur_token.val not in GDSTokenValue.fileend:
        if cur_token.val in GDSTokenValue.command:
            ctx.elements.append(GDSElement.command(read_command(ctx, cur_token)))
        elif cur_token.val in GDSTokenValue.taddr:
            ctx.read_label(cur_token)
        elif cur_token.val in GDSTokenValue.BREAK:
            b = GDSElement.BREAK()
            b.loc: int = cur_token.loc
            ctx.elements.append(b)
        else:
            # The game technically allows this, but it's meaningless nonsense so for now we forbid it
            raise ValueError("Unexpected token type")

        cur_token = ctx.read_token()

    label_names = ctx.name_labels()

    oldlabel_indices = [
        (i, el()) for i, el in enumerate(ctx.elements) if el in GDSElement.label
    ]
    olduse_indices = [
        (el, el().target)
        for el in ctx.elements
        if el in GDSElement.command
        and isinstance(el(), (BinaryIfCommand, BinaryLoopCommand))
        and isinstance(el().target, LabelUse)
    ]

    labels = {}
    for addr, name in label_names.items():
        lst = []
        for i in ctx.labels[addr]:
            if isinstance(i, LabelToken):
                newlabel = GDSLabel(
                    name=name,
                    present=i.addr is not None,
                    loc=i.addr if i.pointsto is None else None,
                )
                for idx, el in oldlabel_indices:
                    if el == i:
                        ctx.elements[idx] = GDSElement.label(newlabel)
                        break
                lst.append(newlabel)
            elif isinstance(i, LabelUse):
                newuse = GDSJumpAddress(label=name, primary=i.primary)
                for el, olduse in olduse_indices:
                    if olduse == i:
                        el().target = newuse
                        break
                lst.append(newuse)
            else:
                raise TypeError()
        labels[name] = lst

    return GDSProgram(
        context=ctx.context, path=path, elements=ctx.elements, labels=labels
    )


def read_condition(
    ctx: DecompilerState, use: str = ""
) -> Tuple[List[GDSConditionToken], LabelUse]:
    cur_token = ctx.read_token()
    cond = []
    while cur_token.val not in GDSTokenValue.saddr:
        if cur_token.val in GDSTokenValue.NOT:
            cond.append(GDSConditionToken.NOT())
        elif cur_token.val in GDSTokenValue.AND:
            cond.append(GDSConditionToken.AND())
        elif cur_token.val in GDSTokenValue.OR:
            cond.append(GDSConditionToken.OR())
        elif cur_token.val in GDSTokenValue.command:
            cond.append(GDSConditionToken.command(read_command(ctx, cur_token)))
        else:
            raise ValueError("Unexpected token type")
        cur_token = ctx.read_token()

    addr = ctx.read_address(cur_token, use)

    return cond, addr


def read_command(ctx: GDSCommand, token: GDSToken) -> BinaryCommand:
    if token.val not in GDSTokenValue.command:
        raise ValueError("Expected instruction")

    cmdid = token.val()
    cmdobj = COMMANDS_BYID.get(cmdid)
    if cmdobj is None:
        raise ValueError(f"Command {cmdid} not defined")

    if cmdobj.complex:
        return (READ_COMPLEX.get(cmdobj.name) or READ_COMPLEX.get(cmdobj.id))(
            ctx, cmdobj
        )

    cmd = read_simple(ctx, cmdobj)
    cmd.loc = token.loc
    return cmd


def read_simple(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryCommand:
    args = []
    for param in cmdobj.params:
        arg = ctx.read_token()
        options = match(
            arg.val,
            {
                GDSTokenValue.int: lambda val: [
                    (GDSValue.int(val), ["int"]),
                    (
                        GDSValue.bool(val),
                        ["bool", "bool|int"],
                    ),
                ],
                GDSTokenValue.float: lambda val: [(GDSValue.float(val), ["float"])],
                GDSTokenValue.str: lambda val: [
                    (GDSValue.str(val), ["string"]),
                    (
                        GDSValue.bool(val),
                        ["bool", "bool|string"],
                    ),
                ],
                GDSTokenValue.longstr: lambda val: [
                    (GDSValue.longstr(val), ["longstr"])
                ],
                ...: lambda: [],
            },
        )
        val = next((v for v, reqtypes in options if param.type in reqtypes), None)
        if val is None:
            if not param.optional:
                raise ValueError(
                    f"Unexpected parameter token type: should have been {param.type}, token was {arg}"
                )
            val = None
            ctx.cursor = ctx.prev_cursor

        args.append(val)
    return BinaryCommand(command=cmdobj, args=args)


def read_if(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryIfCommand:
    cond, addr = read_condition(ctx, "if")

    # this diagnostic is literally just objectively wrong
    # pylint: disable=unexpected-keyword-arg
    return BinaryIfCommand(
        command=cmdobj,
        args=[],
        condition=cond,
        block=[],
        elze=False,
        elseif=False,
        target=addr,
    )


def read_elif(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryIfCommand:
    cond, addr = read_condition(ctx, "elif")

    # this diagnostic is literally just objectively wrong
    # pylint: disable=unexpected-keyword-arg
    return BinaryIfCommand(
        command=cmdobj,
        args=[],
        condition=cond,
        block=[],
        elze=False,
        elseif=True,
        target=addr,
    )


def read_else(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryIfCommand:
    addr = None
    cur_token = ctx.read_token()
    while cur_token.val not in GDSTokenValue.saddr:
        cur_token = ctx.read_token()
    addr = ctx.read_address(cur_token, "else")

    # this diagnostic is literally just objectively wrong
    # pylint: disable=unexpected-keyword-arg
    return BinaryIfCommand(
        command=cmdobj,
        args=[],
        condition=None,
        block=[],
        elze=True,
        elseif=False,
        target=addr,
        loc=None,
    )


def read_repeatN(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryLoopCommand:
    cntt = ctx.read_token()
    if cntt.val not in GDSTokenValue.int:
        raise ValueError(
            f"Unexpected parameter token type: should have been int, token was {cntt}"
        )
    cnt = cntt.val()

    saddrt = ctx.read_token()
    while saddrt.val not in GDSTokenValue.saddr:
        if saddrt.val in GDSTokenValue.fileend:
            raise ValueError("repeatN: encountered EOF looking for jump address")
        saddrt = ctx.read_token()
    addr = ctx.read_address(saddrt, "loop")

    # this diagnostic is literally just objectively wrong
    # pylint: disable=unexpected-keyword-arg
    return BinaryLoopCommand(
        command=cmdobj, condition=cnt, target=addr, args=[], block=[]
    )


def read_while(ctx: DecompilerState, cmdobj: GDSCommand) -> BinaryLoopCommand:
    cond, addr = read_condition(ctx, "loop")

    # this diagnostic is literally just objectively wrong
    # pylint: disable=unexpected-keyword-arg
    return BinaryLoopCommand(
        command=cmdobj, condition=cond, target=addr, args=[], block=[]
    )


READ_COMPLEX = {
    "if": read_if,
    "elif": read_elif,
    "else": read_else,
    "repeatN": read_repeatN,
    "while": read_while,
}


@dataclass(kw_only=True)
class CompilerState:
    data: bytearray
    elements: List[GDSElement]
    labels: Mapping[str, List[Union[GDSLabel, GDSJumpAddress]]]
    label_locs: Mapping[str, Tuple[int, GDSLabel]]
    use_locs: Mapping[str, List[Tuple[int, GDSJumpAddress]]]

    def __init__(self, prog: GDSProgram):
        self.data = bytearray()
        # self.context = prog.context
        self.elements = prog.elements
        self.labels = prog.labels
        self.label_locs = {}
        self.use_locs = {}

    def write_bytes(self, b: bytes):
        self.data += b

    def write_token(self, token: GDSTokenValue):
        els = match(
            token,
            {
                GDSTokenValue.command: lambda val: (
                    (0).to_bytes(2, "little"),
                    val.to_bytes(2, "little"),
                ),
                GDSTokenValue.int: lambda val: (
                    (1).to_bytes(2, "little"),
                    val.to_bytes(4, "little"),
                ),
                GDSTokenValue.float: lambda val: (
                    (2).to_bytes(2, "little"),
                    struct.pack("<f", val),
                ),
                GDSTokenValue.str: lambda val: (
                    (3).to_bytes(2, "little"),
                    (len(val) + 1).to_bytes(2, "little"),
                    val.encode("ascii") + b"\0",
                ),
                GDSTokenValue.longstr: lambda val: (
                    (4).to_bytes(2, "little"),
                    (len(val) + 1).to_bytes(2, "little"),
                    val.encode("ascii") + b"\0",
                ),
                GDSTokenValue.saddr: lambda val: (
                    (6).to_bytes(2, "little"),
                    val.to_bytes(4, "little"),
                ),
                GDSTokenValue.taddr: lambda val: (
                    (7).to_bytes(2, "little"),
                    val.to_bytes(4, "little"),
                ),
                GDSTokenValue.NOT: lambda val: ((8).to_bytes(2, "little"),),
                GDSTokenValue.AND: lambda val: ((9).to_bytes(2, "little"),),
                GDSTokenValue.OR: lambda val: ((10).to_bytes(2, "little"),),
                GDSTokenValue.BREAK: lambda val: ((0xB).to_bytes(2, "little"),),
                GDSTokenValue.fileend: lambda val: ((0xC).to_bytes(2, "little"),),
                GDSTokenValue.unused5: lambda val: ((5).to_bytes(2, "little"),),
            },
        )
        for el in els:
            self.data += el

    def write_command(self, cmd: GDSInvocation):
        self.write_token(GDSTokenValue.command((cmd.command).id))

        if cmd.command.complex:
            (WRITE_COMPLEX.get(cmd.command.name) or WRITE_COMPLEX.get(cmd.command.id))(
                self, cmd
            )
            return

        write_simple(self, cmd)

    def write_label(self, label: GDSLabel):
        if not label.present:
            return

        backptr = label.loc
        label_loc = len(self.data) + 6

        for use_loc, addr in self.use_locs.get(label.name) or []:
            if addr.primary:
                backptr = use_loc
            self.data[use_loc - 4 : use_loc] = label_loc.to_bytes(4, "little")

        self.write_token(GDSTokenValue.taddr(GDSAddress(backptr or 0)))
        self.label_locs[label.name] = (label_loc, label)

    def write_addr(self, addr: GDSJumpAddress):
        label_loc = None
        use_loc = len(self.data) + 6

        if addr.label in self.label_locs:
            label_loc, _ = self.label_locs[addr.label]
            if addr.primary:
                self.data[label_loc - 4 : label_loc] = use_loc.to_bytes(4, "little")

        self.write_token(GDSTokenValue.saddr(GDSAddress(label_loc or 0)))

        if addr.label not in self.use_locs:
            self.use_locs[addr.label] = []
        self.use_locs[addr.label].append((use_loc, addr))


def write_gds(prog: GDSProgram) -> bytes:
    ctx = CompilerState(prog)

    for el in ctx.elements:
        if el in GDSElement.BREAK:
            ctx.write_token(GDSTokenValue.BREAK())
        elif el in GDSElement.command:
            ctx.write_command(el())
        elif el in GDSElement.label:
            ctx.write_label(el())
    
    ctx.write_token(GDSTokenValue.fileend())
    return len(ctx.data).to_bytes(4, 'little') + bytes(ctx.data)


def write_simple(ctx: CompilerState, cmd: GDSInvocation):
    args = cmd.args
    if len(args) < len(cmd.command.params):
        args += [None] * len(cmd.command.params)-len(args)
    for arg, param in zip(args, cmd.command.params):
        if arg is None:
            if param.optional:
                continue
            else:
                raise ValueError("Too few parameters")
        options = match(
            arg,
            {
                GDSValue.int: lambda val: [
                    (GDSTokenValue.int(val), ["int", "bool", "bool|int"]),
                ],
                GDSValue.float: lambda val: [(GDSTokenValue.float(val), ["float"])],
                GDSValue.str: lambda val: [
                    (GDSTokenValue.str(val), ["string", "bool", "bool|string"]),
                ],
                GDSValue.longstr: lambda val: [
                    (GDSTokenValue.longstr(val), ["longstr"])
                ],
                GDSValue.bool: lambda val: 
                    [(GDSTokenValue.int(val), ["bool", "bool|int"])] if isinstance(val, int)
                    else
                    [(GDSTokenValue.str(val), ["bool", "bool|string"])] if isinstance(val, str)
                    else
                    [
                    (GDSTokenValue.int(1 if val else 0), ["bool", "bool|int"]),
                    (
                        GDSTokenValue.str("true" if val else "false"),
                        ["bool", "bool|string"],
                    ),
                ]
                ,
                ...: lambda: [],
            },
        )
        tok = next((v for v, reqtypes in options if param.type in reqtypes), None)
        if tok is None:
            raise ValueError(
                f"Unexpected parameter type: should have been {param.type}, value was {arg}"
            )

        ctx.write_token(tok)


def write_condition(ctx: CompilerState, cond: List[GDSConditionToken]):
    for tok in cond:
        if tok in GDSConditionToken.NOT:
            ctx.write_token(GDSTokenValue.NOT())
        elif tok in GDSConditionToken.AND:
            ctx.write_token(GDSTokenValue.AND())
        elif tok in GDSConditionToken.OR:
            ctx.write_token(GDSTokenValue.OR())
        elif tok in GDSConditionToken.command:
            ctx.write_command(tok())
        else:
            raise ValueError("Unexpected token type")


def write_if(ctx: CompilerState, cmd: GDSIfInvocation):
    write_condition(ctx, cmd.condition)
    ctx.write_addr(cmd.target)


def write_else(ctx: CompilerState, cmd: GDSIfInvocation):
    # write_condition(ctx, cmd.condition)
    ctx.write_addr(cmd.target)


def write_repeatN(ctx: CompilerState, cmd: GDSLoopInvocation):
    ctx.write_token(GDSTokenValue.int(cmd.condition))
    ctx.write_addr(cmd.target)

def write_while(ctx: CompilerState, cmd: GDSLoopInvocation):
    write_condition(ctx, cmd.condition)
    ctx.write_addr(cmd.target)


WRITE_COMPLEX = {
    "if": write_if,
    "elif": write_if,
    "else": write_else,
    "repeatN": write_repeatN,
    "while": write_while,
}
