import os
import pprint

import unittest

from .gds import read_gds, write_gds
from .patch import patch
from utils import RESOURCES

def print_hexdump(data: bytes):
    res = ""
    padstart = 4
    for i in range(padstart):
        if i % 16 == 0:
            res += "\n"
        elif i % 4 == 0:
            res += " "
        res += "## "
        
    i = padstart
    for b in data:
        if i % 16 == 0:
            res += "\n"
        elif i % 4 == 0:
            res += " "
        
        if b < 16:
            res += "0"
        res += hex(b)[2:]
        res += " "
        i += 1
    return res


BASE = os.path.join(RESOURCES, "game_root/lt1_eu")


def test_file(filepath: str, base: str):
    # sourcery skip: use-fstring-for-concatenation

    with open(os.path.join(base, filepath), "rb") as f:
        data = f.read()
    data = patch(data, filepath)
    try:
        prog = read_gds(data, filepath)
    except Exception as e:
        print(f"ERR: {filepath}: could not decompile: {e}")
        return
    try:
        data2 = write_gds(prog)
    except Exception as e:
        print(f"ERR: {filepath}: could not recompile: {e}")
        return
    if data != data2:
        print(
            f"ERR: {filepath}: Recompiled contents not identical. Result written as {filepath}2 for comparison."
        )
        with open(os.path.join(base, filepath + "2"), "wb") as f:
            f.write(data2)
    elif os.path.exists(os.path.join(base, filepath + "2")):
        os.remove(os.path.join(base, filepath + "2"))


# TODO: make this a unit test!
def test_all(base: str):
    for root, _subdirs, files in os.walk(os.path.join(base, "data/script")):
        for f in files:
            if not f.endswith(".gds"):
                continue
            path = os.path.relpath(os.path.join(root, f), base)
            test_file(path, base)

# test_all(BASE)
# test_file("data/script/qscript/q4_param.gds", BASE)

class TestGDSVanillaFiles(unittest.TestCase):
    def test_all_files(self):
        """
        Checks if the decompiler is able to disassemble and reassemble each of the unmodified original game scripts.
        This baseline sanity check ensures that merely running `decompile` and then `compile` does not corrupt
        game files.
        
        Note that for this test to be possible, original files from the LT1 EU version .nds ROM need to be
        extracted/symlinked into `{flora root dir}/data/game_root/lt1_eu/`, such that the folder contains the
        subfolders `data`, `dwc` and `ftc`. Eventually Flora should support this, but for now you can use Tinke to do it.
        """
        base = BASE
# sourcery skip: no-conditionals-in-tests
        if not os.path.exists(base) or not os.path.isdir(base):
            self.skipTest("Could not find vanilla game files under \"data/game_root/lt1_eu\". Please make sure "
                          "to extract and either copy or symlink the entire contents of a valid LT1 EU version .nds ROM "
                          "into that location.")
# sourcery skip: no-loop-in-tests
        for root, _subdirs, files in os.walk(os.path.join(base, "data/script")):
            for f in files:
                if not f.endswith(".gds"):
                    continue
                path = os.path.relpath(os.path.join(root, f), base)
                with self.subTest(msg=f"Check file {path}"):
                    self.single_file(path, base)
    
    def single_file(self, filepath: str, base: str):
        with open(os.path.join(base, filepath), "rb") as f:
            data = f.read()
        data = patch(data, filepath)
        try:
            prog = read_gds(data, filepath)
        except Exception as e:
            self.fail(f"Decompile: {e}")
            raise e
        try:
            data2 = write_gds(prog)
        except Exception as e:
            self.fail(f"Recompile: {e}")
            raise e
        
        self.assertEqual(data, data2, "Recompiled result is not identical")
        # if data != data2:
        #     print(
        #         f"ERR: {filepath}: Recompiled contents not identical. Result written as {filepath}2 for comparison."
        #     )
        #     with open(os.path.join(base, filepath + "2"), "wb") as f:
        #         f.write(data2)
        # elif os.path.exists(os.path.join(base, filepath + "2")):
        #     os.remove(os.path.join(base, filepath + "2"))

