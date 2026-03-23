"""Item definitions and inventory helpers."""

import json
from pathlib import Path

from evennia.utils.create import create_object

from .player_stats import apply_exp, get_stats


ITEM_DATA_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "items.json"


def _load_item_data():
    with ITEM_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


ITEM_DEFINITIONS = _load_item_data()
ITEM_DEFINITIONS_BY_ID = {
    item_data["id"]: {"key": item_key, **item_data}
    for item_key, item_data in ITEM_DEFINITIONS.items()
    if item_data.get("id")
}


def get_item_definition(item_key):
    return ITEM_DEFINITIONS.get(item_key)


def get_item_definition_by_id(item_id):
    return ITEM_DEFINITIONS_BY_ID.get(item_id)


def get_item_definition_for_object(item):
    item_id = getattr(item.db, "item_id", None)
    if item_id:
        item_def = get_item_definition_by_id(item_id)
        if item_def:
            return item_def
    return get_item_definition(item.key)


def resolve_item_key(item_key=None, item_id=None):
    if item_key:
        return item_key
    item_def = get_item_definition_by_id(item_id)
    return item_def["key"] if item_def else None


def get_inventory_items(caller):
    return [obj for obj in caller.contents_get(content_type="object") if getattr(obj.db, "is_item", False)]


def find_item(caller, item_name=None, item_id=None):
    for obj in get_inventory_items(caller):
        if item_id and getattr(obj.db, "item_id", None) == item_id:
            return obj
        if item_name and obj.key == item_name:
            return obj
    return None


def create_item(caller, key, desc=None):
    item = create_object("typeclasses.items.Item", key=key, location=caller)
    item_def = get_item_definition(key)
    item.db.desc = desc or (item_def["desc"] if item_def else None)
    item.db.item_id = item_def.get("id") if item_def else None
    return item


def create_loot(caller, key=None, item_id=None, desc=None):
    resolved_key = resolve_item_key(item_key=key, item_id=item_id)
    return create_item(caller, resolved_key, desc=desc) if resolved_key else None


def create_reward_item(caller, key=None, item_id=None, desc=None):
    resolved_key = resolve_item_key(item_key=key, item_id=item_id)
    return create_item(caller, resolved_key, desc=desc) if resolved_key else None


def refine_item(caller, item):
    item_def = get_item_definition_for_object(item)
    refine_exp = item_def.get("refine_exp") if item_def else None
    if not refine_exp:
        return {"ok": False, "reason": "not_refinable"}

    old_realm, new_realm, exp = apply_exp(caller, refine_exp)
    item_key = item.key
    item.delete()
    return {
        "ok": True,
        "item_key": item_key,
        "gain": refine_exp,
        "old_realm": old_realm,
        "new_realm": new_realm,
        "exp": exp,
    }


def use_item(caller, item):
    item_def = get_item_definition_for_object(item)
    use_effect = item_def.get("use_effect") if item_def else None
    if not use_effect:
        return {"ok": False, "reason": "not_usable"}

    stats = get_stats(caller)
    effect_type = use_effect["type"]

    if effect_type == "restore_hp":
        if stats["hp"] >= stats["max_hp"]:
            return {"ok": False, "reason": "hp_full"}
        gain = use_effect["hp"]
        caller.db.hp = min(stats["max_hp"], stats["hp"] + gain)
        recovered = caller.db.hp - stats["hp"]
        item.delete()
        return {
            "ok": True,
            "effect_type": effect_type,
            "text": use_effect["full_text"],
            "hp_gain": recovered,
            "hp_now": caller.db.hp,
            "max_hp": stats["max_hp"],
        }

    if effect_type == "restore_stamina":
        if stats["stamina"] >= stats["max_stamina"]:
            return {"ok": False, "reason": "stamina_full"}
        gain = use_effect["stamina"]
        caller.db.stamina = min(stats["max_stamina"], stats["stamina"] + gain)
        recovered = caller.db.stamina - stats["stamina"]
        item.delete()
        return {
            "ok": True,
            "effect_type": effect_type,
            "text": use_effect["full_text"],
            "stamina_gain": recovered,
            "stamina_now": caller.db.stamina,
            "max_stamina": stats["max_stamina"],
        }

    if effect_type == "restore_both":
        if stats["hp"] >= stats["max_hp"] and stats["stamina"] >= stats["max_stamina"]:
            return {"ok": False, "reason": "all_full"}
        hp_gain = min(stats["max_hp"], stats["hp"] + use_effect["hp"]) - stats["hp"]
        stamina_gain = min(stats["max_stamina"], stats["stamina"] + use_effect["stamina"]) - stats["stamina"]
        caller.db.hp = stats["hp"] + hp_gain
        caller.db.stamina = stats["stamina"] + stamina_gain
        item.delete()
        return {
            "ok": True,
            "effect_type": effect_type,
            "text": use_effect["full_text"],
            "hp_gain": hp_gain,
            "stamina_gain": stamina_gain,
        }

    return {"ok": False, "reason": "unknown_effect"}
