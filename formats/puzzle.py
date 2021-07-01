import click
import json
import os

from formats import rom

dir_path = "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
puzzles = json.load(open(f"{dir_path}/data/puzzles.json"))

@click.group(help="Simplify puzzle editing: extract or import the files related to a certain puzzle.",options_metavar='')
def cli():
    pass

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

        puzzle = puzzles["A5F"].get(puzzle)
        if puzzle == None:
            raise Exception("Puzzle provided is not valid! See the readme for a list of valid puzzles.")
        
        #directory structure:
        #  puzzle_dir
        #    readme.txt
        #    bg
        #      region folders if needed
        #      q??_bg.arc
        #      jiten_q??.arc
        #    qtext
        #      region folders if needed
        #      q???.pcm
        #    script
        #      region folders if needed
        #      pscript.gds
        #      q??_param.gds
        #      qscript.gds
        #      qtitle.gds
    
        readme = open(f"{out_dir}/readme.txt", "w")
        readme.write(
f'''The files you want from the PCM file are:
    - t_{puzzle}.txt
    - q_{puzzle}.txt
    - h_{puzzle}_1.txt
    - h_{puzzle}_2.txt
    - h_{puzzle}_3.txt
    - f_{puzzle}.txt
    - c_{puzzle}.txt
Inside the qtitle.gds script, look for the line that starts with: 0xba {puzzle}
Inside the pscript.gds script, look for the line that starts with: 0xc3 {puzzle}
Inside the qscript.gds script, look for the line that starts with: 0xdc {puzzle}
'''
        )
        readme.close()

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
            print("ROM is PAL - loading game as multi-region.")
            langs = ('de', 'en', 'es', 'fr', 'it')
            try:
                for lang in langs:
                    os.mkdir(out_dir+ "/bg/" + lang)
                    if puzzle != 0:
                        os.mkdir(out_dir+ "/qtext/" + lang)
                    os.mkdir(out_dir+ "/script/" + lang)
            except FileExistsError:
                pass
        else:
            pass

        #extract all files that don't depend on language (the grand total of 2 :P)
        print(f"Extracting q{puzzle}_param.gds...")
        qparam = open(f"{out_dir}/script/q{puzzle}_param.gds", "wb")
        qparam.write(romfile.getFileByName(f"data/script/qscript/q{puzzle}_param.gds"))
        qparam.close()
        print(f"Extracting pscript.gds...")
        pscript = open(f"{out_dir}/script/pscript.gds", "wb")
        pscript.write(romfile.getFileByName("data/script/pcarot/pscript.gds"))
        pscript.close()

        print("\nDone!")