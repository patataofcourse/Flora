"""
Defines the way values and their types are defined and handled in GDS and GDA.
"""

from abc import ABC, abstractmethod
from typing import Any, Union, Optional, Literal, List
from dataclasses import dataclass

from parsy import regex, string, Parser, seq, success, fail, peek

import formats.gds.gds as gds
from utils import round_perfect

TYPES: List["GDSValueType"] = []


def parse_type(descriptor: str) -> Optional["GDSValueType"]:
    """
    Given a type descriptor (used internally in the GDS command definition files),
    creates a corresponding type object, or returns None if the descriptor is invalid.
    
    See the individual type classes registered in `TYPES` for information on valid
    descriptor formats
    """
    for t in TYPES:
        ty = t.parse_type(descriptor)
        if ty is not None:
            return ty
    return None


class GDSValueType(ABC):
    """
    A GDS Value Type. Defines how a value of this type is created from
    a GDS token or a string parsed in a GDA file.
    """
    @classmethod
    @abstractmethod
    def parse_type(cls, descriptor: str) -> Optional["GDSValueType"]:
        """
        Parses the descriptor and returns the corresponding type object
        if the descriptor corresponds to a variant of this type,
        otherwise returns None to signal the next candidate type should be tried.
        """

    @abstractmethod
    def from_token(self, tok: gds.GDSTokenValue) -> "GDSValue":
        """
        Parses a value of this type from a GDSToken(Value), or returns
        None if there is no way to correspond that token to a value of this type.
        """

    @abstractmethod
    def parser(self) -> Parser:
        """
        Returns a `parsy` parser that attempts to read a value of this type from a GDA script,
        and if so returns a value instance of this type.
        """


class GDSValue(ABC):
    """
    A GDS Value, of a specific `GDSValueType`. Defines how a value
    is printed, either in Python code or in a GDA script,
    and conversion to other value types / GDS tokens.
    """
    type: GDSValueType
    value: Any

    @abstractmethod
    def as_token(self) -> gds.GDSTokenValue:
        """
        Converts the value into a GDSToken(Value). There should
        rarely be a reason for this to fail,
        but if it does this function should return None.
        """

    @abstractmethod
    def __format__(self, format_spec: Optional[str] = None) -> str:
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({format(self)})"

    def write(self) -> str:
        """
        Returns a string representation of this value, as it would be written in a GDA script.
        Separate from Python's format and repr mechanisms, though it corresponds more closely
        to the latter; however some representations in GDA would not be valid repr strings in Python
        (specifically long strings).
        """
        return format(self)


@dataclass
class GDSIntType(GDSValueType):
    """
    An integer type, with a fixed byte length, and a marker whether it is intended to be
    read as an unsigned integer in the game.
    """
    bytelen: int = 4
    unsigned: bool = True

    @classmethod
    def parse_type(cls, descriptor: str) -> "GDSIntType":
        """
        Valid descriptors are:
        int(n): n bytes, signed
        uint(n): n bytes, unsigned
        
        or alternatively the shorthands:
        int / uint: 4 bytes, optionally unsigned
        short / ushort: 2 bytes, optionally unsigned
        byte / ubyte: 1 byte, optionally unsigned
        
        Note that all int values are still written as 4 little endian bytes in GDS files,
        but only a subset of these values is actually read by the game. Note also that
        this hard limits the byte length to 4 at most.
        """
        unsigned = False
        if descriptor.startswith("u"):
            unsigned = True
            descriptor = descriptor[1:]

        if descriptor.startswith("int"):
            if descriptor == "int":
                bytelen = 4
            elif descriptor[3] == "(":
                bytelen = int(descriptor[4:-1])
            else:
                return None
        elif descriptor == "short":
            bytelen = 2
        elif descriptor == "byte":
            bytelen = 1
        else:
            return None
        return GDSIntType(bytelen=bytelen, unsigned=unsigned)

    def from_token(self, tok: gds.GDSTokenValue) -> "GDSIntValue":
        if tok not in gds.GDSTokenValue.int:
            return None
        val = tok()
        if not self.unsigned and val >= (256**self.bytelen)/2:
            val -= 256**self.bytelen
        return GDSIntValue(val, self)

    def parser(self) -> Parser:
        """
        Valid integer literals can include a sign (+-), and can be written in base 10 (default) or
        base 16/2 (prefixed by 0x or 0b respectively). Note that if a dot is found at the end of
        the literal, parsing will fail, as this designates the value as a float instead.
        """
        def parser_map(
            val: int, lit_fmt: Literal["hex", "bin", "dec"] = "dec"
        ) -> "GDSIntValue":
            if self.unsigned:
                if val < 0:
                    new_val = (256**self.bytelen) + val
                    if new_val >= 0:
                        print(
                            f"WARN: assigned negative value {val} to uint; this will be converted "
                            f"to the two's complement in {self.bytelen} bytes ({new_val})"
                        )
                        val = new_val
                    else:
                        print(
                            f"WARN: assigned negative value {val} to uint; this value is out of "
                            f"bounds for a {self.bytelen}-byte int, and cannot be represented in "
                            "two's complement. This WILL lead to errors!"
                        )
                if val >= 256**self.bytelen:
                    print(
                        f"WARN: value {val} is out of bounds for {self.bytelen}-byte uint; "
                        "the value will be stored in full (truncated to 4 bytes due to "
                        f"technical limitations), but only the least significant {self.bytelen} "
                        "bytes will be read."
                    )
            elif val * 2 < -(256**self.bytelen) or val * 2 >= 256**self.bytelen:
                print(
                    f"WARN: value {val} is out of bounds for {self.bytelen}-byte int; "
                    "the value will be stored in full (truncated to 4 bytes due to "
                    f"technical limitations), but only the least significant {self.bytelen} "
                    "bytes will be read."
                )

            return GDSIntValue(val, self, lit_fmt=lit_fmt)

        return (
            regex(r"[+-]?0x[0-9a-fA-F]+").map(lambda i: parser_map(int(i, 16), "hex"))
            | regex(r"[+-]?0b[01]+").map(lambda i: parser_map(int(i, 2), "bin"))
            | regex(r"[+-]?[0-9]+").map(lambda i: parser_map(int(i), "dec"))
        ) << peek(regex(r"[^\.]?"))


TYPES.append(GDSIntType)


class GDSIntValue(GDSValue):
    """
    An integer value. If written in a non-decimal base in a GDA script, this information is
    preserved here (but not after being written to a GDS binary).
    """
    value: int
    lit_fmt: Literal["hex", "bin", "dec"] = "dec"

    def __init__(
        self, value: int, ty: GDSIntType, lit_fmt: Literal["hex", "bin", "dec"] = "dec"
    ):
        self.type = ty
        self.value = value
        self.lit_fmt = lit_fmt

    def as_token(self) -> gds.GDSToken:
        val = self.value
        if val < 0:
            val += 256**self.type.bytelen
        return gds.GDSTokenValue.int(val)

    def __format__(self, format_spec: Optional[str] = None) -> str:
        # sourcery skip: assign-if-exp, reintroduce-else
        if self.lit_fmt == "hex":
            return hex(self.value)
        if self.lit_fmt == "bin":
            return bin(self.value)
        return str(self.value)


class GDSFloatType(GDSValueType):
    """
    A float type, of which there are no variations. It matches the IEEE-754 32-bit float
    specification, though it is stored in little-endian byte order in GDS files.
    """
    @classmethod
    def parse_type(cls, descriptor: str) -> "GDSFloatType":
        return GDSFloatType() if descriptor == "float" else None

    def from_token(self, tok: gds.GDSTokenValue) -> "GDSFloatValue":
        return GDSFloatValue(tok(), self) if tok in gds.GDSTokenValue.float else None

    def parser(self) -> Parser:
        """
        Valid float literals can include a sign (+-), and MUST include a period as well
        as a nonempty int literal to either side of it. Omitting the other will denote it as 0,
        therefore `123.` is a convenient way to write integers explicitly as floats.
        Literals may also include an exponent.
        
        TODO: allow writing integers here? Since we already know where the program expects
        a float due to the command list, we could make a convenient conversion here...
        """
        return regex(r"[+-]?([0-9]+\.|[0-9]*\.[0-9])[0-9]*([eE][+-]?[0-9]+)?").map(
            lambda f: GDSFloatValue(float(f), self)
        )


TYPES.append(GDSFloatType)


class GDSFloatValue(GDSValue):
    """
    A float value. The only interesting aspect is the way it's printed in GDA files:
    since IEEE-754 introduces nasty rounding errors even for simple float values,
    we correct this by attempting to round to the float with the least decimal digits
    which still produces the same value as the original.
    """
    value: float

    def __init__(self, value: float, ty: GDSFloatType):
        self.type = ty
        self.value = value

    def as_token(self) -> gds.GDSToken:
        return gds.GDSTokenValue.float(self.value)

    def __format__(self, format_spec: Optional[str] = None) -> str:
        return str(round_perfect(self.value))


@dataclass
class GDSStringType(GDSValueType):
    """
    A string type, with a maximum buffer length, and a flag indicating whether the game expects
    a "long string". The main difference between the two is that a long string is stored in a
    different buffer, meaning the two types can NOT be substituted for each other!
    """
    maxlen: int = 63
    longstr: bool = False

    @classmethod
    def parse_type(cls, descriptor: str) -> "GDSStringType":
        """
        Valid descriptors are: str, string, longstr (for long strings)
        optionally followed by the buffer length in bytes / characters.
        """
        # NOTE: if the game uses a 64-char buffer internally, remember the null terminator
        # also needs to fit! The length of the corresponding GDS type should then be 63.
        # TODO: I haven't yet determined the game's actual buffer size for both string types...
        if descriptor.startswith("string"):
            longstr = False
            descriptor = descriptor[6:]
        elif descriptor.startswith("str"):
            longstr = False
            descriptor = descriptor[3:]
        elif descriptor.startswith("longstr"):
            longstr = True
            descriptor = descriptor[7:]
        else:
            return None
        if descriptor == "":
            maxlen = 63
        elif descriptor[0] == "(":
            maxlen = int(descriptor[1:-1])
        else:
            return None
        return GDSStringType(maxlen=maxlen, longstr=longstr)

    def from_token(self, tok: gds.GDSTokenValue) -> "GDSStringValue":
        # TODO: this should allow me to make things more flexible later
        if self.longstr:
            return (
                GDSStringValue(tok(), self)
                if tok in gds.GDSTokenValue.longstr
                else None
            )
        else:
            return GDSStringValue(tok(), self) if tok in gds.GDSTokenValue.str else None

    def parser(self) -> Parser:
        """
        Valid literals can be delimited by double quotes or single quotes;
        the chosed quote type will need to be escaped if it appears in the literal.
        Generally most Python string escape sequences should be supported.
        
        Long strings are denoted by prepending a single "l" to the front of the quoted literal.
        """
        def parser_map(args: List[Any]) -> Parser:
            is_longstr: bool = args[0]
            text: str = args[1]
            if is_longstr != self.longstr:
                return fail(
                    f'A {"long" if is_longstr else "regular"} string cannot be '
                    f'used in place of a {"long" if self.longstr else "regular"} string'
                )
            if len(text) > self.maxlen:
                print(
                    f"WARN: String {repr(text)} is too long ({len(text)}, max is {self.maxlen})"
                )
            return success(GDSStringValue(text, self))

        string_part_sq = regex(r"[^'\\]+")
        string_part_dq = regex(r'[^"\\]+')
        string_esc = string("\\") >> (
            string("\\")
            | string("/")
            | string('"')
            | string("'")
            | string("b").result("\b")
            | string("f").result("\f")
            | string("n").result("\n")
            | string("r").result("\r")
            | string("t").result("\t")
            | regex(r"u[0-9a-fA-F]{4}").map(lambda s: chr(int(s[1:], 16)))
        )
        quoted = (
            string('"') >> (string_part_dq | string_esc).many().concat() << string('"')
        ) | (string("'") >> (string_part_sq | string_esc).many().concat() << string("'"))

        return seq(regex("l?").map(lambda s: s != ""), quoted).bind(parser_map)


TYPES.append(GDSStringType)


class GDSStringValue(GDSValue):
    """
    A string value, also denoting whether it was defined as a long string.
    This is currently redundant, since the GDSStringType already determines
    whether a long string is expected; however, in the future interoperability
    of the types might be possible.
    """
    value: str
    longstr: bool

    def __init__(self, value: str, ty: GDSStringType):
        self.type = ty
        self.value = value
        self.longstr = ty.longstr

    def as_token(self) -> gds.GDSToken:
        if self.longstr:
            return gds.GDSTokenValue.longstr(self.value)
        return gds.GDSTokenValue.str(self.value)

    def __format__(self, format_spec: Optional[str] = None) -> str:
        return ("l" if self.longstr else "") + repr(self.value)


@dataclass
class GDSBoolType(GDSValueType):
    """
    A boolean type. This type is virtual, meaning it doesn't actually exist in the GDS
    file format; however it is a useful abstraction for writing GDA scripts, and can be easily
    converted into the GDS format (though this process may be lossy).
    """
    force_rep: Optional[Literal["int", "str"]] = None

    @classmethod
    def parse_type(cls, descriptor: str) -> "GDSBoolType":
        """
        Valid descriptors are:
        bool|int : a bool backed by an integer token. Considered true if the value is != 0.
        bool|string : a bool backed by a string token. Considered true exactly if the value
                        is the string "true" (WARNING: this is very specific and in particular,
                        case-sensitive. Especially for Python developers, accidentally writing
                        "True" and having the game recognize it as false is a serious pitfall!
                        For this reason, we discourage use of this type in its string form.)
        bool : a bool that can be backed by either an integer or a string token;
                the game will check both and uses whichever is applicable!
        """
        if descriptor == "bool":
            return GDSBoolType()
        elif descriptor == "bool|int":
            return GDSBoolType(force_rep="int")
        elif descriptor == "bool|string":
            return GDSBoolType(force_rep="str")
        else:
            return None

    def from_token(self, tok: gds.GDSTokenValue) -> "GDSBoolValue":
        if (tok in gds.GDSTokenValue.int and self.force_rep != "str") or (
            tok in gds.GDSTokenValue.str and self.force_rep != "int"
        ):
            return GDSBoolValue(tok(), self)
        return None

    def parser(self) -> Any:
        """
        `true` and `false` are always valid literals, and will be converted to the required
        backing token type (default is int). Otherwise, if the backing type allows it,
        either a string or an int literal can be used instead.
        
        As all values other than 0/1 or "true"/"false" are flattened into a truth value by
        the game, this is only possible to preserve binary parity between decompiled-then-recompiled
        original scripts (which sometimes show a preference for either type despite the command
        supporting both).
        """
        p = regex(r"true|false").map(lambda b: GDSBoolValue(b == "true", self))
        if self.force_rep != "int":
            p |= GDSStringType().parser().map(lambda v: GDSBoolValue(v.value, self))
        if self.force_rep != "str":
            p |= GDSIntType().parser().map(lambda v: GDSBoolValue(v.value, self))
        return p


TYPES.append(GDSBoolType)


class GDSBoolValue(GDSValue):
    """
    A boolean value, backed either by an actual boolean, or an int or string.
    Note that if the GDSBoolType declares a forced backing type, but the value
    here is encoded as the opposite backing type, the value will be converted
    in a lossy manner (this doesn't matter for the game though.)
    """
    value: Union[bool, int, str]

    def __init__(self, value: bool, ty: GDSBoolType):
        self.type = ty
        self.value = value

    def as_token(self) -> gds.GDSToken:
        preferred_rep = self.type.force_rep or None
        value = self.value
        if isinstance(value, int):
            if preferred_rep == "str":
                if value not in ["true", "false"]:
                    print(
                        f"WARN: assigning string value {repr(value)} (false) to int-backed bool; "
                        "this may lose information, but this information would be ignored "
                        "by the game anyway."
                    )
                value = value != 0
            else:
                preferred_rep = "int"
        elif isinstance(value, str):
            if preferred_rep == "int":
                if value not in [0, 1]:
                    print(
                        f"WARN: assigning int value {value} (true) to string-backed bool; "
                        "this may lose information, but this information would be ignored "
                        "by the game anyway."
                    )
                value = value == "true"
            else:
                preferred_rep = "str"

        if preferred_rep is None:
            preferred_rep = "int"

        if preferred_rep == "int":
            if isinstance(value, bool):
                value = 1 if value else 0
            return gds.GDSTokenValue.int(value)
        elif preferred_rep == "str":
            if isinstance(value, bool):
                value = "true" if value else "false"
            return gds.GDSTokenValue.str(value)
        # unreachable
        return None

    def __format__(self, format_spec: Optional[str] = None) -> str:
        return repr(self.value)
