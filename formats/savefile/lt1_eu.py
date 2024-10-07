from dataclasses import dataclass, field
from enum import IntEnum
from typing import Mapping, Optional, Tuple, Annotated
from ctypes import c_byte, c_int, c_short


class ScriptType(IntEnum):
    RESET = 0
    PUZZLE = 1
    ROOM = 2


@dataclass
class PuzzleFlags:
    discovered: bool = False
    solved: bool = False
    unk: bool = False
    hints_unlocked: int | Tuple[bool, bool, bool] = 0
    """
    Normally when a hint is unlocked, all previous ones are also unlocked;
    but it may technically be possible for that not to be the case.
    """
    fail_count: int = 0
    """
    Counts up to 3
    """

    @classmethod
    def from_byte(cls, data: c_byte) -> "PuzzleFlags":
        hints = (data & 8 != 0, data & 0x10 != 0, data & 0x20 != 0)
        if (hints[0] or not hints[1]) and (hints[1] or not hints[2]):
            hints = 3 if hints[2] else 2 if hints[1] else 1 if hints[0] else 0
        return PuzzleFlags(
            discovered=data & 1 != 0,
            solved=data & 2 != 0,
            unk=data & 4 != 0,
            hints_unlocked=hints,
            fail_count=(data & 0xC0) >> 6,
        )


@dataclass
class StoryStateFlags:
    dog_unlocked: bool = False
    """offset 500"""
    painting_unlocked: bool = False
    """offset 501"""
    hotelroom_unlocked: bool = False
    """offset 502"""

    puzzle_at_nazobaba: Mapping[int, bool] = field(default_factory=dict)
    """
    Set true when a puzzle was sent to Nazobaba (Granny Riddleton).
    offset 800 + <puzzle id>

    TODO: put in the puzzle flags somehow
    """
    pass


class HotelroomPlacement(IntEnum):
    LAYTON = 0
    LUKE = 1
    UNPLACED = 2
    UNDISCOVERED = 3  # TODO: unsure


@dataclass
class Savefile:
    filename: str = "♪ワンボ♪"
    """
    The filename chosen by the player. Max length 20.
    For empty files, replaced with "♪ワンボ♪" in SHIFT-JIS
    (almost certainly a remnant from the Japanese version)
    """
    cur_location: str = "NO DATA"
    """
    The current location of the savefile, displayed on the file select screen.
    Can be set to any nonsense text, and need not match the current room ID,
    but will be corrected on next save. Max length 63.
    For empty files, replaced with "NO DATA"
    """
    playtime: int = 0
    """
    Playtime in seconds, used internally.
    """
    playtime_simple: Tuple[int, int] = (0, 0)
    """
    The simplified playtime, split in (hours, minutes), for direct display
    on the file select screen. Can be set to nonsense that doesn't match
    `playtime`, but will be corrected on next save.
    """
    puzzles_discovered: int = 0
    """
    Number of discovered puzzles, for display on the file select screen
    """
    puzzles_solved: int = 0
    """
    Number of solved puzzles, for display on the file select screen
    """
    game_cleared: bool = False
    """
    Whether the player has finished the game on this file.
    """

    cur_room_id: int = 0
    """
    The current room ID when saving, determines where the player spawns
    back in.
    """
    cur_puzzle_id: int = 0
    """
    Internal state that doesn't actually belong in a savefile:
    the last solved/attempted/relevant puzzle when saving
    """
    cur_puzzle_solved: bool = False
    """
    Internal state that doesn't actually belong in a savefile:
    flag set by the puzzle engine and used by the grader
    """
    cur_puzzle_retry: bool = False
    """
    Internal state that doesn't actually belong in a savefile:
    flag set to true when the user decides to restart a puzzle after
    grading is done (set by user to "Try again")
    """
    cur_puzzle_aborted: bool = False
    """
    Internal state that doesn't actually belong in a savefile:
    flag set to true if the user has quit out of the puzzle. Used
    by the puzzle framework to skip grading.
    """
    cur_script_type: ScriptType = ScriptType.RESET
    """
    The current script type; determines to what state the game will return
    after loading a save. Normally this is ROOM, but one could try if setting
    to (eg.) PUZZLE would work as intended.
    """
    return_script_type: ScriptType = ScriptType.RESET
    """
    For self-contained engines like puzzles or event movies:
    the script type that the game should return to once that engine completes.
    This allows a puzzle to either return to the event that started it, or the
    puzzle index, or the wifi puzzle list etc.
    """
    puzzle_win_img: int = 0
    """
    Internal state that doesn't actually belong in a savefile:
    to my understanding, used to determine which image ID is shown
    on the grading screen if the puzzle is correct
    """
    puzzle_flags: Mapping[int, PuzzleFlags] = field(
        default_factory=lambda: {i: PuzzleFlags() for i in range(256)}
    )

    cur_event: int = 0
    """
    The current event ID when saving, normally the last event played
    right before (or still in progress if the save dialog has been triggered
    by an event). If `cur_script_type` was EVENT, this event would (likely)
    begin right after loading the savefile and watching the recap (unless
    the recap messes up these values)
    """
    event_flags: Mapping[int, bool] = field(
        default_factory=lambda: {i: False for i in range(480)}
    )
    """
    Array of flags, seemingly one for every event. Potentially as simple as
    "has this event been seen before?"
    There are 480 entries, as many as the game handles scripts.
    """
    hint_coins: int = 0
    """
    Number of hint coins. Because you can spend hint coins, this is
    tracked separately from the flags for which specific coins were found.
    """

    inventory: Annotated[list[int], 8] = field(default_factory=list)
    """
    A list of (at most 8) item IDs which are shown to be collected in
    the trunk.
    """

    story_flags: StoryStateFlags = field(default_factory=StoryStateFlags)
    """
    Various story-state related flags are collected here. Collecting
    all of their meanings is WIP.
    """

    cur_objective: int = 0
    """
    The ID of the current objective/mission, as displayed on the top
    screen banner.
    """
    dog_parts_backlog: list[int] = field(default_factory=list)
    """
    List of dog part item IDs that were collected, but not yet placed.
    Used in the minigame to show these parts in collection order.
    """
    dog_parts_placed: Mapping[int, bool] = field(
        default_factory=lambda: {i: False for i in range(32)}
    )
    """
    Flags for each of the dog parts: set true if the part was placed.
    """
    puzzle_pieces_obtained: Mapping[int, bool] = field(
        default_factory=lambda: {i: False for i in range(20)}
    )
    """
    Records for each puzzle piece whether it was obtained already
    """
    puzzle_pieces_location: Mapping[int, int] = field(
        default_factory=lambda: {i: 0xFF for i in range(20)}
    )
    """
    The slot in which each puzzle piece was placed, if any.
    TODO: what's the value for unplaced pieces?
    """

    hotelroom_items: Mapping[int, HotelroomPlacement] = field(
        default_factory=lambda: {i: HotelroomPlacement.UNDISCOVERED for i in range(32)}
    )
    """
    Where each specific hotelroom item is placed.
    """

    news_journal: bool = False
    """
    Whether the Journal in the trunk should have the NEW badge
    """
    news_dog: bool = False
    """
    Whether the Dog/Gizmo minigame should have the NEW badge
    """
    news_hotelroom: bool = False
    """
    Whether the hotelroom minigame should have the NEW image
    """
    news_painting: bool = False
    """
    Whether the painting minigame should have the NEW badge
    """
    news_mysteries: bool = False
    """
    Whether the Mysteries category in the trunk should have the NEW badge
    """
    journal_entries_unread: Mapping[int, bool] = field(
        default_factory=lambda: {i: False for i in range(64)}
    )
    """
    For each of the 45 journal entries, whether each one of them
    is unread.
    """
    dog_name: str = ""
    """
    The name given to the dog after completing the Gizmo minigame
    """

    unk1: c_byte = 0
    unk2: c_byte = 0
    unk3: c_byte = 0
    unk4: c_byte = 0
    unk5: c_int = 0
    unk6: c_short = 0
    unk7: Annotated[list[c_byte], 64] = field(default_factory=list)
    unk8: Annotated[list[c_byte], 64] = field(default_factory=list)
    unk9: c_int = 0
    unk10: Annotated[list[c_byte], 32] = field(default_factory=list)
    unk_bitfield2: Mapping[int, bool] = field(default_factory=dict)
    unk11: c_int = 0
    unk12: c_int = 0


@dataclass
class SaveBonusData:
    pass


@dataclass
class Savedata:
    """
    The entire save data written by the game

    Magic Word: "ATAMFIREBELLNY"
    """

    files: Annotated[list[Optional[Savefile]], 3] = field(
        default_factory=lambda: [None, None, None]
    )
    cur_file: int = 0
    bonus_data: SaveBonusData = field(default_factory=SaveBonusData)


def read_savedata(raw: bytes) -> Savedata:
    data = Savedata()
    if raw[4 : 4 + 14] != b"ATAMFIREBELLNY":
        raise ValueError("Input buffer is not a valid LT1_EU savefile (magic mismatch)")

    hash = int.from_bytes(raw[0:4], "little")
    actual_hash = compute_hash(raw[4:0x150])
    if hash != actual_hash:
        print("WARN: input savefile had invalid global hash; will be accepted anyway")

    data.cur_file = raw[0x14]

    for id in range(3):
        read_file(raw, id, data)

    read_bonus(raw, data)
    pass


def read_file(raw: bytes, id: int, data: Savedata):
    file_present = raw[0x15 + id] != 0
    if not file_present:
        data.files[id] = None
        return
    file = Savefile()

    # Header block
    raw_filename = raw[0x108 + 20 * id : 0x108 + 20 * (id + 1)]
    dec_filename = decode_str(raw_filename)
    if dec_filename is None:
        print("WARN: filename is not a valid encoding")
    file.filename = dec_filename

    raw_location = raw[0x18 + 64 * id : 0x18 + 64 * (id + 1)]
    dec_location = decode_str(raw_location)
    if dec_location is None:
        print("WARN: current location name is not a valid encoding")
    file.cur_location = dec_location

    file.playtime_simple = (
        int.from_bytes(raw[0xE4 + id * 4 : 0xE4 + (id + 1) * 4], "little"),
        int.from_bytes(raw[0xD8 + id * 4 : 0xD8 + (id + 1) * 4], "little"),
    )
    file.puzzles_discovered = int.from_bytes(
        raw[0xF0 + id * 4 : 0xF0 + (id + 1) * 4], "little"
    )
    file.puzzles_solved = int.from_bytes(
        raw[0xFC + id * 4 : 0xFC + (id + 1) * 4], "little"
    )

    file.game_cleared = raw[0x144 + id] != 0

    # File body block
    block_offset = 1000 + 2000 * id
    block = raw[block_offset : block_offset + 2000]
    hash = int.from_bytes(block[0x538 : 0x538 + 4], "little")
    actual_hash = compute_hash(block[:0x538])
    if hash != actual_hash:
        print(f"WARN: input savefile {id+1} has invalid hash; will be accepted anyway")

    file.cur_puzzle_id = block[0x0]
    file.cur_room_id = block[0x1]
    file.cur_puzzle_solved = block[0x2]
    file.cur_puzzle_retry = block[0x3]
    file.cur_puzzle_aborted = block[0x4]
    file.unk1 = block[0x5]
    file.unk2 = block[0x6]
    file.unk3 = block[0x7]
    file.puzzle_win_img = block[0x8]
    file.cur_script_type = block[0x9]
    file.return_script_type = block[0xA]
    file.unk4 = block[0xB]

    file.puzzle_flags = {
        i: PuzzleFlags.from_byte(b) for i, b in enumerate(block[0xC:0x10C])
    }

    file.unk5 = int.from_bytes(block[0x10C:0x110], "little")
    file.cur_event = int.from_bytes(block[0x110:0x114], "little")
    file.event_flags = {i: b != 0 for i, b in enumerate(block[0x114:0x2F4])}
    file.unk6 = int.from_bytes(block[0x2F4:0x2F6], "little")
    file.unk7 = list(block[0x2F6:0x336])
    file.unk8 = list(block[0x336:0x376])

    file.hint_coins = int.from_bytes(block[0x376:0x378], "little")
    file.playtime = int.from_bytes(block[0x378:0x380], "little")
    file.inventory = list(block[0x380:0x388])

    read_storyflags(block, file)

    file.cur_objective = block[0x408]
    file.dog_parts_backlog = list(block[0x409:0x429])
    file.dog_parts_placed = {
        i: b != 0 for i, b in enumerate(expand_flags(block[0x429:0x42D]))
    }
    file.unk9 = int.from_bytes(block[0x42D:0x431], "little")
    file.puzzle_pieces_obtained = {i: b != 0 for i, b in enumerate(block[0x431:0x445])}
    file.puzzle_pieces_location = {i: v for i, v in enumerate(block[0x445:459])}

    hotelroom_locations = [None for _ in range(32)]
    for i in range(32):
        for loc in range(4):
            if block[0x459 + i + 32 * loc] != 0:
                if hotelroom_locations[i] is not None:
                    print(f"WARN: hotelroom item {i} assigned to multiple locations")
                hotelroom_locations[i] = loc
    file.hotelroom_items = hotelroom_locations

    # ??????

    file.news_journal = block[0x4ED]
    file.news_dog = block[0x4EE]
    file.news_hotelroom = block[0x4EF]
    file.news_painting = block[0x4F0]
    file.news_mysteries = block[0x4F1]

    file.unk10 = list(block[0x4F2:0x512])

    file.journal_entries_unread = {
        i: b != 0 for i, b in enumerate(expand_flags(block[0x512:0x51A]))
    }

    file.unk_bitfield2 = expand_flags(block[0x51A:0x51C])
    file.unk11 = int.from_bytes(block[0x51C:0x520], "little")
    file.dog_name = decode_str(block[0x520:0x534])
    file.unk12 = int.from_bytes(block[0x534:0x538], "little")


def read_storyflags(block: bytes, data: Savefile):
    data.story_flags = StoryStateFlags()
    flags = expand_flags(block[0x388:0x408])
    data.story_flags.dog_unlocked = flags[500]
    data.story_flags.painting_unlocked = flags[501]
    data.story_flags.hotelroom_unlocked = flags[502]


def read_bonus(raw: bytes, data: Savedata):
    hash = int.from_bytes(raw[0x1B58:0x1B5C], "little")
    actual_hash = compute_hash(raw[0x1B5C:0x1BD0])
    if hash != actual_hash:
        print(
            "WARN: input savefile bonus section has invalid hash; will be accepted anyway"
        )

    # TODO
    pass


def compute_hash(data: bytes) -> int:
    pass


def decode_str(raw: bytes) -> str:
    raw = raw.rstrip(b'\0')
    encodings_to_try = ["utf8", "shift-jis"]
    for enc in encodings_to_try:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return None


def expand_flags(raw: bytes) -> list[bool]:
    return [b & (1 << i) != 0 for b in raw for i in range(8)]
