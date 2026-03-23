"""Structured event envelope helpers for future H5/WebSocket clients."""

import time


def emit_event(event_name, payload=None, scope="character", target_id=None):
    return {
        "type": "event",
        "event": event_name,
        "scope": scope,
        "target_id": target_id,
        "ts": int(time.time()),
        "payload": payload or {},
    }


def stats_updated(payload):
    return emit_event("stats.updated", payload)


def room_updated(payload):
    return emit_event("room.updated", payload)


def inventory_updated(payload):
    return emit_event("inventory.updated", payload)


def quest_updated(payload):
    return emit_event("quest.updated", payload)


def system_notice(message, level="info", code=None):
    payload = {"message": message, "level": level}
    if code:
        payload["code"] = code
    return emit_event("system.notice", payload, scope="system")
