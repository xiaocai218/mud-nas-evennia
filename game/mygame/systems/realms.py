"""Realm and cultivation progression helpers."""

from .content_loader import load_content


REALM_DATA = load_content("realms")
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
