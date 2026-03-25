"""Battle result builders and snapshot helpers."""

from __future__ import annotations


def build_basic_attack_result(actor, target, damage, applied):
    action_result = _build_action_result(
        action_type="basic_attack",
        card_id="basic_attack",
        source=actor,
        target=target,
        damage=applied["damage"],
        raw_damage=damage,
        guard_reduced=applied["guard_reduced"],
        guard_blocked=applied["guard_blocked"],
        shield_absorbed=applied["shield_absorbed"],
        source_stamina=-3 if actor.get("entity_type") == "player" else 0,
        target_hp_delta=-applied["damage"],
        target_effects_removed=["guard"] if applied["guard_blocked"] or applied["guard_reduced"] else [],
    )
    return {
        "type": "basic_attack",
        "target_id": target["combatant_id"],
        "action_result": action_result,
        "log": {
            "type": "basic_attack",
            "card_id": "basic_attack",
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "target_id": target["combatant_id"],
            "target_name": target["name"],
            "value": applied["damage"],
            "raw_value": damage,
            "shield_absorbed": applied["shield_absorbed"],
            "guard_reduced": applied["guard_reduced"],
            "guard_blocked": applied["guard_blocked"],
            "target_hp": target["hp"],
            "action_result": action_result,
        },
    }


def build_spell_damage_result(actor, target, card, damage, applied):
    mp_cost = int(((card or {}).get("costs") or {}).get("mp", 0) or 0)
    action_result = _build_action_result(
        action_type="skill_card",
        card_id=card["card_id"],
        source=actor,
        target=target,
        damage=applied["damage"],
        raw_damage=damage,
        shield_absorbed=applied["shield_absorbed"],
        source_mp=-mp_cost,
        target_hp_delta=-applied["damage"],
    )
    return {
        "type": "skill_card",
        "action_result": action_result,
        "log": {
            "type": "skill_card",
            "card_id": card["card_id"],
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "target_id": target["combatant_id"],
            "target_name": target["name"],
            "value": applied["damage"],
            "raw_value": damage,
            "shield_absorbed": applied["shield_absorbed"],
            "target_hp": target["hp"],
            "action_result": action_result,
        },
    }


def build_item_result(actor, item=None, heal=0, text=None):
    action_result = _build_action_result(
        action_type="use_combat_item",
        card_id="use_combat_item",
        source=actor,
        target=None,
        heal=heal,
        source_hp_delta=heal,
    )
    return {
        "type": "use_combat_item",
        "action_result": action_result,
        "log": {
            "type": "use_combat_item",
            "card_id": "use_combat_item",
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "item_id": getattr(getattr(item, "db", None), "item_id", None) if item else None,
            "value": heal,
            "text": text,
            "action_result": action_result,
        },
    }


def build_guard_result(actor, card_id, damage_reduction_pct, block_chance_pct, source_mp=0):
    action_result = _build_action_result(
        action_type="guard",
        card_id=card_id,
        source=actor,
        target=None,
        source_mp=source_mp,
        source_effects_added=["guard"],
    )
    return {
        "type": "guard",
        "action_result": action_result,
        "log": {
            "type": "guard",
            "card_id": card_id,
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "value": damage_reduction_pct,
            "block_chance_pct": block_chance_pct,
            "action_result": action_result,
        },
    }


def build_shield_result(actor, card_id, shield_gain, source_mp=0):
    action_result = _build_action_result(
        action_type="skill_card",
        card_id=card_id,
        source=actor,
        target=None,
        shield_gain=shield_gain,
        source_mp=source_mp,
    )
    return {
        "type": "skill_card",
        "action_result": action_result,
        "log": {
            "type": "skill_card",
            "card_id": card_id,
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "value": shield_gain,
            "action_result": action_result,
        },
    }


def build_heal_result(actor, card_id, heal, source_mp=0):
    action_result = _build_action_result(
        action_type="skill_card",
        card_id=card_id,
        source=actor,
        target=None,
        heal=heal,
        source_mp=source_mp,
        source_hp_delta=heal,
    )
    return {
        "type": "skill_card",
        "action_result": action_result,
        "log": {
            "type": "skill_card",
            "card_id": card_id,
            "actor_id": actor["combatant_id"],
            "actor_name": actor["name"],
            "value": heal,
            "target_hp": actor["hp"],
            "action_result": action_result,
        },
    }


def snapshot_battle_state(battle):
    players = []
    enemies = []
    alive_player_count = 0
    alive_enemy_count = 0
    for combatant in battle["participants"]:
        entry = serialize_state_entry(combatant)
        if combatant["side"] == "player":
            players.append(entry)
            if combatant["alive"]:
                alive_player_count += 1
        else:
            enemies.append(entry)
            if combatant["alive"]:
                alive_enemy_count += 1
    return {
        "player": players,
        "enemy": enemies,
        "meta": {
            "alive_player_count": alive_player_count,
            "alive_enemy_count": alive_enemy_count,
        },
    }


def build_round_report(battle, actor, log_entry, before_snapshot, after_snapshot, auto=False):
    return {
        "turn_count": battle["turn_state"]["turn_count"],
        "actor_name": actor["name"],
        "actor_side": actor["side"],
        "card_id": log_entry.get("card_id") or log_entry.get("type"),
        "target_name": log_entry.get("target_name"),
        "entry": dict(log_entry),
        "before": before_snapshot,
        "after": after_snapshot,
        "auto": auto,
        "action_result": dict(log_entry.get("action_result") or {}),
    }


def serialize_state_entry(combatant):
    return {
        "combatant_id": combatant.get("combatant_id"),
        "name": combatant["name"],
        "side": combatant["side"],
        "alive": combatant["alive"],
        "hp": combatant["hp"],
        "max_hp": combatant["max_hp"],
        "mp": combatant["mp"],
        "max_mp": combatant["max_mp"],
        "stamina": combatant["stamina"],
        "max_stamina": combatant["max_stamina"],
        "shield": combatant.get("shield", 0),
        "resources": {
            "hp": combatant["hp"],
            "max_hp": combatant["max_hp"],
            "mp": combatant["mp"],
            "max_mp": combatant["max_mp"],
            "stamina": combatant["stamina"],
            "max_stamina": combatant["max_stamina"],
            "shield": combatant.get("shield", 0),
        },
        "effects": list(combatant.get("effects") or []),
    }


def _build_action_result(
    *,
    action_type,
    card_id,
    source,
    target,
    damage=0,
    heal=0,
    shield_gain=0,
    raw_damage=0,
    guard_reduced=0,
    guard_blocked=False,
    shield_absorbed=0,
    source_mp=0,
    source_stamina=0,
    source_hp_delta=0,
    target_hp_delta=0,
    source_effects_added=None,
    source_effects_removed=None,
    target_effects_added=None,
    target_effects_removed=None,
):
    return {
        "action_type": action_type,
        "card_id": card_id,
        "source": {
            "combatant_id": source.get("combatant_id"),
            "name": source.get("name"),
            "side": source.get("side"),
        },
        "target": None
        if not target
        else {
            "combatant_id": target.get("combatant_id"),
            "name": target.get("name"),
            "side": target.get("side"),
        },
        "result": {
            "damage": damage,
            "heal": heal,
            "shield_gain": shield_gain,
        },
        "modifiers": {
            "raw_damage": raw_damage,
            "guard_reduced": guard_reduced,
            "guard_blocked": guard_blocked,
            "shield_absorbed": shield_absorbed,
        },
        "resource_delta": {
            "source_mp": source_mp,
            "source_stamina": source_stamina,
        },
        "state_delta": {
            "source_hp": source_hp_delta,
            "target_hp": target_hp_delta,
            "source_effects_added": list(source_effects_added or []),
            "source_effects_removed": list(source_effects_removed or []),
            "target_effects_added": list(target_effects_added or []),
            "target_effects_removed": list(target_effects_removed or []),
        },
    }
