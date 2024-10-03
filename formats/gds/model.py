from typing import List, Optional, NewType, Union
from dataclasses import dataclass, field
# pylint: disable=unused-wildcard-import,wildcard-import
from tagged_union import *

from .cmddef import GDSCommand


GDSAddress = NewType('GDSAddress', int)


@dataclass
class GDSInvocation:
    command: GDSCommand
    args: List["GDSValue"]


@tagged_union
class GDSConditionToken:
    command = GDSInvocation
    NOT = Unit
    AND = Unit
    OR = Unit


@dataclass
class GDSIfInvocation(GDSInvocation):
    condition: List[GDSConditionToken]
    elseif: bool = False
    target_addr: GDSAddress


@dataclass
class GDSLoopInvocation(GDSInvocation):
    condition: Union[List[GDSConditionToken] | int]
    target_addr: GDSAddress


@tagged_union
class GDSValue:
    int = int
    float = float
    str = str
    longstr = str


@dataclass
class GDSJump:
    source: GDSAddress
    target: GDSAddress


@tagged_union
class GDSElement:
    command = GDSInvocation
    target_label = GDSJump
    BREAK = Unit


@dataclass
class GDSProgram:
    context: str
    path: Optional[str] = None
    tokens: List[GDSElement] = field(default_factory=list)


@tagged_union
class GDSToken:
    command = int
    int = int
    float = float
    str = str
    longstr = str
    unused5 = Unit
    # the source address is the one pointing to the target
    saddr = GDSAddress
    taddr = GDSAddress
    NOT = Unit
    AND = Unit
    OR = Unit
    BREAK = Unit
    fileend = Unit