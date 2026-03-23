"""NPC dialogue configuration helpers."""

import json
from pathlib import Path


DIALOGUE_DATA_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "dialogues.json"


def _load_dialogue_data():
    with DIALOGUE_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


DIALOGUE_DATA = _load_dialogue_data()


def get_dialogue(section, key, **kwargs):
    text = DIALOGUE_DATA.get(section, {}).get(key, "")
    return text.format(**kwargs) if kwargs else text
