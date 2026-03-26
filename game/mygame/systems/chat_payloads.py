"""Shared chat DTO helpers."""

from systems.realms import build_entity_realm_payload


def serialize_chat_message(channel, text, sender=None, target=None, ts=None, extra=None):
    sender_name = getattr(sender, "key", None) if sender else None
    sender_title = None
    if sender and getattr(sender, "db", None) is not None:
        progression = dict(getattr(sender.db, "progression", None) or {})
        if not progression and getattr(sender.db, "realm", None):
            progression = {"realm": getattr(sender.db, "realm", None)}
        if progression:
            sender_title = build_entity_realm_payload(progression, suffix=sender_name).get("realm_title")
    payload = {
        "channel": channel,
        "sender_id": getattr(sender, "pk", None) if sender else None,
        "sender_name": sender_name,
        "sender_title": sender_title,
        "target_id": getattr(target, "pk", None) if target else None,
        "target_name": getattr(target, "key", None) if target else None,
        "text": text,
        "ts": int(ts or 0),
    }
    if extra:
        payload.update(extra)
    return payload
