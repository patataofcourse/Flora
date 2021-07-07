import os
from formats import bg

os.chdir("../Layton Modding/CV_out/data/data/bg")
for folder in os.walk("."):
    dir = folder[0].lstrip(".")
    os.mkdir(f"out{dir}")
    for file in folder[2]:
        try:
            bg.extract(f"{folder[0]}/{file}", f"out/{folder[0]}/{file}.png")
        except Exception as e:
            print(e)