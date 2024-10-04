import os
import pprint

import unittest

import tqdm

from .gds import read_gds, write_gds
from .gda import read_gda, write_gda, parse_element, CommentContext, format_comment
from .patch import patch
from .value import GDSIntType, GDSIntValue

from utils import RESOURCES


def test_file(gdspath: str, base: str):
    with open(os.path.join(base, gdspath), "rb") as gdsf:
        gdsb = gdsf.read()
    gdsb = patch(gdsb, gdspath)
    prog = read_gds(gdsb, gdspath)
    gdas = write_gda(prog, gdspath, base)
    gdapath = gdspath.replace(".gds", ".gda")
    with open(os.path.join(base, gdapath), "w", encoding="utf8") as gdaf:
        gdaf.write(gdas)

    try:
        reread = read_gda(gdas, gdapath)
    except Exception as e:
        print(f"ERR: {gdapath}: could not read decompiled script: {e}")
        return
    try:
        recompiled = write_gds(reread)
    except Exception as e:
        print(f"ERR: {gdapath}: could not recompile script: {e}")
        return

    if recompiled != gdsb:
        print(
            f"ERR: {gdspath}: Recompiled contents not identical. Result written as {gdspath}2 for comparison."
        )
        with open(os.path.join(base, f"{gdspath}2"), "wb") as gdsf:
            gdsf.write(recompiled)


BASE = os.path.join(RESOURCES, "game_root/lt1_eu")


def test_all(base: str):
    for f in tqdm.tqdm(
        os.path.join(root, f)
        for root, _subdirs, files in os.walk(os.path.join(base, "data/script"))
        for f in files
    ):
        if not f.endswith(".gds"):
            continue
        path = os.path.relpath(f, base)
        test_file(path, base)


def test_comment():
    EXAMPLE = """
    /data/etext/${lang}/e${eventid:r100<=200:03}{pcm}/e${eventid}_t${1}.txt:

    $(/data/etext/${lang}/e${eventid:r100<=200:03}{pcm}/e${eventid}_t${1}.txt)
    """
    print(
        format_comment(
            EXAMPLE,
            CommentContext(
                args=[GDSIntValue(7, GDSIntType())],
                filename="/data/script/event/e6.gds",
                workdir=BASE,
            ),
        )
    )


def test_parsers():
    print(parse_element.parse("if not 0x49:{  #   test \n0x49 # test2\n#test3\n}"))


class TestGDSVanillaFiles(unittest.TestCase):
    """
    A basic parameterized test case, checking if the decompiler is able to decompile and recompile the
    original game scripts and produce identical data.
    
    For this suite to be possible, the original files from the LT1 EU version .nds ROM need to be
    extracted/symlinked into `{flora root dir}/data/game_root/lt1_eu/`, such that the folder contains the
    subfolders `data`, `dwc` and `ftc`. Eventually Flora should support this, but for now you can use Tinke to do it.
    """
    def test_all_files(self):
        """
        Checks if the decompiler is able to disassemble and reassemble each of the unmodified original game scripts.
        This baseline sanity check ensures that merely running `decompile` and then `compile` does not corrupt
        game files.
        """
        base = BASE
        # sourcery skip: no-conditionals-in-tests
        if not os.path.exists(base) or not os.path.isdir(base):
            self.skipTest(
                'Could not find vanilla game files under "data/game_root/lt1_eu". Please make sure '
                "to extract and either copy or symlink the entire contents of a valid LT1 EU version .nds ROM "
                "into that location."
            )
        # sourcery skip: no-loop-in-tests
        for root, _subdirs, files in os.walk(os.path.join(base, "data/script")):
            for f in files:
                if not f.endswith(".gds"):
                    continue
                path = os.path.relpath(os.path.join(root, f), base)
                with self.subTest(msg=f"Check file {path}"):
                    self.single_file(path, base)

    def single_file(self, gdspath: str, base: str):
        with open(os.path.join(base, gdspath), "rb") as f:
            gdsb = f.read()
        # For now we require these known exceptions
        gdsb = patch(gdsb, gdspath)
        try:
            prog = read_gds(gdsb, gdspath)
        except Exception as e:
            self.fail(f"Decompile: {e}")
            raise e
        try:
            gdas = write_gda(prog, gdspath, base)
        except Exception as e:
            self.fail(f"Write GDA: {e}")
            raise e
        
        gdapath = gdspath.replace(".gds", ".gda")
        try:
            prog2 = read_gda(gdas, gdapath)
        except Exception as e:
            self.fail(f"Read GDA: {e}")
            raise e
        try:
            gdsb2 = write_gds(prog2)
        except Exception as e:
            self.fail(f"Recompile: {e}")
            raise e
        
        self.assertEqual(gdsb, gdsb2, "Recompiled result is not identical")

if __name__ == "__main__":
    # test_file("data/script/rooms/room4_param.gds", BASE)
    test_all(BASE)
    # test_parsers()
