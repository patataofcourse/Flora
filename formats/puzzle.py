import click
import json
import os

from formats import rom

dir_path = "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
puzzles = json.load(open(f"{dir_path}/data/puzzles.json"))

@click.group(help="Simplify puzzle editing: extract or import the files related to a certain puzzle.",options_metavar='')
def cli():
    pass

def load_file(rom, out_dir, file, og_path, out_path="."):
    print(f"Extracting {file}...")
    contents = rom.getFileByName(f"data/{og_path}/{file}")  #maybe "data" is not an essential part?
    f = open(f"{out_dir}/{out_path}/{file}", "wb")
    f.write(contents)
    f.close()

@cli.command(
                name="extract",
                help="Extracts all the files related to a certain puzzle from the ROM into a specific directory",
                no_args_is_help = True,
                options_metavar = "[--lang]"
            )
@click.argument("romfile")
@click.argument("puzzle")
@click.argument("out_dir")
@click.option("--lang", is_flag=True, default = False, help = "Load the game titles in their original language.")
def extract(romfile, puzzle, out_dir, lang):
    romfile, id, title = rom.load(romfile, lang)
    try:
        os.mkdir(out_dir)
    except FileExistsError:
        pass

    print("") #newline lol

    if id.startswith("A5F"): #Curious Village
        #TODO: get files called from the script?

        readme = open(f"{out_dir}/readme.txt", "a")

        puzzle = puzzles["A5F"].get(puzzle)
        if puzzle == None:
            raise Exception("Puzzle provided is not valid! See the readme for a list of valid puzzles.")

        pcm_file = 'q000.pcm' if puzzle < 50 else ('q050.pcm' if puzzle < 100 else 'q100.pcm')
        try:
            os.mkdir(out_dir+ "/bg")
            if puzzle != 0:
                os.mkdir(out_dir+ "/qtext")
            os.mkdir(out_dir+ "/script")
        except FileExistsError:
            pass

        #extract files dependant on language
        if id.endswith("P"):
            print("ROM is PAL - loading game as multilanguage.")
            langs = ('de', 'en', 'es', 'fr', 'it')
            try:
                for lang in langs:
                    os.mkdir(out_dir+ "/bg/" + lang)
                    if puzzle != 0:
                        os.mkdir(out_dir+ "/qtext/" + lang)
                    os.mkdir(out_dir+ "/script/" + lang)
            except FileExistsError:
                pass
            
            bg_lang = True
            bga_lang = True

            try:
                load_file(romfile, out_dir, f"q{puzzle}_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}_bg.arc not found - to be looked in language folders")
            
            try:
                load_file(romfile, out_dir, f"q{puzzle}a_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}a_bg.arc not found - to be looked in language folders")

            for lang in langs:
                if bg_lang:
                    try:
                        load_file(romfile, out_dir, f"{lang}/q{puzzle}_bg.arc", "bg", "bg")
                    except ValueError:
                        print(f"File q{puzzle}_bg.arc not found in language folders.")
                        bg_lang = False
                if bga_lang:
                    try:
                        load_file(romfile, out_dir, f"{lang}/q{puzzle}a_bg.arc", "bg", "bg")
                    except ValueError:
                        print(f"File q{puzzle}a_bg.arc not found in language folders.")
                        bga_lang = False
                load_file(romfile, out_dir, f"{lang}/{pcm_file}", "qtext", "qtext")
                load_file(romfile, out_dir, f"{lang}/qscript.gds", "script/qinfo", "script")
                load_file(romfile, out_dir, f"{lang}/qtitle.gds", "script/puzzletitle", "script")
            
            readme.write(
f'''The files you want from the PCM file are:
    - t_{puzzle}.txt
    - q_{puzzle}.txt
    - h_{puzzle}_1.txt
    - h_{puzzle}_2.txt
    - h_{puzzle}_3.txt
    - f_{puzzle}.txt
    - c_{puzzle}.txt
'''
            )

        elif id.endswith("E"):
            if puzzle == 163:
                raise Exception("Puzzle not available in US version!")
            try:
                load_file(romfile, out_dir, f"q{puzzle}_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}_bg.arc not found")
            try:
                load_file(romfile, out_dir, f"q{puzzle}a_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}a_bg.arc not found")
            load_file(romfile, out_dir, f"t_{puzzle}.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"q_{puzzle}.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_1.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_2.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_3.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"f_{puzzle}.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"c_{puzzle}.txt", "qtext/en", "qtext")
            load_file(romfile, out_dir, f"qscript.gds", "script/qinfo/en", "script")
            load_file(romfile, out_dir, f"qtitle.gds", "script/puzzletitle/en", "script")
        
        elif id.endswith("J"):
            if puzzle == 163:
                raise Exception("Puzzle not available on JP version!")
            try:
                load_file(romfile, out_dir, f"q{puzzle}_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}_bg.arc not found")
            try:
                load_file(romfile, out_dir, f"q{puzzle}a_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}a_bg.arc not found")
            load_file(romfile, out_dir, f"t_{puzzle}.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"q_{puzzle}.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_1.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_2.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"h_{puzzle}_3.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"f_{puzzle}.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"c_{puzzle}.txt", "qtext", "qtext")
            load_file(romfile, out_dir, f"qscript.gds", "script/qinfo", "script")
            load_file(romfile, out_dir, f"qtitle.gds", "script/puzzletitle", "script")
        
        elif id.endswith("K"):
            try:
                load_file(romfile, out_dir, f"q{puzzle}_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}_bg.arc not found - looking in /ko folder")
                try:
                    load_file(romfile, out_dir, f"q{puzzle}_bg.arc", "bg/ko", "bg")
                except ValueError:
                    print(f"File q{puzzle}_bg.arc not found in /ko folder")
            try:
                load_file(romfile, out_dir, f"q{puzzle}a_bg.arc", "bg", "bg")
            except ValueError:
                print(f"File q{puzzle}a_bg.arc not found - looking in /ko folder")
                try:
                    load_file(romfile, out_dir, f"q{puzzle}a_bg.arc", "bg/ko", "bg")
                except ValueError:
                    print(f"File q{puzzle}a_bg.arc not found in /ko folder")
            load_file(romfile, out_dir, pcm_file, "qtext/ko", "qtext")
            load_file(romfile, out_dir, f"qscript.gds", "script/qinfo/ko", "script")
            load_file(romfile, out_dir, f"qtitle.gds", "script/puzzletitle/ko", "script")

            readme.write(
f'''The files you want from the PCM file are:
    - t_{puzzle}.txt
    - q_{puzzle}.txt
    - h_{puzzle}_1.txt
    - h_{puzzle}_2.txt
    - h_{puzzle}_3.txt
    - f_{puzzle}.txt
    - c_{puzzle}.txt
'''
            )
        else:
            raise Exception(f"Unknown region for game 'A5F': {id[-1]}")

        readme.write (
f'''Inside the qtitle.gds script, look for the line that starts with: 0xba {puzzle}
Inside the pscript.gds script, look for the line that starts with: 0xc3 {puzzle}
Inside the qscript.gds script, look for the line that starts with: 0xdc {puzzle}
'''
        )
        readme.close()

        #extract all files that don't depend on language (the grand total of 3 :P)
        load_file(romfile, out_dir, f"jiten_q{puzzle}.arc", "bg", "bg")
        load_file(romfile, out_dir, f"q{puzzle}_param.gds", "script/qscript", "script")
        load_file(romfile, out_dir, f"pscript.gds", "script/pcarot", "script")

        print("\nDone!")