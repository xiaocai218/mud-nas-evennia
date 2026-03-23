"""Helpers for configured world objects."""

from evennia.objects.models import ObjectDB

from systems.items import create_loot
from systems.player_stats import get_stats


def is_readable(target):
    return bool(getattr(target.db, "readable_text", None))


def get_readable_text(target):
    return getattr(target.db, "readable_text", None)


def is_gatherable(target):
    return bool(getattr(target.db, "gather_item", None))


def gather_from_object(caller, target):
    gather_item = getattr(target.db, "gather_item", None)
    cost = int(getattr(target.db, "gather_cost", 0) or 0)
    if not gather_item:
        return {"ok": False, "reason": "not_gatherable"}

    stats = get_stats(caller)
    if stats["stamina"] < cost:
        fail_text = getattr(target.db, "gather_fail_text", None) or "你现在体力不足，没法好好采集。"
        return {"ok": False, "reason": "stamina_low", "cost": cost, "text": fail_text.format(cost=cost)}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    item = create_loot(caller, gather_item)
    text = getattr(target.db, "gather_text", None) or f"你从 {target.key} 上采下了 {gather_item}。"
    return {
        "ok": True,
        "item": item,
        "cost": cost,
        "text": text,
        "stamina_now": caller.db.stamina,
        "max_stamina": stats["max_stamina"],
    }


def is_teleportable(target):
    return bool(getattr(target.db, "teleport_room_key", None))


def teleport_via_object(caller, target):
    room_key = getattr(target.db, "teleport_room_key", None)
    if not room_key:
        return {"ok": False, "reason": "not_teleportable"}

    destination = ObjectDB.objects.filter(db_key=room_key).first()
    if not destination:
        return {"ok": False, "reason": "destination_missing", "text": "这处灵纹如今黯淡无光，似乎暂时无法回应。"}

    caller.move_to(destination, quiet=True)
    text = getattr(target.db, "teleport_text", None) or f"你借 {target.key} 的灵力回到了 {destination.key}。"
    return {"ok": True, "text": text, "destination": destination}
