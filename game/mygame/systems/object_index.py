"""Shared helpers for resolving world objects by content identifiers."""

from evennia.objects.models import ObjectDB


def iter_world_objects():
    return ObjectDB.objects.filter(db_key__isnull=False)


def get_object_by_content_id(content_id):
    if not content_id:
        return None
    for obj in iter_world_objects():
        if getattr(obj.db, "content_id", None) == content_id:
            return obj
    return None
