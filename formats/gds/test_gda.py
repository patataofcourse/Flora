import os
import pprint

import unittest

import tqdm

from .gds import read_gds, write_gds
from .gda import read_gda, write_gda
from .patch import patch

from utils import RESOURCES


def test_file(gdspath: str, base: str):
    with open(os.path.join(base, gdspath), "rb") as gdsf:
        gds = gdsf.read()
    gds = patch(gds, gdspath)
    prog = read_gds(gds, gdspath)
    gda = write_gda(prog, gdspath)
    gdapath = gdspath.replace(".gds", ".gda")
    with open(os.path.join(base, gdapath), "w", encoding="utf8") as gdaf:
        gdaf.write(gda)


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


if __name__ == "__main__":
    # test_file("data/script/event/e6.gds", BASE)
    test_all(BASE)
