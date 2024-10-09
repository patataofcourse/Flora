# TODO: what to do with these?
# Do we just provide a baseline patch internally? Or do I expand the GDA language
# to accommodate for these mistakes?
PATCHES = {
    # These scripts use `0x12 if` in a condition, in places where that doesn't seem legal.
    # The game would likely crash if this inner if's condition was ever true. The intention
    # seems to have been to write `if ... and if ...`, which hints at the nature of the scripting
    # language used in the development process! But is still incorrect.
    "data/script/rooms/room4_param.gds": [(0x2B1, b"\0\0\x12\0", b"\x09\0\x09\0")],
    "data/script/rooms/room13_in.gds": [(0x5C, b"\0\0\x12\0", b"\x09\0\x09\0")],
    # Similarly someone might forget that "elseif" is its own command, and write "else if" instead.
    # It's actually possible that this doesn't cause an error though!
    "data/script/rooms/room12_in.gds": [
        (0x127, b"\0\0\x17\0\0\0\x12\0", b"\0\0\x16\0\x09\0\x09\0")
    ],
    # I have no idea about these. Maybe stuff got cut?
    "data/script/rooms/room23_in.gds": [
        (0x18, b"\0\0\x12\0\0\0\x8d\0", b"\0\0\xdf\0\0\0\xdf\0")
    ],
    "data/script/rooms/room24_in.gds": [
        (0x18, b"\0\0\x12\0\0\0\x8d\0", b"\0\0\xdf\0\0\0\xdf\0")
    ],
    # The code says that the second parameter of 0x78 is a float, but it's called with an
    # int here... Apparently in their language it was very easy to accidentally write an integer
    # instead of a float, and there were no compile-time checks for that.
    "data/script/event/e49.gds": [
        (0x24D, b"\x01\0\xfa\xff\xff\xff", b"\x02\0\xc0\0\xc0\0"),
        (0x25D, b"\x01\0\xfa\xff\xff\xff", b"\x02\0\xc0\0\xc0\0"),
    ],
    "data/script/event/e126.gds": [(0x398, b"\x01", b"\x02")],
    "data/script/event/e276.gds": [(0x1B4, b"\x01", b"\x02")],
    "data/script/event/e233.gds": [(0x1F8, b"\x01", b"\x02")],
    "data/script/event/e42.gds": [(0x1C3, b"\x01", b"\x02")],
}
"""
A list of patches to the vanilla scripts, correcting some common mistakes(?).

For some of these it's more obvious than for others that they are incorrect; an example being
command arguments that should be floats but are integers (likely because of a forgotten decimal point).
There are also cases of extremely nonstandard overlapping use of multiple if statements, which would
crash the game in certain cases, but look like they are obviously meant to mean something correct.
"""


def patch(data: bytes, filepath: str) -> bytes:
    if filepath not in PATCHES:
        return data

    data = bytearray(data)

    for start, old, new in PATCHES[filepath]:
        if data[start : start + len(old)] != old:
            print(
                f"WARN: {filepath}: patch at {hex(start)} incorrect: expected {old}, was {data[start:start+len(old)]}"
            )
            continue
        data[start : start + len(old)] = new

    return bytes(data)


def unpatch(data: bytes, filepath: str) -> bytes:
    if filepath not in PATCHES:
        return data

    data = bytearray(data)

    for start, old, new in PATCHES[filepath]:
        if data[start : start + len(new)] != new:
            print(
                f"WARN: {filepath}: patch at {hex(start)} incorrect: expected {new}, was {data[start:start+len(new)]}"
            )
            continue
        data[start : start + len(new)] = old

    return bytes(data)