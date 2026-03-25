"""Rule-based battle AI helpers."""

from __future__ import annotations


def choose_card(battle, actor):
    actor["available_cards"] = list(actor.get("available_cards") or [])
    for rule in actor.get("decision_rules") or []:
        if match_rule(battle, actor, rule):
            chosen = find_available_card(actor, rule.get("use_card"))
            if chosen:
                return {"card_id": chosen["card_id"], "target_id": resolve_target_id(battle, actor, chosen)}
    for card in actor.get("available_cards") or []:
        if card.get("card_type") == "skill_card" and card.get("target_rule") == "enemy_single":
            return {"card_id": card["card_id"], "target_id": resolve_target_id(battle, actor, card)}
    target = resolve_target_for_actor(battle, actor)
    return {"card_id": "basic_attack", "target_id": target["combatant_id"] if target else None}


def match_rule(battle, actor, rule):
    when = dict(rule.get("when") or {})
    hp_pct = int(100 * actor.get("hp", 0) / max(1, actor.get("max_hp", 1)))
    target = resolve_target_for_actor(battle, actor)
    target_hp_pct = None
    if target:
        target_hp_pct = int(100 * target.get("hp", 0) / max(1, target.get("max_hp", 1)))

    if "self_hp_lte_pct" in when and hp_pct > int(when["self_hp_lte_pct"]):
        return False
    if "self_hp_gte_pct" in when and hp_pct < int(when["self_hp_gte_pct"]):
        return False
    if "card_ready" in when and actor.get("cooldowns", {}).get(when["card_ready"], 0) > 0:
        return False
    if "has_effect" in when and not any(effect.get("type") == when["has_effect"] for effect in actor.get("effects") or []):
        return False
    if "missing_effect" in when and any(effect.get("type") == when["missing_effect"] for effect in actor.get("effects") or []):
        return False
    if "shield_lte" in when and int(actor.get("shield", 0) or 0) > int(when["shield_lte"]):
        return False
    if "target_hp_lte_pct" in when:
        if target_hp_pct is None or target_hp_pct > int(when["target_hp_lte_pct"]):
            return False
    return True


def find_available_card(actor, card_id):
    for card in actor.get("available_cards") or []:
        if card.get("card_id") == card_id:
            return card
    return None


def resolve_target_id(battle, actor, card):
    target_rule = card.get("target_rule")
    if target_rule == "self":
        return actor["combatant_id"]
    target = resolve_target_for_actor(battle, actor)
    return target["combatant_id"] if target else None


def resolve_target_for_actor(battle, actor, target_id=None):
    opponents = [entry for entry in battle.get("participants", []) if entry.get("alive") and entry.get("side") != actor.get("side")]
    if not opponents:
        return actor
    if target_id:
        for target in opponents:
            if target.get("combatant_id") == target_id:
                return target
    return opponents[0]
