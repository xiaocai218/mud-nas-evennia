"""Structured action routing layer for future H5/API clients."""

from systems.client_protocol import build_response
from systems.items import find_item, use_item
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
        "talk": _handle_not_implemented,
        "attack": _handle_not_implemented,
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


def _handle_not_implemented(caller, payload):
    return build_response(False, error={"code": "not_implemented"})
