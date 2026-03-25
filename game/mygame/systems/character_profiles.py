"""Character default profile helpers."""

from .content_loader import load_content
from .realms import get_default_realm


CHARACTER_DEFAULTS = load_content("character_defaults")


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
        "copper": int(profile.get("copper", 0) or 0),
        "spirit_stone": int(profile.get("spirit_stone", 0) or 0),
    }
