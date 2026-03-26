"""Shared helpers for normalized entity gender values."""

from copy import deepcopy


GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDER_UNKNOWN = "unknown"

VALID_GENDERS = {GENDER_MALE, GENDER_FEMALE, GENDER_UNKNOWN}
GENDER_LABELS = {
    GENDER_MALE: "男",
    GENDER_FEMALE: "女",
    GENDER_UNKNOWN: "未知",
}
GENDER_ALIASES = {
    "男": GENDER_MALE,
    "male": GENDER_MALE,
    "m": GENDER_MALE,
    "女": GENDER_FEMALE,
    "female": GENDER_FEMALE,
    "f": GENDER_FEMALE,
    "未知": GENDER_UNKNOWN,
    "unknown": GENDER_UNKNOWN,
    "u": GENDER_UNKNOWN,
    "none": GENDER_UNKNOWN,
    "": GENDER_UNKNOWN,
}


def normalize_gender(value, default=GENDER_UNKNOWN):
    if value in VALID_GENDERS:
        return value
    if value is None:
        return default
    key = str(value).strip().lower()
    return GENDER_ALIASES.get(key, default)


def get_gender_label(value, default="未知"):
    return GENDER_LABELS.get(normalize_gender(value), default)


def serialize_gender(value):
    normalized = normalize_gender(value)
    return {
        "gender": normalized,
        "gender_label": get_gender_label(normalized),
    }


def copy_gender_labels():
    return deepcopy(GENDER_LABELS)
