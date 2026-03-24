"""Shared chat DTO helpers."""


def serialize_chat_message(channel, text, sender=None, target=None, ts=None, extra=None):
    payload = {
        "channel": channel,
        "sender_id": getattr(sender, "pk", None) if sender else None,
        "sender_name": getattr(sender, "key", None) if sender else None,
        "target_id": getattr(target, "pk", None) if target else None,
        "target_name": getattr(target, "key", None) if target else None,
        "text": text,
        "ts": int(ts or 0),
    }
    if extra:
        payload.update(extra)
    return payload
