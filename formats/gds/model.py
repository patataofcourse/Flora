from typing import List, Optional, NewType, Union, Set
from dataclasses import dataclass, field
# pylint: disable=unused-wildcard-import,wildcard-import
from tagged_union import *

from .cmddef import GDSCommand

GDSAddress = NewType('GDSAddress', int)

@tagged_union
class GDSValue:
    """
    A value usable as a parameter in a GDSInvocation.
    """
    int = int
    float = float
    str = str
    longstr = str


@dataclass
class GDSInvocation:
    """
    The specific invocation of a GDS commmand, with the given parameter values.
    """
    command: GDSCommand
    args: List[GDSValue]


@tagged_union
class GDSConditionToken:
    """
    A token that appears in the condition for a flow statement.
    """
    command = GDSInvocation
    NOT = Unit
    AND = Unit
    OR = Unit


@dataclass
class GDSJumpTarget:
    """
    A jump address used by flow instructions in GDS scripts.
    """
    label: str
    """
    The name of the label to be jumped to.
    """


@dataclass
class GDSIfInvocation(GDSInvocation):
    condition: List[GDSConditionToken]
    block: Optional[List["GDSElement"]]
    elseif: bool = False
    elze: bool = False
    target: GDSJumpTarget


@dataclass
class GDSLoopInvocation(GDSInvocation):
    condition: Union[List[GDSConditionToken] | int]
    block: Optional[List["GDSElement"]]
    target: GDSJumpTarget


@dataclass
class GDSLabel:
    """
    A target label from a GDS script file.
    """
    name: str
    """
    The name of the label
    """
    present: bool = True
    """
    Whether the label actually physically exists, or was inserted as the target
    of a jump that didn't point to a target label
    """
    loc: Optional[int] = None
    """
    The location encoded in the physically stored label word.
    Only set if it differs from what would be expected, i.e. the location
    of a jump address pointing to the label.
    """


@tagged_union
class GDSElement:
    """
    An entry in a GDS script file.
    """
    command = GDSInvocation
    label = GDSLabel
    BREAK = Unit


@dataclass
class GDSContext:
    """
    The context that was determined for a GDS script, either manually or by context narrowing.
    
    TODO: find the best way to represent conflicts
    """
    manual_name: Optional[str] = None
    """
    A manual context set on construction, which will never change on narrowing
    """
    candidates: Set[str] = field(default_factory=lambda: ["all"])
    """
    A list of candidate contexts, if any are still applicable. This list will be empty if narrowing caused a conflict.
    """
    conflicts: List[GDSCommand] = field(default_factory=list)
    """
    Whenever an instruction does not match any of the candidate contexts, the offending command is recorded here, and its
    context candidates added to the global candidate list.
    """

    def narrow(self, cmd: GDSCommand) -> bool:
        """
        Checks if the given command is compatible with the currently assumed candidates, and narrows the list if so.
        Otherwise, records the conflict and returns false.
        """
        intersection = GDSContext.intersection([self.manual_name] if self.manual_name else self.candidates, cmd.context)
        if not intersection:
            self.conflicts.append(cmd)
            if not self.manual_name:
                self.candidates = GDSContext.union(self.candidates, cmd.context)
            return False
        if not self.manual_name:
            self.candidates = intersection
        return True

    @staticmethod
    def intersection(n1: Union[str, Set[str]], n2: Union[str, Set[str]]) -> Set[str]:
        if isinstance(n1, list):
            res = set()
            for n in n1:
                res.update(GDSContext.intersection(n, n2))
            return res
        if isinstance(n2, list):
            res = set()
            for n in n2:
                res.update(GDSContext.intersection(n1, n))
            return res

        # sourcery skip: assign-if-exp, reintroduce-else
        if n1 == n2:
            return {n1}
        if n2.startswith(f"{n1}."):
            return {n2}
        if n1.startswith(f"{n2}."):
            return {n1}
        return set()

    @staticmethod
    def union(n1: Union[str, Set[str]], n2: Union[str, Set[str]]) -> Set[str]:
        if isinstance(n1, list):
            res = set()
            for n in n1:
                res.update(GDSContext.intersection(n, n2))
            return res
        if isinstance(n2, list):
            res = set()
            for n in n2:
                res.update(GDSContext.intersection(n1, n))
            return res

        # sourcery skip: assign-if-exp, reintroduce-else
        if n1 == n2:
            return {n1}
        if n2.startswith(f"{n1}."):
            return {n1}
        if n1.startswith(f"{n2}."):
            return {n2}
        return set()


@dataclass
class GDSProgram:
    """
    The program contained in a GDS script file.
    """
    context: Optional[GDSContext] = None
    """
    The execution context of the script, or any candidates for it.
    """
    path: Optional[str] = None
    """
    The file path this script was loaded from, if any.
    """
    elements: List[GDSElement] = field(default_factory=list)
    """
    The instructions or other flow elements in the script.
    """
    labels: List[str] = field(default_factory=list)
    """
    A list of all the labels present in the script. May not technically be necessary.
    """
