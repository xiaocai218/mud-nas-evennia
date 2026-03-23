"""Starter combat helpers."""

from .items import create_loot
from .player_stats import apply_exp, get_stats
from .quests import mark_combat_kill


def attack_training_target(caller, target):
    stats = get_stats(caller)
    target_hp = target.db.hp if target.db.hp is not None else 30
    target_max_hp = target.db.max_hp if target.db.max_hp is not None else 30

    cost = 8
    damage = target.db.damage_taken if target.db.damage_taken is not None else 12
    reward_exp = target.db.reward_exp if target.db.reward_exp is not None else 12
    counter = target.db.counter_damage if target.db.counter_damage is not None else 6
    drop_key = target.db.drop_key
    drop_desc = target.db.drop_desc

    if stats["stamina"] < cost:
        return {"ok": False, "reason": "stamina", "cost": cost, "stats": stats}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    target_hp -= damage

    if target_hp <= 0:
        old_realm, new_realm, exp = apply_exp(caller, reward_exp)
        target.db.hp = target_max_hp
        mark_combat_kill(caller, target)
        drop = None
        if drop_key and drop_desc:
            drop = create_loot(caller, drop_key, drop_desc)
        return {
            "ok": True,
            "result": "kill",
            "cost": cost,
            "reward_exp": reward_exp,
            "old_realm": old_realm,
            "new_realm": new_realm,
            "exp": exp,
            "drop": drop,
            "target_name": target.key,
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
        "target_name": target.key,
    }
