# GDA: a human-friendly decompilation of GDS

With how significant [GDS](./gds.md) is for controlling this game, obviously modders would be interested in modifying or writing these script files themselves. But that's pretty difficult to do with a binary format that has location-sensitive jump markers... of course we could build a visual editor, but that's extremely
out of scope for Flora.

Incidentally, this problem is identical to the one of writing actual real-world executable programs in machine code. And the easiest solution people came up with was **Assembly**: a slightly more human-readable format, where instructions weren't just numbers but had understandable (or at least decipherable) names, and crucially, label and jump locations would be assembled automatically. While most of us write programs in high-level, sometimes even interpreted languages, Assembly is also still widely used!

And so it only makes sense that, in order to make both the reading and the creation of GDS scripts easier, Flora should include a (dis)assembler. The special dialect we use is called **GDA**, which may stand for  **G**ame **D**ata **A**ssembly. This doc describes our specification of the format's syntax.

## Structure

The GDA specification and compiler were both written by the Flora devs, based on knowledge from the decompilation of the game and its scripts. It's a hopefully good attempt at a readable scripting language matching the feature set of GDS.

A GDA script consists of a few elements:

- An (optional but recommended) version comment at the beginning
- Instructions with parameters
- Jump labels referred to by the jump instructions
- Optional comments

### Comments

At any point in the file, in a new line or after an instruction in the same line, you may use the `#` character to have GDA ignore the entire rest of the line. This is used purely for your own documentation purposes. Unfortunately when re-decompiling a GDS file, the compiler doesn't yet have a way to keep these comments in place.

A special comment of the form `#!version 1.0` can be placed as the first non-empty line of a GDA file, to mark the version of the language that the script was written in. This is useful for the compiler, because it allows disambiguating commands whose names have changed across Flora/GDA versions (due to improved understanding and research).

### Instructions

An instruction is referred to by its name, which comes from a predefined list of commands. Since the instructions in GDS are named neither in the data files nor in the assembly, we took our best guess to name them descriptively and accurately. But as our understanding evolves (or mods add new capabilities to GDS), these names may change over time.

You can ask Flora to print help for a certain command (by name or hex id), or list all known name (and parameter) assignments.

### Parameters

There are four types of parameter values usable in a script:
- Integers, which are just written as regular numbers. Negative numbers are allowed, and sometimes used as sentinel values (markers that denote a special case and are not meant to be interpreted as a number, usually -1). Remember that the value of these numbers needs to fit into 4 bytes, which means it must be in the (inclusive) range from -2^31 to 2^31-1 (alternatively, if you know the number is treated as unsigned positive, you can go from 0 to 2^32-1).  
  > TODO: many commands have a far smaller number range, this should be denoted in their type!

  You are also allowed to write them in different bases, by using the prefixes `0x` for hex, and `0b` for binary. We don't support writing numbers in octal, what the hell. (This means you can add leading zeroes without worrying.)
- Floats, which are also written as numbers, but which contain a decimal point or are written in scientific notation. If you want to force an integer to be a float, just write it like `1234.` (the decimal part is implied zero). Likewise you can omit the integer part for numbers like `.5`. Scientific notation works like it does in most languages, by separating the mantisse and exponent with an `e`.
- Strings, which may contain up to 63 standard ASCII characters, and are enclosed in either single or double quotes. Common escape sequences like line breaks (`\n`), arbitrary ASCII (`\x12`) or escaping the quotes (`\"`) or escape character (`\\`) are supported; but keep in mind that this is separate from the escape mechanisms some instructions use internally (for example, "break page" or "change expression" commands inlined in dialogue text). Backslash escaping is understood and processed only by the GDA compiler.  
  > Technical note: If you want to know why the max length isn't a power of two when 64 is right there: that's because the buffer itself is 64 bytes long, but must keep room for a single null byte at the end of the string. GDA automatically takes care of this for you.
- Long Strings, which work exactly like regular Strings, but may be (practically) as long as you wish! ...they're also completely unused in the game, and you can't use them in places where a regular string is required (maybe someone could make a mod that makes more or even all GDS commands accept them in place of strings). The only reason they even exist seems to be because `0x21 eventTrigger`'s filename seems to have been very long at some point, but it is now simply a format string derived in code (and also completely unused). If you still want to use one, just prepend `l` to the front of a regular string literal `l'like so'`.  
  > TODO: Check other language versions of this game. Perhaps the Asian versions needed more string length since their character set is larger.

### Jump Labels

A jump label denotes a location in the GDS binary file, right before the next instruction after it. They are used for jumps, and physically represented in code as a number pointing to the location that jumps to them (there is only one at all times).

You can define one (or more) jump labels by name in a location in GDA code, by beginning the line with an `@` symbol and writing space-separated label names:
```
@JumpLoc_1 JumpLoc2
print "this is the next instruction after the jump"
```

Referencing a label is equally simple, by just writing `@` before its label name. These references can be used as another type of function parameter:
```
jump @Label
print "This gets skipped"
@Label
print "This gets printed"
```

The GDA compiler will take care of converting these names into their actual binary file locations for you.

In the degenerate case that a jump address doesn't correspond to a physical label at its target location (which seems possible, since that is technically completely unnecessary), this syntax wouldn't produce identical results as its input... So when defining a jump label, you can prepend `!` to (each of) the names, indicating that no label should be created in the binary file. This is mostly for completeness, and you shouldn't ever need to do this in your own scripts, so it's best if you don't.

### `if` statements

In practice there are only a handful of statements which accept an address as a parameter, and all of them do it via special handling: `if`, `elif`, `else`, `repeatN` and `while`. If handled naïvely as described above, the if statement would look roughly like this:

```
if <condition> @else_1
<if block>
@else_1
elif <condifion> @else_2
<elif block>
@else_2
else @endif_1
<else block>
@endif
<stuff that comes after>
```

But that's unnecessarily cluttered, so instead there's special syntax for if blocks that more resembles how other languages do it:

```
if <condition> {
  <if block>
} elif <condition> {
  <elif block>
} else {
  <else block>
}
<stuff that comes after>
```

In detail, the behavior of the commands is as follows:
- `if` will evaluate a condition, and jump if it is `false` (if there is no condition, that's the default). If after jumping it encounters an `elif` as the next instruction, it'll evaluate that condition too and again jump if it is false. If it encounters an `else` as the next instruction, it will always jump to the location it specifies.
- `elif` and `else`, when encountered outside the context of an `if` instruction being executed, will simply discard all tokens before the jump address and always jump there.

Because of the way these functions play together, none of them can always be used as a pure jump instruction without side effects; but the compiler may make an effort to let you know when that did happen.

It is important to note that while all scripts in the base game have well-structured `if` blocks, this may not necessarily be the case for third-party scripts. The main problems arise when non-condition instructions, in particular other jumps, are placed inside a condition block:
- An `if` statement may jump out of the condition block, which is technically fine, but can't be represented with the nice block syntax. In that case we fall back to the basic syntax.
- Similarly, a `loop` may have its end outside of the condition block, and while this will almost certainly crash the game, the basic syntax of the loop section below can be used as fallback.

> TODO: A big problem happens when the condition of an `elif` statement contains a jump: when reached from `if` the condition will be evaluated and the next address read, but when encountered regularly the first address (of the inner if) will be used instead! This actually can't be represented at all, I think... We could solve this by simply refusing to (de)compile files that are so badly malformed, but we need to detect it.

### loop statements

Similarly, loops in their simplest form would be written like this:
```
while <condition>: @endwhile_1
# or
#repeatN <count>: @endwhile_1
<loop body>
@endwhile_1
<stuff that comes after>
```

And likewise, in regular cases this might be simplified to:
```
while <condition> {
# or
#repeatN <count> {
  <loop body>
}
<stuff that comes after>
```

It's possible that there isn't actually a degenerate case here, since the loop statement seems to only really be usable for its intended purpose. The only possible edge case is when the loop doesn't end with a physical jump label, which shouldn't matter and is addressed by using `@!endwhile_1` as described above.

## Compiler

The Compiler and Decompiler are part of Flora, and executable using `flora gds (de)compile` respectively. Its goal is to produce a GDA script that, when reassembled into GDS, produces an identical binary. (The opposite is certainly impossible, since comments are lost, but the logic should obviously be identical.)

If a text file doesn't seem to be a valid GDA script, the compiler will report (hopefully helpful) errors. It will *not* output a faulty binary file, or overwrite/delete existing GDS files with invalid ones.

If a `.gds` file doesn't seem to be a valid script binary, the decompiler will report so. All GDS files in the base game are valid scripts, so if you encounter this while unpacking a fresh ROM, it may be corrupted. This is not guaranteed for third-party files, but all scripts compiled by Flora should be valid as well; if that is not the case, this is a bug you should report to us.

### Versioning

The current version of the GDA language and compiler can be found using `flora gds -v`. This version mostly refers to the command list, of which instruction and parameter names may change in the future; these changes will be documented in the resource files, to ensure the compiler still understands what to do when encountering a script of an older version. It can only recognize this by the script's version comment, which is why you should always include it and match it to your current compiler version. (The decompiler does this automatically.)
