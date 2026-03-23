"""Shared JSON content loading helpers."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "world" / "data"
_CONTENT_CACHE = {}
CONTENT_SPECS = {
    "items": {"source": "items", "container": None, "kind": "dict", "key_field": "key", "id_field": "id"},
    "enemies": {"source": "enemies", "container": None, "kind": "dict", "key_field": "enemy_key", "id_field": "id"},
    "rooms": {"source": "rooms", "container": "rooms", "kind": "dict", "key_field": "room_key", "id_field": "content_id"},
    "npcs": {"source": "npcs", "container": "npcs", "kind": "list", "key_field": "key", "id_field": "id"},
    "objects": {"source": "objects", "container": "objects", "kind": "list", "key_field": "key", "id_field": "id"},
    "main_stages": {"source": "quests", "container": "main_stages", "kind": "dict", "key_field": "state", "id_field": "id"},
    "side_quests": {"source": "quests", "container": "side_quests", "kind": "dict", "key_field": "quest_key", "id_field": "id"},
}


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
    if name in CONTENT_SPECS:
        name = CONTENT_SPECS[name]["source"]
    _CONTENT_CACHE.pop(name, None)


def list_content_names():
    return sorted(CONTENT_SPECS.keys())


def get_content_records(name):
    spec = CONTENT_SPECS.get(name)
    if not spec:
        return []

    data = load_content(spec["source"])
    container = data.get(spec["container"]) if spec["container"] else data
    if spec["kind"] == "dict":
        return [{spec["key_field"]: record_key, **record_data} for record_key, record_data in container.items()]
    return [{**record} for record in container]


def find_content_record(name, lookup):
    spec = CONTENT_SPECS.get(name)
    if not spec:
        return None

    for record in get_content_records(name):
        if record.get(spec["id_field"]) == lookup:
            return record
        if record.get(spec["key_field"]) == lookup:
            return record
    return None


def get_content_summary():
    summary = []
    for name in list_content_names():
        summary.append({"name": name, "count": len(get_content_records(name))})
    return summary
