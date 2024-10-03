# GDS: The Scripting Language of Professor Layton

Most complex events in the Professor Layton game(s) are driven by **GDS** (which may stand for **G**ame **D**ata **S**cript),
a binary scripting language that can trigger events in the currently running
script engine. This is used, among other things, to:

- choose a puzzle engine, and initialize details of the puzzle specific to that engine
- define room layouts, i.e. entities, text objects, hint coins, exits,...
- write out dialogue sequences, including all NPC interactions
- provide localized data for certain minigames and use cases, where it is easier to read a single
  script containing all the definitions into an existing engine, than to open a specific text file
- setup subtitles for the event movies
- It also defines what the logo sequence on bootup looks like. Yes, that is not hardcoded,
  you can change the logo sequence!

While far too many things are still hard-defined in code (such as Puzzle IDs), this makes
the Layton engine fairly data-driven and moddable! It's therefore extremely important to gain
an understanding of this scripting format, to take control of the engine in custom scenarios.

This page describes the basic structure of GDS scripts, according to what we know now. This knowledge
was gained mostly from common-sense guesses about commands that were only used in specific scripts,
as well as a disassembly effort by [@ilonachan](https://github.com/ilonachan). The information here
*may* be limited to the European version of the game, but it seems unlikely the scripting language
would have been changed significantly between regional releases.

This knowledge gives important insights about how **GDA** (which may stand for **G**ame **D**ata **A**ssembly),
a custom language designed to be an easy-to-read decompilation target for GDS, should be structured.

## Structure

In general, all scripts (after their 4-byte length header) are made up of *tokens* of specified type.
The type is defined in two bytes, though it never comes close to using that range:
all possible values (as far as we know so far) are: 

- `0` for executing commands,
- `1,2,3,4` for data parameters,
- `6,7` for jump addressing,
- `8,9,10` for logic operators, and
- `11` and `12` for loop behavior,
- `12` to end the script.

`5` is technically handled in code, but never used and contains no data. All type values higher than 12 will cause the read function to fail and the program to behave unpredictably (including infinite loops).

### Basic Commands

A GDS script consists mostly of these: a type 0 token contains the command ID, and may be followed by multiple
type 1-4 parameter tokens; how many are read is determined by the command's logic itself.

Nearly all of these commands have a static parameter list with fixed meaning, and these commands and their parameters are
defined for programmatic purposes by the YAML files in this directory (split into categories of relevance, because many
commands are only implemented in certain engine contexts).

Certain commands have a more variable parameter list or parsing behavior than the regular ones: these commands are documented in YAML, but their parameter list is specially handled in [the gds parser module](../../formats/gds.py). Specific ones used for control flow are described further down.

Commands may also modify a game-internal conditional flag, which will be described further below.

### Data parameters

The following are all the data type parameters handled:

- `1`: a 4-byte integer
- `2`: a 4-byte floating point number
- `3`: a string, beginning with a 2-byte length, and then that many 1-byte "ASCII" characters (plus null terminator)
- `4`: unknown, but also read as a string

Each command decides which types of data it will read; it will *not* check if the read parameter actually corresponds to that
type, so specifying incorrect types will cause unpredictable error behavior.

### Conditional Jump Instructions

At the core these are also implemented as type-0 instructions, but their "parameter" fetching logic differs significantly.
The most common example is the instruction ensemble `0x12 jumpUnless`, `0x17 jumpIfNotArrived`, and `0x16 jumpChainUnless`.
These would probably be more aptly described as `if`, `else` and `else if` (I haven't 100% confirmed that, but their behavior and use imply this).

To define jump targets, the following tokens are used:

- `6`: a 4-byte jump location within the binary script file. Always seems to point to the beginning of a type-7 token.
- `7`: a 4-byte jump source address within the binary file. Seems to always be the target of a single jump instruction,
       and holds the address of its source. While this doesn't seem strictly required by the jump routine,
       it makes reading and debugging scripts easier, and that's likely why they never bothered to remove it.

`if` and `else if` are obviously not very useful without any conditions to check; for this purpose, a list of type-0 commands (with arguments) are executed right after them, and the conditional flag they returned is incorporated into the boolean expression (note that not all instructions modify the conditional flag, the ones that do are marked in our analysis files).
The conditional chain ends once a type-6 token with a jump address is encountered.

To define complex conditional chains, the following flag tokens can be interspersed with instruction executions:

- `8`: All following commands' condition output is treated as negated.
       Note that while you'd think this flag would only apply to the next command, or be reset by toggling it,
       this is not the case! Once set the flag persists, and there's no way to unset it (within the same conditional).
       They probably never bothered to check this, because I only see this used to negate single conditions.
- `9`:  Changes the mode of how multiple commands' flags are combined: ANDs their results.
- `10`: Changes the mode of how multiple commands' flags are combined: ORs their results.

When writing your own scripts, note the following pitfalls:
- If no conditions are provided, `0x12` will always jump (because the default condition value is false)
- If neither flag 9 or 10 are specified, the result of a new instruction's condition will always overwrite all previous ones,
  until either one is specified.
- The 8 flag may seem like a one-shot or toggle, but internally it actually can't be reset! Once used, all future instruction 
  results will be negated, and there is no easy way around this. Plan your conditionals around this fact, or nest if blocks!
- Using a command that does not produce a conditional output will simply leave the previous one untouched. This is fairly useless
  because there is no short-circuiting, and contitional instructions normally don't modify state to prevent a command from running before the `if` block entirely.  
  But if you choose to do this, keep in mind that the previously negated condition will be negated again! In DISCARD mode this would undo the negate flag's effect (but that's pretty useless because ideally you're only in DISCARD mode in the first instruction), and in AND/OR modes it fixes the value to `false`/`true` respectively (which is also very useless). Therefore, ideally only condition instructions should be used in conditions.

### Loop Instructions

The instructions `0x14 repeatN` and `0x15 while` are assumed to be loops (hence why I named them that). `repeatN` takes a single number parameter for the amount of times to loop, and then simply ignores all tokens until it finds a jump address; `while` consumes a conditional in the same way as `if`, and re-executes it on each loop.

The loop will execute commands until:
1. the GDS instruction pointer exceeds the loop exit address, in which case it will be moved back to the start of the loop (checking conditions)
2. it encounters a type-`11` token (a flag with no data), in which case it will break the loop by jumping to its end (in hex this type is recognizable as `0xb` for **b**reak)
3. it encounters a type-`12` token (a flag with no data), in which case it will abort the loop but leave the program counter as 
   it is. This is not equivalent to the `continue` of most programming languages, rather saying "we don't want to loop anymore, 
   but finish this final iteration".  
   This token is also always found at the end of a script, and I'm still looking for instances outside of that, meaning there is a chance this is simply a failsafe to make sure the loop doesn't continue beyond the script buffer. However, if this behavior seems useful, it doesn't look like using it would have any negative side effects.
4. the next instruction would be `0x4f return`, in which case the loop manually handles to respect the early return.

## Future Work: A Turing Machine in Professor Layton 1

Most script engines only provide a limited number of flags to freely set and access, but maybe this is enough to do a fun proof-of-concept turing machine design.