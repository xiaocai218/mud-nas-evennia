"""Realm and cultivation progression helpers."""

import json
from pathlib import Path


REALM_DATA_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "realms.json"


def _load_realm_data():
    with REALM_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


REALM_DATA = _load_realm_data()
DEFAULT_REALM = REALM_DATA["default_realm"]
REALM_ORDER = sorted(REALM_DATA["realms"], key=lambda realm: realm["exp_threshold"])


def get_default_realm():
    return DEFAULT_REALM


def get_realm_from_exp(exp):
    realm = DEFAULT_REALM
    for realm_data in REALM_ORDER:
        if exp >= realm_data["exp_threshold"]:
            realm = realm_data["name"]
    return realm
