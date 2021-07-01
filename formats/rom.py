from ndspy import rom

def load(romfile, long=False):
    print("Loading ROM...")
    romfile = rom.NintendoDSRom.fromFile(romfile)
    print("ROM loaded!")
    
    id = romfile.idCode.decode("ASCII")
    if id not in titles["roms"]:
        print(f"Game supplied ({id}) is not a Professor Layton DS game!")
        quit()
    title = ""
    if long:
        title = titles["roms_long"][id]
    else:
        title = titles["roms"][id]
    print(f"Game: {title}")
    
    if id not in titles["supported_roms"]:
        print("Currently, this game is not supported by Flora!")
        quit()
    elif id not in titles["tested_roms"]:
        print("\nWarning: this game has not been tested properly with Flora, so errors may arise.")
        ans = input("Continue? (y/N) ")
        if ans.lower() != "y":
            quit()
    return romfile, id, title