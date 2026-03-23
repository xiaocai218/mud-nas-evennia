"""Helpers for configured world objects."""

from evennia.objects.models import ObjectDB

from systems.items import create_loot
from systems.player_stats import add_temporary_effect, get_stats
from systems.quests import get_quest_status_text


def is_readable(target):
    return bool(getattr(target.db, "readable_text", None) or getattr(target.db, "quest_hint_title", None))


def get_readable_text(caller, target):
    static_text = getattr(target.db, "readable_text", None)
    if static_text:
        return static_text

    quest_hint_title = getattr(target.db, "quest_hint_title", None)
    if quest_hint_title:
        intro = getattr(target.db, "quest_hint_intro", None) or "碑面上的灵光缓缓聚拢，映出你当前最紧要的方向。"
        return f"{quest_hint_title}\n\n{intro}\n\n{get_quest_status_text(caller)}"

    return None


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


def is_blessable(target):
    return bool(getattr(target.db, "buff_key", None))


def receive_object_blessing(caller, target):
    buff_key = getattr(target.db, "buff_key", None)
    if not buff_key:
        return {"ok": False, "reason": "not_blessable"}

    effect = add_temporary_effect(
        caller,
        buff_key,
        int(getattr(target.db, "buff_bonus", 0) or 0),
        int(getattr(target.db, "buff_duration", 0) or 0),
        getattr(target.db, "buff_label", "灵息加持"),
    )
    text = getattr(target.db, "buff_text", None) or f"{target.key} 上的灵息短暂落在你身上。"
    return {
        "ok": True,
        "text": text,
        "effect": effect,
    }
