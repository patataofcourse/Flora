import json
from ndspy import rom
import os

dir_path = "/".join(os.path.dirname(os.path.realpath(__file__).replace("\\", "/")).split("/")[:-1])
titles = json.load(open(f"{dir_path}/data/titles.json", encoding="utf-8"))

def load(romfile, long=False, layton_only=True):
    print("Loading ROM...")
    romfile = rom.NintendoDSRom.fromFile(romfile)
    print("ROM loaded!")
    
    id = romfile.idCode.decode("ASCII")
    if id not in titles["roms"]:
        raise Exception(f"Game supplied ({id}) is not a Professor Layton DS game!")
    title = ""
    if long:
        title = titles["roms_long"][id]
    else:
        title = titles["roms"][id]
    print(f"Game: {title}")
    
    if layton_only:
        if id not in titles["supported_roms"]:
            raise Exception("Currently, this game is not supported by Flora!")
        elif id not in titles["tested_roms"]:
            print("\nWarning: this game has not been tested properly with Flora, so errors may arise.")
            ans = input("Continue? (y/N) ")
            if ans.lower() != "y":
                quit()
        #TODO: check checksum, to see if it's a modified file or not
    return romfile, id, title