"""Shared JSON content loading helpers."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "world" / "data"
_CONTENT_CACHE = {}


def load_content(name):
    if name not in _CONTENT_CACHE:
        path = DATA_DIR / f"{name}.json"
        with path.open("r", encoding="utf-8") as file_obj:
            _CONTENT_CACHE[name] = json.load(file_obj)
    return _CONTENT_CACHE[name]


def reload_content(name=None):
    if name is None:
        _CONTENT_CACHE.clear()
        return
    _CONTENT_CACHE.pop(name, None)
