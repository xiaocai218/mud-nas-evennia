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


def chat_message(payload):
    return emit_event("chat.message", payload, scope="social")


def chat_message_event(payload):
    return chat_message(payload)


def combat_started(payload):
    return emit_event("combat.started", payload, scope="combat")


def combat_updated(payload):
    return emit_event("combat.updated", payload, scope="combat")


def combat_turn_ready(payload):
    return emit_event("combat.turn_ready", payload, scope="combat")


def combat_action_resolved(payload):
    return emit_event("combat.action_resolved", payload, scope="combat")


def combat_finished(payload):
    return emit_event("combat.finished", payload, scope="combat")


def enqueue_account_event(account, event):
    if not account:
        return
    queue = list(getattr(getattr(account, "db", None), "h5_event_queue", []) or [])
    queue.append(event)
    account.db.h5_event_queue = queue[-50:]


def pop_account_events(account, limit=50):
    if not account:
        return []
    queue = list(getattr(getattr(account, "db", None), "h5_event_queue", []) or [])
    events = queue[:limit]
    account.db.h5_event_queue = queue[limit:]
    return events


def build_event_batch(events=None, cursor=None, transport="poll"):
    events = list(events or [])
    resolved_cursor = cursor if cursor is not None else int(time.time() * 1000)
    return {
        "events": events,
        "cursor": str(resolved_cursor),
        "transport": transport,
        "has_more": False,
    }
