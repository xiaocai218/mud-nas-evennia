"""Player battle card provider and template hooks."""

from .player_stats import get_stats


DEFAULT_PLAYER_BATTLE_CARD_POOL = ["basic_attack", "guard", "use_combat_item"]
ROOT_SKILL_CARD_MAP = {
    "metal": "metal_edge",
    "wood": "wood_rejuvenation",
    "water": "water_barrier",
    "fire": "fire_burst",
    "earth": "earth_guard",
}


def get_player_battle_card_pool(caller, battle=None):
    stats = get_stats(caller)
    pool = list(DEFAULT_PLAYER_BATTLE_CARD_POOL)

    # Template hook for future real skill definitions.
    pool.extend(get_player_available_skill_cards(caller, battle=battle, stats=stats))
    return _dedupe(pool)


def get_player_available_skill_cards(caller, battle=None, stats=None):
    stats = stats or get_stats(caller)
    stage = stats.get("stage")
    root = stats.get("root")
    realm = stats.get("realm")

    cards = []

    if root in ROOT_SKILL_CARD_MAP:
        cards.append(ROOT_SKILL_CARD_MAP[root])
    elif stage == "cultivator" or realm == "启灵":
        cards.append("spirit_blast")

    return cards


def can_use_player_card(caller, card_id, battle=None):
    return card_id in get_player_battle_card_pool(caller, battle=battle)


def get_player_card_context(caller, battle=None):
    stats = get_stats(caller)
    return {
        "stage": stats.get("stage"),
        "root": stats.get("root"),
        "realm": stats.get("realm"),
        "battle_id": battle.get("battle_id") if battle else None,
    }


def _dedupe(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
