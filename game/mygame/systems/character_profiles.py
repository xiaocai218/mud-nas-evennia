"""Character default profile helpers."""

import json
from pathlib import Path

from .realms import get_default_realm


CHARACTER_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "character_defaults.json"


def _load_character_defaults():
    with CHARACTER_DEFAULTS_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


CHARACTER_DEFAULTS = _load_character_defaults()


def get_default_profile_key():
    return CHARACTER_DEFAULTS["default_profile"]


def get_character_profile(profile_key=None):
    profile_key = profile_key or get_default_profile_key()
    profiles = CHARACTER_DEFAULTS.get("profiles", {})
    profile = profiles.get(profile_key, {})
    return {
        "profile_key": profile_key,
        "label": profile.get("label", "默认模板"),
        "realm": profile.get("realm", get_default_realm()),
        "hp": int(profile.get("hp", 100) or 100),
        "max_hp": int(profile.get("max_hp", 100) or 100),
        "stamina": int(profile.get("stamina", 50) or 50),
        "max_stamina": int(profile.get("max_stamina", 50) or 50),
        "exp": int(profile.get("exp", 0) or 0),
    }
