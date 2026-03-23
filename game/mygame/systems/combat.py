"""Starter combat helpers."""

from .items import create_loot
from .player_stats import apply_exp, get_stats
from .quests import mark_dummy_kill


def attack_training_target(caller, target):
    stats = get_stats(caller)
    target_hp = target.db.hp if target.db.hp is not None else 30
    target_max_hp = target.db.max_hp if target.db.max_hp is not None else 30

    cost = 8
    damage = 12
    reward_exp = 12
    counter = 6

    if stats["stamina"] < cost:
        return {"ok": False, "reason": "stamina", "cost": cost, "stats": stats}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    target_hp -= damage

    if target_hp <= 0:
        old_realm, new_realm, exp = apply_exp(caller, reward_exp)
        target.db.hp = target_max_hp
        mark_dummy_kill(caller)
        drop = create_loot(
            caller,
            "青木碎片",
            "一块从青木傀儡身上掉下来的木质碎片，边缘仍留着浅浅灵纹。",
        )
        return {
            "ok": True,
            "result": "kill",
            "cost": cost,
            "reward_exp": reward_exp,
            "old_realm": old_realm,
            "new_realm": new_realm,
            "exp": exp,
            "drop": drop,
        }

    target.db.hp = target_hp
    hp_after = max(0, stats["hp"] - counter)
    caller.db.hp = hp_after
    return {
        "ok": True,
        "result": "hit",
        "cost": cost,
        "counter": counter,
        "target_hp": target_hp,
        "target_max_hp": target_max_hp,
        "hp_after": hp_after,
        "max_hp": stats["max_hp"],
        "stamina_after": caller.db.stamina,
        "max_stamina": stats["max_stamina"],
    }
