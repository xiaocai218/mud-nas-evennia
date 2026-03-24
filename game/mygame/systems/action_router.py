"""Structured action routing layer for future H5/API clients."""

from systems.client_protocol import build_response
from systems.chat import send_private_message, send_team_message, send_world_message
from systems.combat import attack_training_target
from systems.items import find_item, use_item
from systems.npc_routes import run_npc_route
from systems.player_stats import get_stats
from systems.quests import get_quest_status_text
from systems.serializers import build_bootstrap_payload, serialize_inventory, serialize_room
from systems.shops import buy_item
from systems.world_objects import (
    gather_from_object,
    get_readable_text,
    is_gatherable,
    is_readable,
    trigger_object,
)


def dispatch_action(caller, action, payload=None):
    payload = payload or {}
    handlers = {
        "bootstrap": _handle_bootstrap,
        "look": _handle_look,
        "move": _handle_move,
        "read": _handle_read,
        "gather": _handle_gather,
        "trigger_object": _handle_trigger_object,
        "use_item": _handle_use_item,
        "buy_item": _handle_buy_item,
        "chat_world": _handle_chat_world,
        "chat_team": _handle_chat_team,
        "chat_private": _handle_chat_private,
        "talk": _handle_talk,
        "attack": _handle_attack,
    }
    handler = handlers.get(action)
    if not handler:
        return build_response(False, error={"code": "unknown_action"})
    return handler(caller, payload)


def _handle_bootstrap(caller, payload):
    return build_response(True, build_bootstrap_payload(caller))


def _handle_look(caller, payload):
    return build_response(True, {"room": serialize_room(caller.location)})


def _handle_move(caller, payload):
    direction = payload.get("direction")
    exit_obj = caller.search(direction, candidates=caller.location.exits, quiet=True)
    if not exit_obj:
        return build_response(False, error={"code": "exit_not_found", "message": f"没有 '{direction}' 这个出口"})

    target = exit_obj[0] if isinstance(exit_obj, list) else exit_obj
    destination = getattr(target, "destination", None)
    if not destination:
        return build_response(False, error={"code": "destination_missing"})

    caller.move_to(destination, quiet=True)
    return build_response(True, {"room": serialize_room(destination)})


def _handle_read(caller, payload):
    target = caller.search(payload.get("target"), location=caller.location)
    if not target or not is_readable(target):
        return build_response(False, error={"code": "target_not_readable"})
    text = get_readable_text(caller, target)
    return build_response(True, {"text": text, "target": target.key})


def _handle_gather(caller, payload):
    target = caller.search(payload.get("target"), location=caller.location)
    if not target or not is_gatherable(target):
        return build_response(False, error={"code": "target_not_gatherable"})
    result = gather_from_object(caller, target)
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason"), "message": result.get("text")})
    return build_response(
        True,
        {
            "text": result.get("text"),
            "inventory": serialize_inventory(caller),
            "stamina": result.get("stamina_now"),
            "max_stamina": result.get("max_stamina"),
        },
    )


def _handle_trigger_object(caller, payload):
    target = caller.search(payload.get("target"), location=caller.location)
    if not target:
        return build_response(False, error={"code": "target_not_found"})
    result = trigger_object(caller, target)
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason"), "message": result.get("text")})
    response = {"text": result.get("text"), "room": serialize_room(caller.location)}
    if result.get("destination"):
        response["room"] = serialize_room(result["destination"])
    return build_response(True, response)


def _handle_use_item(caller, payload):
    item = find_item(caller, item_name=payload.get("target"), item_id=payload.get("item_id"))
    if not item:
        return build_response(False, error={"code": "item_not_found"})
    result = use_item(caller, item)
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason")})
    return build_response(True, {"result": result, "inventory": serialize_inventory(caller)})


def _handle_buy_item(caller, payload):
    result = buy_item(caller, payload.get("target"))
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason"), "message": result.get("currency")})
    return build_response(True, {"result": result, "inventory": serialize_inventory(caller)})


def _build_chat_response(result):
    if not result.get("ok"):
        return build_response(
            False,
            error={"code": result.get("reason"), "message": result.get("text")},
        )
    return build_response(
        True,
        {
            "message": result.get("message"),
            "event": result.get("event"),
            "delivered": result.get("delivered", 0),
            "text": result.get("text", ""),
        },
    )


def _handle_chat_world(caller, payload):
    return _build_chat_response(send_world_message(caller, payload.get("text", "").strip()))


def _handle_chat_team(caller, payload):
    return _build_chat_response(send_team_message(caller, payload.get("text", "").strip()))


def _handle_chat_private(caller, payload):
    return _build_chat_response(
        send_private_message(caller, payload.get("target", "").strip(), payload.get("text", "").strip())
    )


def _handle_talk(caller, payload):
    target = caller.search(payload.get("target"), location=caller.location)
    if not target:
        return build_response(False, error={"code": "target_not_found"})
    if not getattr(target.db, "npc_role", None):
        return build_response(False, error={"code": "target_not_talkable"})

    messages = _capture_messages(caller, lambda: _run_talk_route(caller, target))
    return build_response(
        True,
        {
            "target": target.key,
            "messages": messages,
            "quests_text": get_quest_status_text(caller),
        },
    )


def _handle_attack(caller, payload):
    target = caller.search(payload.get("target"), location=caller.location)
    if not target:
        return build_response(False, error={"code": "target_not_found"})
    if not getattr(target.db, "combat_target", False):
        return build_response(False, error={"code": "target_not_attackable"})

    result = attack_training_target(caller, target)
    if not result.get("ok"):
        return build_response(
            False,
            error={"code": result.get("reason"), "cost": result.get("cost")},
        )

    payload = {
        "result": result,
        "character_stats": get_stats(caller),
        "inventory": serialize_inventory(caller),
    }
    return build_response(True, payload)


def _handle_not_implemented(caller, payload):
    return build_response(False, error={"code": "not_implemented"})


def _run_talk_route(caller, target):
    if run_npc_route(caller, getattr(target.db, "talk_route", None)):
        return
    caller.msg(f"{target.key} 暂时没有更多可说的。")


def _capture_messages(caller, func):
    messages = []
    original_msg = caller.msg

    def _capture(text=None, *args, **kwargs):
        messages.append("" if text is None else str(text))

    caller.msg = _capture
    try:
        func()
    finally:
        caller.msg = original_msg
    return messages
