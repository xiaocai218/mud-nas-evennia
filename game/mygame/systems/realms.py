"""Realm and cultivation progression helpers."""

REALM_ORDER = [
    ("炼气一层", 0),
    ("炼气二层", 30),
    ("炼气三层", 80),
    ("炼气四层", 150),
]


def get_realm_from_exp(exp):
    realm = REALM_ORDER[0][0]
    for name, threshold in REALM_ORDER:
        if exp >= threshold:
            realm = name
    return realm
