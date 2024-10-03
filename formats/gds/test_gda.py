import os
import pprint

import unittest

import tqdm

from .gds import read_gds, write_gds
import formats.gds.gda as gda
from .patch import patch
from .value import *

from utils import RESOURCES


def test_file(gdspath: str, base: str):
    with open(os.path.join(base, gdspath), "rb") as gdsf:
        gdsb = gdsf.read()
    gdsb = patch(gdsb, gdspath)
    prog = read_gds(gdsb, gdspath)
    gdas = gda.write_gda(prog, gdspath, base)
    gdapath = gdspath.replace(".gds", ".gda")
    with open(os.path.join(base, gdapath), "w", encoding="utf8") as gdaf:
        gdaf.write(gdas)

    try:
        reread = gda.read_gda(gdas, gdapath)
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
        gda.format_comment(
            EXAMPLE,
            gda.CommentContext(
                args=[GDSIntValue(7, GDSIntType())],
                filename="/data/script/event/e6.gds",
                workdir=BASE,
            ),
        )
    )


def test_parsers():
    print(gda.parse_element.parse("if not 0x49:{  #   test \n0x49 # test2\n#test3\n}"))


def test_readfile(gdapath: str, base: str):
    with open(os.path.join(base, gdapath), "r", encoding="utf8") as gdaf:
        gdas = gdaf.read()

    prog = gda.read_gda(gdas, gdapath)
    compiled = write_gds(prog)

    gdspath = gdapath.replace(".gda", ".gds")
    with open(os.path.join(base, gdspath), "rb") as gdsf:
        gdsb = gdsf.read()
    gdsb = patch(gdsb, gdspath)

    assert gdsb == compiled


if __name__ == "__main__":
    # test_file("data/script/event/e49.gds", BASE)
    test_all(BASE)
    # test_parsers()
