"""Starter combat helpers."""

from .battle import attack_or_start_battle
from .chat import notify_player
from .enemy_model import get_enemy_definition, get_enemy_sheet, get_loot_table, is_enemy
from .items import create_loot, get_item_definition, get_item_definition_by_id, resolve_item_key
from .player_stats import apply_exp, get_stats
from .quests import mark_combat_kill
from .teams import get_same_area_team_members


def notify_team_combat_kill(caller, target):
    teammates = get_same_area_team_members(caller, include_self=False)
    if not teammates:
        return False
    notify_player(
        caller,
        f"同区域队友已收到你击败 {target.key} 的协同战斗提示。",
        code="combat_team_notice_sent",
    )
    for teammate in teammates:
        notify_player(
            teammate,
            f"队友 {caller.key} 击败了 {target.key}。本次奖励与掉落仍归击杀者个人所有。",
            code="combat_team_notice",
        )
    return True


def attack_enemy(caller, target):
    return attack_or_start_battle(caller, target)


def attack_training_target(caller, target):
    enemy_sheet = get_enemy_sheet(target) if is_enemy(target) else None
    enemy_meta = (enemy_sheet or {}).get("enemy_meta", {})
    enemy_combat = (enemy_sheet or {}).get("combat_stats", {})
    stats = get_stats(caller)
    target_hp = target.db.hp if getattr(target.db, "hp", None) is not None else enemy_combat.get("hp", 30)
    target_max_hp = target.db.max_hp if getattr(target.db, "max_hp", None) is not None else enemy_combat.get("max_hp", 30)

    cost = enemy_meta.get("stamina_cost", getattr(target.db, "stamina_cost", 8) if hasattr(target.db, "stamina_cost") else 8)
    damage = enemy_meta.get("damage_taken", getattr(target.db, "damage_taken", 12) if hasattr(target.db, "damage_taken") else 12)
    reward_exp = enemy_meta.get("reward_exp", getattr(target.db, "reward_exp", 12) if hasattr(target.db, "reward_exp") else 12)
    counter = enemy_meta.get("counter_damage", getattr(target.db, "counter_damage", 6) if hasattr(target.db, "counter_damage") else 6)
    loot = get_loot_table(target) if is_enemy(target) else {
        "drop_item_id": getattr(target.db, "drop_item_id", None),
        "drop_key": getattr(target.db, "drop_key", None),
        "drop_desc": getattr(target.db, "drop_desc", None),
    }
    drop_item_id = loot.get("drop_item_id")
    drop_key = loot.get("drop_key") or resolve_item_key(item_id=drop_item_id)
    drop_desc = loot.get("drop_desc") or (
        (get_item_definition(drop_key) or {}).get("desc") if drop_key else (get_item_definition_by_id(drop_item_id) or {}).get("desc")
    )

    if stats["stamina"] < cost:
        return {"ok": False, "reason": "stamina", "cost": cost, "stats": stats}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    target_hp -= damage

    if target_hp <= 0:
        old_realm, new_realm, exp = apply_exp(caller, reward_exp)
        target.db.hp = target_max_hp
        if getattr(target.db, "combat_stats", None):
            target.db.combat_stats = {**target.db.combat_stats, "hp": target_max_hp}
        mark_combat_kill(caller, target)
        notify_team_combat_kill(caller, target)
        drop = None
        if drop_key and drop_desc:
            drop = create_loot(caller, key=drop_key, item_id=drop_item_id, desc=drop_desc)
        message = f"击败 {target.key}，获得修为 +{reward_exp}。"
        if drop:
            message += f" 掉落：{drop.key}。"
        notify_player(caller, message, code="combat_reward")
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
    if getattr(target.db, "combat_stats", None):
        target.db.combat_stats = {**target.db.combat_stats, "hp": target_hp}
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
