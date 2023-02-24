import json
from pathlib import Path


def to_json(dictionary: dict, filepath: Path) -> None:
    with open(filepath, "w") as outfile:
        json.dump(dictionary, outfile, indent=4)


def from_json(filepath: Path) -> dict:
    with open(filepath, "r") as openfile:
        return json.load(openfile)
