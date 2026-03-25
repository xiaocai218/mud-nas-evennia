"""Reusable battle effect handlers."""

from __future__ import annotations

import random

from .battle_results import build_guard_result, build_heal_result, build_shield_result


def spend_card_costs(actor, card, default_cooldown=0):
    costs = dict((card or {}).get("costs") or {})
    actor["mp"] = max(0, actor.get("mp", 0) - int(costs.get("mp", 0) or 0))
    actor.setdefault("cooldowns", {})
    actor["cooldowns"][card["card_id"]] = int((card or {}).get("cooldown", default_cooldown) or default_cooldown)


def apply_guard_effect(actor, card=None):
    params = dict((card or {}).get("effect_params") or {})
    mp_cost = 0
    if card and card.get("card_type") == "skill_card":
        mp_cost = int(((card or {}).get("costs") or {}).get("mp", 0) or 0)
        spend_card_costs(actor, card)
    actor["effects"] = [effect for effect in actor.get("effects") or [] if effect.get("type") != "guard"]
    damage_reduction_pct = int(params.get("damage_reduction_pct", 60) or 60)
    block_chance_pct = int(params.get("block_chance_pct", 5) or 5)
    effect = {
        "type": "guard",
        "source_card_id": card["card_id"] if card else "guard",
        "duration_mode": "until_trigger",
        "triggers_on": "basic_attack_taken",
        "params": {
            "damage_reduction_pct": damage_reduction_pct,
            "block_chance_pct": block_chance_pct,
        },
        "damage_reduction_pct": damage_reduction_pct,
        "block_chance_pct": block_chance_pct,
        "consumed_on": "basic_attack",
    }
    actor.setdefault("effects", []).append(effect)
    card_id = card["card_id"] if card else "guard"
    return build_guard_result(actor, card_id, damage_reduction_pct, block_chance_pct, source_mp=-mp_cost)


def apply_shield_effect(actor, card=None):
    params = dict((card or {}).get("effect_params") or {})
    mp_cost = 0
    if card and card.get("card_type") == "skill_card":
        mp_cost = int(((card or {}).get("costs") or {}).get("mp", 0) or 0)
        spend_card_costs(actor, card)
    shield = max(
        int(params.get("min_shield", 6) or 6),
        int(params.get("base_shield", 0) or 0)
        + int(actor.get("combat_stats_snapshot", {}).get("defense", 5) * float(params.get("defense_ratio", 1.2) or 1.2)),
    )
    actor["shield"] = actor.get("shield", 0) + shield
    effect_type = card["card_id"] if card else "shield"
    actor["effects"] = [effect for effect in actor.get("effects") or [] if effect.get("type") != effect_type]
    actor.setdefault("effects", []).append(
        {
            "type": effect_type,
            "source_card_id": effect_type,
            "duration_mode": "until_value_spent",
            "params": {"shield": shield},
            "shield": shield,
        }
    )
    return build_shield_result(actor, effect_type, shield, source_mp=-mp_cost)


def apply_heal_effect(actor, card=None, default_cooldown=3):
    params = dict((card or {}).get("effect_params") or {})
    mp_cost = 0
    if card:
        mp_cost = int(((card or {}).get("costs") or {}).get("mp", 0) or 0)
        spend_card_costs(actor, card, default_cooldown=default_cooldown)
    heal = max(
        int(params.get("min_heal", 8) or 8),
        int(params.get("base_heal", 8) or 8) + int(actor.get("max_hp", 0) * float(params.get("max_hp_ratio", 0.25) or 0)),
    )
    actor["hp"] = min(actor["max_hp"], actor.get("hp", 0) + heal)
    return build_heal_result(actor, card["card_id"] if card else "heal", heal, source_mp=-mp_cost)


def apply_damage(target, damage, attack_type=None):
    guard_blocked = False
    guard_reduced = 0
    guard_effect = None
    if attack_type == "basic_attack":
        for effect in target.get("effects") or []:
            if effect.get("type") == "guard":
                guard_effect = effect
                break
        if guard_effect:
            reduction_pct = max(0, int(guard_effect.get("damage_reduction_pct", 0) or 0))
            block_chance_pct = max(0, float(guard_effect.get("block_chance_pct", 0) or 0))
            if random.random() * 100 < block_chance_pct:
                guard_blocked = True
                damage = 0
            else:
                guard_reduced = int(damage * reduction_pct / 100)
                damage = max(0, damage - guard_reduced)
            target["effects"] = [effect for effect in target.get("effects") or [] if effect is not guard_effect]
    shield_absorbed = min(target.get("shield", 0), damage)
    damage -= shield_absorbed
    target["shield"] = max(0, target.get("shield", 0) - shield_absorbed)
    if target.get("shield", 0) <= 0:
        target["effects"] = [effect for effect in target.get("effects") or [] if effect.get("shield", 0) <= 0]
    target["hp"] = max(0, target["hp"] - damage)
    target["alive"] = target["hp"] > 0
    return {
        "damage": damage,
        "shield_absorbed": shield_absorbed,
        "guard_reduced": guard_reduced,
        "guard_blocked": guard_blocked,
    }
