# Savefile Format documentation (for LT1 EU)

**Total length:** 0x2000 (8192)

## Header

**Starts at:** 0  
**Length:** 0x150 (336)

```
0x000   w: hash of the following data
0x004   b[14]: magic word "ATAMFIREBELLNY"
0x012   ?x2
0x014   b: current / last saved file
0x015   b[3]: file present? (bool)
0x018   b[64][3]: current location name (or "NO DATA")
0x0d8   w[3]: playtimeMinutes
0x0e4   w[3]: playtimeHours
0x0f0   w[3]: puzzlesDiscovered
0x0fc   w[3]: puzzlesSolved
0x108   b[20][3]: savefile name (or 0x81f4838f8393837b81f4, which decodes to "♪ワンボ♪" in SHIFT-JIS)
0x144   b[3]: savefile cleared? (bool)
0x147   ?x9
```

**Padding:** 0x150 to 0x3e8, filled with 0xff

## Savefiles

**Starts at:** 0x3e8 (1000), 0xbb8 (3000), 0x1388 (5000)  
**Length:** 0x7d0 (2000)

If a file is not present, this region is filled with 0xff instead.

```
0x000   b: current puzzle ID (internal)
0x001   b: current room ID
0x002   b: current puzzle solved? (bool)
0x003   b: current puzzle should be retried? (bool)
0x004   b: current puzzle was aborted without solving? (bool)
0x005   ?
0x006   ?
0x007   ?
0x008   b: puzzle win image
0x009   b: current script type
0x00a   b: return script type (when script type is eg PUZZLE, a puzzle will begin, and when it ends this type will be started)
0x00b   b: move mode (whether or not the boot was pressed and the exits shown. They were not.)
0x00c   b[256]: puzzle flags
        # -------1: discovered
        # ------1-: solved
        # -----1--: ? (seems to always be set together with solved, at least for story puzzles)
        # --111---: least to most significant: hints 1-3 unlocked
        # 11------: number of previous failed attempts
0x10c   w: is the current script executed right after a puzzle ended? (nonsense in a savefile)
0x110   w: current event
0x114   b[480]: event flags (8bit[])
        # 257: hotelroom completed
        # 258: painting completed
        # 259: game completed
0x2f4   hw: global story progress?? Chapter number??
0x2f6   b[64]: engine played before? (bool[])
0x336   b[64]: hint coins collected (bitfield)
0x376   hw: hint coint count
0x378   dw: playtime (in seconds)
0x380   b[8]: inventory
0x388   b[128]: various story flags
        # 500-502: dog/painting/hotel unlocked
        # 506: challenges unlocked (probably by clearing the game or any minigame)
        # 507-509: dog/hotel/painting completed
        # 511: All puzzles except the last Layton's Challenges complete
        # 512: game cleared
        # puzzleid+800: puzzle sent to nazobaba
        # 300-319: mystery discovered
        # 320-339: mystery solved
0x408   b: current objective
0x409   b[32]: dog collected (but not placed) part list
0x429   b[4]: dog part placed? (bitfield)
0x42d   w: picarat count
0x431   b[20]: puzzle pieces obtained? (list of bool)
0x445   b[20]: puzzle pieces placed slot
0x459   b[20]: puzzle pieces placed rotation
0x46d   b[32]: hotelroom layton
0x48d   b[32]: hotelroom luke
0x4ad   b[32]: ?
0x4cd   b[32]: ?
0x4ed   b: journal has news?
0x4ee   b: dog has news?
0x4ef   b: hotelroom has news?
0x4f0   b: painting has news?
0x4f1   b: mysteries has news?
0x4f2   b[32]: puzzle favorites (bitfield)
0x512   b[8]: journal entry unread flags
0x51a   b[2]: mysteries unread? (bitfield)
0x51c   w: recap event ID
0x520   b[20]: dogname
0x534   w: clues given by dog
0x538   w: hash of all previous data

# ~0x53c to ~0x7d0: padding 0
```

## Postfix

**Starts at:** 0x1b58 (7000)  
**Length:** 0x78 (120)

```
0x1b58  w: hash of the following data
0x1b5c  w: number of downloadable puzzles
0x1b60  w: number of downloadable puzzles (again???)
        # I believe one of these values stores how many puzzle have been downloaded,
        # while the other stores how many WILL ever be downloadable. We can't really
        # test the distinction now, because the game service is down... maybe the
        # program that simulates it knows what these mean.
0x1b64  struct[27]: Wifi puzzles
  ~0x0  b: puzzle ID (yes all the downloadable puzzles are already in the files, and unlocked by ID)
  ~0x1  b: date of release: day
  ~0x2  b: date of release: month
  ~0x3  b: date of release: year (relative to 2000)
```

**Padding:** 0x1bd0 to 0x2000, filled with 0xff