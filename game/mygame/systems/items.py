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


def get_item_definition(item_key):
    return ITEM_DEFINITIONS.get(item_key)


def get_inventory_items(caller):
    return [obj for obj in caller.contents_get(content_type="object") if getattr(obj.db, "is_item", False)]


def find_item(caller, item_name):
    return next((obj for obj in get_inventory_items(caller) if obj.key == item_name), None)


def create_item(caller, key, desc=None):
    item = create_object("typeclasses.items.Item", key=key, location=caller)
    item_def = get_item_definition(key)
    item.db.desc = desc or (item_def["desc"] if item_def else None)
    return item


def create_loot(caller, key, desc=None):
    return create_item(caller, key, desc=desc)


def create_reward_item(caller, key, desc=None):
    return create_item(caller, key, desc=desc)


def refine_item(caller, item):
    item_def = get_item_definition(item.key)
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
    item_def = get_item_definition(item.key)
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
