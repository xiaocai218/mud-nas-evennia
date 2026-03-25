"""Battle card adapters and display helpers."""

from __future__ import annotations

from .content_loader import load_content


CARD_DEFINITIONS = load_content("battle_cards")
CARD_ALIASES = {
    "普通攻击": "basic_attack",
    "攻击": "basic_attack",
    "防御": "guard",
    "格挡": "guard",
    "使用战斗物品": "use_combat_item",
    "物品": "use_combat_item",
    "灵击": "spirit_blast",
    "金锋术": "metal_edge",
    "回春诀": "wood_rejuvenation",
    "水幕诀": "water_barrier",
    "炽焰诀": "fire_burst",
    "岩甲诀": "earth_guard",
    "兽性回生": "recover_instinct",
}


def get_card_definition(card_id):
    return CARD_DEFINITIONS.get(card_id)


def build_card_payload(card_id):
    data = get_card_definition(card_id)
    if not data:
        return None
    return {
        "card_id": card_id,
        "card_type": data.get("card_type", "basic_attack"),
        "name": data.get("name", card_id),
        "target_rule": data.get("target_rule", "enemy_single"),
        "costs": dict(data.get("costs", {})),
        "cooldown": int(data.get("cooldown", 0) or 0),
        "source": data.get("source", "basic"),
        "effects": [{"type": effect_type} for effect_type in data.get("effects", [])],
        "effect_params": dict(data.get("effect_params", {})),
    }


def resolve_card_alias(name_or_id):
    return CARD_ALIASES.get(name_or_id, name_or_id)


def get_card_display_name(card_id=None, entry_type=None):
    if card_id:
        definition = get_card_definition(card_id)
        if definition:
            return definition.get("name", card_id)
        return card_id
    return {
        "basic_attack": "普通攻击",
        "guard": "防御",
        "use_combat_item": "使用战斗物品",
        "skill_card": "技能",
        "shield": "护盾",
    }.get(entry_type, entry_type or "unknown")


def get_direct_card_aliases():
    return [alias for alias in CARD_ALIASES if alias not in {"攻击", "格挡"}]
