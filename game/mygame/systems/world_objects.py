"""Helpers for configured world objects."""

from evennia.objects.models import ObjectDB

from systems.items import create_loot
from systems.player_stats import add_temporary_effect, get_stats
from systems.quests import get_quest_state, get_quest_status_text


def get_object_by_content_id(content_id):
    if not content_id:
        return None
    for obj in ObjectDB.objects.filter(db_key__isnull=False):
        if getattr(obj.db, "content_id", None) == content_id:
            return obj
    return None


def _get_config(target, attr_name, fallback_keys=None):
    config = getattr(target.db, attr_name, None)
    if config:
        return config
    if not fallback_keys:
        return None
    data = {}
    for key in fallback_keys:
        value = getattr(target.db, key, None)
        if value is not None:
            data[key] = value
    return data or None


def _check_requirements(caller, requirements):
    if not requirements:
        return {"ok": True}
    main_state = requirements.get("main_state_is")
    if main_state and get_quest_state(caller) != main_state:
        return {
            "ok": False,
            "reason": "locked",
            "text": requirements.get("fail_text") or "这处入口暂时还不会向你开启。",
        }
    return {"ok": True}


def is_readable(target):
    read_config = _get_config(target, "read_config")
    return bool(read_config or getattr(target.db, "readable_text", None) or getattr(target.db, "quest_hint_title", None))


def get_readable_text(caller, target):
    read_config = _get_config(target, "read_config")
    if read_config:
        read_type = read_config.get("type", "static")
        if read_type == "static":
            return read_config.get("text")
        if read_type == "quest_status":
            title = read_config.get("title") or "|g路碑灵光|n"
            intro = read_config.get("intro") or "碑面上的灵光缓缓聚拢，映出你当前最紧要的方向。"
            return f"{title}\n\n{intro}\n\n{get_quest_status_text(caller)}"

    static_text = getattr(target.db, "readable_text", None)
    if static_text:
        return static_text

    quest_hint_title = getattr(target.db, "quest_hint_title", None)
    if quest_hint_title:
        intro = getattr(target.db, "quest_hint_intro", None) or "碑面上的灵光缓缓聚拢，映出你当前最紧要的方向。"
        return f"{quest_hint_title}\n\n{intro}\n\n{get_quest_status_text(caller)}"

    return None


def is_gatherable(target):
    gather_config = _get_config(target, "gather_config", ["gather_item_id", "gather_item", "gather_cost", "gather_text", "gather_fail_text"])
    return bool(gather_config and (gather_config.get("gather_item_id") or gather_config.get("gather_item")))


def gather_from_object(caller, target):
    gather_config = _get_config(target, "gather_config", ["gather_item_id", "gather_item", "gather_cost", "gather_text", "gather_fail_text"])
    gather_item_id = gather_config.get("gather_item_id") if gather_config else None
    gather_item = gather_config.get("gather_item") if gather_config else None
    cost = int((gather_config or {}).get("gather_cost", 0) or 0)
    if not gather_item and not gather_item_id:
        return {"ok": False, "reason": "not_gatherable"}

    stats = get_stats(caller)
    if stats["stamina"] < cost:
        fail_text = (gather_config or {}).get("gather_fail_text") or "你现在体力不足，没法好好采集。"
        return {"ok": False, "reason": "stamina_low", "cost": cost, "text": fail_text.format(cost=cost)}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    item = create_loot(caller, key=gather_item, item_id=gather_item_id)
    item_name = item.key if item else (gather_item or gather_item_id)
    text = (gather_config or {}).get("gather_text") or f"你从 {target.key} 上采下了 {item_name}。"
    return {
        "ok": True,
        "item": item,
        "cost": cost,
        "text": text,
        "stamina_now": caller.db.stamina,
        "max_stamina": stats["max_stamina"],
    }


def is_teleportable(target):
    trigger_config = _get_config(target, "trigger_effect", ["teleport_room_id", "teleport_room_key", "teleport_text", "locked_text", "required_main_state", "buff_key", "buff_bonus", "buff_duration", "buff_label", "buff_text"])
    if not trigger_config:
        return False
    effect_type = trigger_config.get("type", "teleport")
    if effect_type != "teleport":
        return False
    return bool(trigger_config.get("room_id") or trigger_config.get("teleport_room_id") or trigger_config.get("teleport_room_key"))


def teleport_via_object(caller, target):
    trigger_config = _get_config(target, "trigger_effect", ["teleport_room_id", "teleport_room_key", "teleport_text", "locked_text", "required_main_state"])
    requirements = _get_config(target, "trigger_requirements")
    room_id = (trigger_config or {}).get("room_id") or (trigger_config or {}).get("teleport_room_id")
    room_key = (trigger_config or {}).get("room_key") or (trigger_config or {}).get("teleport_room_key")
    if not room_key and not room_id:
        return {"ok": False, "reason": "not_teleportable"}

    legacy_required_main_state = (trigger_config or {}).get("required_main_state")
    if legacy_required_main_state and not requirements:
        requirements = {"main_state_is": legacy_required_main_state, "fail_text": (trigger_config or {}).get("locked_text")}
    requirement_result = _check_requirements(caller, requirements)
    if not requirement_result["ok"]:
        return requirement_result

    destination = None
    if room_id:
        destination = get_object_by_content_id(room_id)
    if not destination and room_key:
        destination = ObjectDB.objects.filter(db_key=room_key).first()
    if not destination:
        return {"ok": False, "reason": "destination_missing", "text": "这处灵纹如今黯淡无光，似乎暂时无法回应。"}

    caller.move_to(destination, quiet=True)
    text = (trigger_config or {}).get("text") or (trigger_config or {}).get("teleport_text") or f"你借 {target.key} 的灵力回到了 {destination.key}。"
    return {"ok": True, "text": text, "destination": destination}


def is_blessable(target):
    trigger_config = _get_config(target, "trigger_effect", ["buff_key", "buff_bonus", "buff_duration", "buff_label", "buff_text"])
    if not trigger_config:
        return False
    effect_type = trigger_config.get("type", "buff")
    if effect_type != "buff":
        return False
    return bool(trigger_config.get("buff_key"))


def is_triggerable(target):
    return bool(_get_config(target, "trigger_effect", ["teleport_room_id", "teleport_room_key", "buff_key", "required_main_state"]))


def receive_object_blessing(caller, target):
    trigger_config = _get_config(target, "trigger_effect", ["buff_key", "buff_bonus", "buff_duration", "buff_label", "buff_text"])
    buff_key = (trigger_config or {}).get("buff_key")
    if not buff_key:
        return {"ok": False, "reason": "not_blessable"}

    effect = add_temporary_effect(
        caller,
        buff_key,
        int((trigger_config or {}).get("buff_bonus", 0) or 0),
        int((trigger_config or {}).get("buff_duration", 0) or 0),
        (trigger_config or {}).get("buff_label", "灵息加持"),
    )
    text = (trigger_config or {}).get("text") or (trigger_config or {}).get("buff_text") or f"{target.key} 上的灵息短暂落在你身上。"
    return {
        "ok": True,
        "text": text,
        "effect": effect,
    }


def trigger_object(caller, target):
    trigger_config = _get_config(target, "trigger_effect", ["teleport_room_id", "teleport_room_key", "teleport_text", "locked_text", "required_main_state", "buff_key", "buff_bonus", "buff_duration", "buff_label", "buff_text"])
    if not trigger_config:
        return {"ok": False, "reason": "not_triggerable", "text": f"{target.key} 看起来并不会回应你的触碰。"}

    effect_type = trigger_config.get("type")
    if effect_type == "restore":
        stats = get_stats(caller)
        hp_gain = min(stats["max_hp"], stats["hp"] + int(trigger_config.get("hp", 0) or 0)) - stats["hp"]
        stamina_gain = min(stats["max_stamina"], stats["stamina"] + int(trigger_config.get("stamina", 0) or 0)) - stats["stamina"]
        if hp_gain <= 0 and stamina_gain <= 0:
            return {
                "ok": False,
                "reason": "all_full",
                "text": trigger_config.get("full_text") or "你此刻气息平稳、筋骨充盈，暂时用不上这里的灵息。",
            }
        caller.db.hp = stats["hp"] + hp_gain
        caller.db.stamina = stats["stamina"] + stamina_gain
        return {
            "ok": True,
            "text": trigger_config.get("text") or f"{target.key} 中的灵息温和地洗过你的经脉。",
            "hp_gain": hp_gain,
            "stamina_gain": stamina_gain,
            "hp_now": caller.db.hp,
            "max_hp": stats["max_hp"],
            "stamina_now": caller.db.stamina,
            "max_stamina": stats["max_stamina"],
        }
    if effect_type == "buff" or (not effect_type and is_blessable(target)):
        return receive_object_blessing(caller, target)
    if effect_type == "teleport" or not effect_type:
        return teleport_via_object(caller, target)
    return {"ok": False, "reason": "unsupported_trigger", "text": f"{target.key} 暂时还没有可触发的反应。"}
