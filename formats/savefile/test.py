from dataclasses import asdict
from formats.savefile.lt1_eu import read_savedata
import yaml


def test_lt1eu(file: str):
    with open(file, 'rb') as f:
        raw = f.read()
    save = read_savedata(raw)
    with open(f"{file}.yml", 'w', encoding="utf-8") as f:
        yaml.safe_dump(asdict(save), f, sort_keys=False)

if __name__ == "__main__":
    test_lt1eu('doc/sample_file.sav')