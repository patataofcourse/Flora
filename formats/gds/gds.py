from typing import Tuple, List
import struct

from .model import (
    GDSProgram,
    GDSToken,
    GDSElement,
    GDSInvocation,
    GDSLoopInvocation,
    GDSIfInvocation,
    GDSValue,
    GDSAddress,
    GDSConditionToken
)
from .cmddef import COMMANDS_BYID, GDSCommand

from tagged_union import _
from tagged_union import match


def read_condition(data: bytes, cursor: int) -> Tuple[int, List[GDSConditionToken], GDSAddress]:
    return (cursor, [], GDSAddress(1234))


def read_if(data: bytes, cursor: int, cmdobj: GDSCommand) -> Tuple[int, GDSIfInvocation]:
    cursor, cond, addr = read_condition(data, cursor)
    
    return (cursor, GDSIfInvocation(command=cmdobj, condition=cond, target_addr=addr, args = []))


def read_elif(data: bytes, cursor: int, cmdobj: GDSCommand) -> Tuple[int, GDSIfInvocation]:
    data, res = read_if(data, cursor, cmdobj)
    res.elseif = True
    return (cursor, res)


def read_repeatN(data: bytes, cursor: int, cmdobj: GDSCommand) -> Tuple[int, GDSLoopInvocation]:
    cursor, cntt = read_token(data, cursor)
    if cntt not in GDSToken.int:
        raise ValueError(
            f"Unexpected parameter token type: should have been int, token was {arg}"
        )
    cnt = cntt()

    cursor, saddrt = read_token(data, cursor)
    while saddrt not in GDSToken.saddr:
        cursor, saddrt = read_token(data, cursor)
        if saddrt in GDSToken.fileend:
            raise ValueError("repeatN: encountered EOF looking for jump address")
    addr = saddrt()

    return (cursor, GDSLoopInvocation(command=cmdobj, condition=cnt, target_addr=GDSAddress(addr), args=[]))


def read_while(data: bytes, cursor: int, cmdobj: GDSCommand) -> Tuple[int, GDSLoopInvocation]:
    cursor, cond, addr = read_condition(data, cursor)
    
    return (cursor, GDSLoopInvocation(command=cmdobj, condition=cond, target_addr=addr, args=[]))


def read_simple(
    data: bytes, cursor: int, cmdobj: GDSCommand
) -> Tuple[int, GDSInvocation]:
    args = []
    for param in cmdobj.params:
        cursor, arg = read_token(data, cursor)
        val, reqtypes = match(
            arg,
            {
                GDSToken.int: lambda val: (
                    GDSValue.int(val),
                    ["int", "bool", "bool|int"],
                ),
                GDSToken.float: lambda val: (GDSValue.float(val), ["float"]),
                GDSToken.str: lambda val: (GDSValue.str(val), ["string", "bool"]),
                GDSToken.longstr: lambda val: (GDSValue.longstr(val), ["longstr"]),
                _: lambda: (None, []),
            },
        )
        if param.type not in reqtypes:
            raise ValueError(
                f"Unexpected parameter token type: should have been {param.type}, token was {arg}"
            )

        args.append(val)
    return (cursor, GDSInvocation(command=cmdobj, args=args))


READ_COMPLEX = {
    "if": read_if,
    "elif": read_elif,
    "repeatN": read_repeatN,
    "while": read_while,
}


def read_command(data: bytes, cursor: int, token: GDSToken) -> Tuple[int, GDSInvocation]:
    if token not in GDSToken.command:
        raise ValueError("Expected instruction")
    cmdid = token()
    cmdobj = COMMANDS_BYID.get(cmdid)
    if cmdobj is None:
        raise ValueError(f"Command {cmdid} not defined")

    if cmdobj.complex:
        return (
            READ_COMPLEX.get(cmdobj.name) or READ_COMPLEX.get(cmdobj.id)
        )(data, cursor)
        
    args = []
    for param in cmdobj.params:
        cursor, arg = read_token(data, cursor)
        val, reqtypes = match(
            arg,
            {
                GDSToken.int: lambda val: (
                    GDSValue.int(val),
                    ["int", "bool", "bool|int"],
                ),
                GDSToken.float: lambda val: (
                    GDSValue.float(val),
                    ["float"],
                ),
                GDSToken.str: lambda val: (
                    GDSValue.str(val),
                    ["string", "bool"],
                ),
                GDSToken.longstr: lambda val: (
                    GDSValue.longstr(val),
                    ["longstr"],
                ),
                _: lambda: (None, []),
            },
        )
        if param.type not in reqtypes:
            raise ValueError(
                f"Unexpected parameter token type: should have been {param.type}, token was {arg}"
            )

        args.append(val)
    return GDSInvocation(command=cmdobj, args=args)




def read_token(data: bytes, cursor: int) -> Tuple[int, GDSToken]:
    p_type = int.from_bytes(data[cursor : cursor + 2], "little")
    if p_type == 0:
        cmd = int.from_bytes(data[cursor + 2 : cursor + 4], "little")
        return (cursor + 4, GDSToken.command(cmd))
    if p_type == 1:
        val = int.from_bytes(data[cursor + 2 : cursor + 6], "little")
        return (cursor + 6, GDSToken.int(val))
    if p_type == 2:
        val = struct.unpack(">f", data[cursor + 2 : cursor + 6])
        return (cursor + 6, GDSToken.float(val))
    if p_type == 3:
        str_len = int.from_bytes(data[cursor + 2 : cursor + 4], "little")
        if str_len > 64:
            print(
                "WARN: string literal is too long (max is 64 bytes); this may lead to errors in the game."
            )
        val = (
            data[cursor + 4 : cursor + 4 + str_len]
                .decode("ascii")  # TODO: JP/KO compatibility
                .rstrip("\x00")
        )
        return (cursor + 4 + str_len, GDSToken.str(val))
    if p_type == 4:
        str_len = int.from_bytes(data[cursor + 2 : cursor + 4], "little")
        val = (
            data[cursor + 4 : cursor + 4 + str_len]
                .decode("ascii")  # TODO: JP/KO compatibility
                .rstrip("\x00")
        )
        return (cursor + 4 + str_len, GDSToken.longstr(val))
    if p_type == 6:
        addr = int.from_bytes(data[cursor + 2 : cursor + 6], "little")
        return (cursor + 6, GDSToken.saddr(addr))
    if p_type == 7:
        addr = int.from_bytes(data[cursor + 2 : cursor + 6], "little")
        return (cursor + 6, GDSToken.taddr(addr))
    if p_type == 8:
        return (cursor + 2, GDSToken.NOT())
    if p_type == 9:
        return (cursor + 2, GDSToken.AND())
    if p_type == 10:
        return (cursor + 2, GDSToken.OR())
    if p_type == 11:
        return (cursor + 2, GDSToken.BREAK())
    if p_type == 12:
        return (cursor + 2, GDSToken.fileend())
    if p_type == 5:
        return (cursor + 2, GDSToken.unused5())
    raise ValueError("Invalid GDS token type")


def read_gds(data: bytes, path: str = None) -> GDSProgram:
    length = int.from_bytes(data[:4], "little")
    cursor = 4
    cmds = []

    cursor, cur_token = read_token(data, cursor)
    # TODO
    while cur_token not in GDSToken.fileend:
        if cur_token in GDSToken.command:
            cursor, cmd = read_command(data, cursor, cur_token)
            cmds.append(cmd)
        elif cur_token in GDSToken.taddr:
            cmds.append(
                GDSElement.target_label(GDSJump(source=cur_token(), target=cursor - 4))
            )
        elif cur_token in GDSToken.BREAK:
            cmds.append(GDSElement.BREAK())
        else:
            raise ValueError("Unexpected token type")

        cursor, cur_token = read_token(data, cursor)

    return GDSProgram(context="all", path=path, tokens=cmds)
