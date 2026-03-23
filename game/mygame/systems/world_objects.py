"""Helpers for configured world objects."""


def is_readable(target):
    return bool(getattr(target.db, "readable_text", None))


def get_readable_text(target):
    return getattr(target.db, "readable_text", None)
