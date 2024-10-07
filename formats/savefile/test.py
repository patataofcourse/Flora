from formats.savefile.lt1_eu import read_savedata


def test_lt1eu(file: str):
    with open(file, 'rb') as f:
        raw = f.read()
    save = read_savedata(raw)

if __name__ == "__main__":
    test_lt1eu('doc/sample_file.sav')