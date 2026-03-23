"""Help and newbie content loaders."""

import json
from pathlib import Path


HELP_CONTENT_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "help_content.json"


def _load_help_content():
    with HELP_CONTENT_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


HELP_CONTENT = _load_help_content()


def get_newbie_content():
    return HELP_CONTENT["newbie"]


def get_help_entries():
    return HELP_CONTENT["help_entries"]
