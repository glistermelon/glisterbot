import os
import json

files = os.listdir("options")

good = None
with open("info.json") as file:
    good = json.loads(file.read())
good = list(good["answers"].keys())

for file in [file for file in os.listdir("options") if file[:file.index('.')] not in good]:
    os.remove("options/" + file)