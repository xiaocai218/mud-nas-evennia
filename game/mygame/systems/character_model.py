"""Unified player character model helpers."""

from copy import deepcopy

from .character_profiles import get_character_profile
from .realms import get_default_realm, get_realm_from_exp


MORTAL_STAGE = "mortal"
CULTIVATOR_STAGE = "cultivator"
MORTAL_REALM = "凡人"
AWAKENED_REALM = "启灵"

ROOT_NONE = None
ROOT_METAL = "metal"
ROOT_WOOD = "wood"
ROOT_WATER = "water"
ROOT_FIRE = "fire"
ROOT_EARTH = "earth"

PRIMARY_CURRENCY_COPPER = "copper"
PRIMARY_CURRENCY_SPIRIT_STONE = "spirit_stone"

PRIMARY_STATS = ("physique", "aether", "spirit", "agility", "bone")
EQUIPMENT_SLOTS = ("chest", "legs")
ROOT_CHOICES = (ROOT_METAL, ROOT_WOOD, ROOT_WATER, ROOT_FIRE, ROOT_EARTH)
ROOT_CHOICE_ALIASES = {
    "金": ROOT_METAL,
    "木": ROOT_WOOD,
    "水": ROOT_WATER,
    "火": ROOT_FIRE,
    "土": ROOT_EARTH,
    ROOT_METAL: ROOT_METAL,
    ROOT_WOOD: ROOT_WOOD,
    ROOT_WATER: ROOT_WATER,
    ROOT_FIRE: ROOT_FIRE,
    ROOT_EARTH: ROOT_EARTH,
}

ROOT_DEFINITIONS = {
    ROOT_METAL: {
        "key": ROOT_METAL,
        "label": "金灵根",
        "combat_bias": {
            "attack_power": "high",
            "defense": "medium_high",
            "speed": "low",
            "mp_efficiency": "low",
            "cooldown": "long",
            "single_target_damage": "high",
        },
        "skill_profile": ["single_target", "burst", "metal_edge"],
        "life_affinity": ["spirit_tool", "metal"],
    },
    ROOT_WOOD: {
        "key": ROOT_WOOD,
        "label": "木灵根",
        "combat_bias": {
            "max_hp": "high",
            "speed": "highest",
            "sustain": "high",
            "control": "medium_high",
            "damage_over_time": "high",
            "single_target_damage": "low",
        },
        "skill_profile": ["control", "group_heal", "damage_over_time"],
        "life_affinity": ["alchemy", "gathering", "wood"],
    },
    ROOT_WATER: {
        "key": ROOT_WATER,
        "label": "水灵根",
        "combat_bias": {
            "healing_power": "highest",
            "shield_power": "highest",
            "control_resist": "high",
            "speed": "medium_high",
            "damage": "lowest",
        },
        "skill_profile": ["single_target_heal", "purify", "shield"],
        "life_affinity": ["talisman", "liquid"],
    },
    ROOT_FIRE: {
        "key": ROOT_FIRE,
        "label": "火灵根",
        "combat_bias": {
            "max_mp": "high",
            "crit_rate": "highest",
            "crit_damage": "high",
            "aoe": "high",
            "cooldown": "longest",
            "attack_power": "medium",
        },
        "skill_profile": ["burst", "aoe", "burn"],
        "life_affinity": ["smithing", "flame"],
    },
    ROOT_EARTH: {
        "key": ROOT_EARTH,
        "label": "土灵根",
        "combat_bias": {
            "defense": "highest",
            "max_hp": "high",
            "threat_modifier": "highest",
            "counter": "high",
            "speed": "low",
            "damage": "low",
        },
        "skill_profile": ["taunt", "counter", "thorns", "guard"],
        "life_affinity": ["formation", "earth"],
    },
}

DEFAULT_PRIMARY_STATS = {
    "physique": 6,
    "aether": 4,
    "spirit": 4,
    "agility": 5,
    "bone": 5,
}

DEFAULT_MORTAL_COMBAT = {
    "hp": 100,
    "max_hp": 100,
    "mp": 0,
    "max_mp": 0,
    "stamina": 50,
    "max_stamina": 50,
    "attack_power": 10,
    "spell_power": 0,
    "defense": 6,
    "speed": 10,
    "crit_rate": 0,
    "crit_damage": 150,
    "healing_power": 0,
    "shield_power": 0,
    "control_power": 0,
    "control_resist": 0,
    "threat_modifier": 100,
}


def ensure_character_model(caller):
    """Populate the unified character model and compatibility fields."""
    profile = get_character_profile(getattr(caller.db, "character_profile", None))

    stage = getattr(caller.db, "character_stage", None) or MORTAL_STAGE
    root = _normalize_root(getattr(caller.db, "spiritual_root", None))

    identity = dict(getattr(caller.db, "identity", None) or {})
    identity.setdefault("name", getattr(caller, "key", None))
    identity["stage"] = stage
    identity["is_cultivator"] = stage == CULTIVATOR_STAGE
    identity["sect"] = identity.get("sect")
    identity["root"] = root

    progression = dict(getattr(caller.db, "progression", None) or {})
    progression["character_profile"] = getattr(caller.db, "character_profile", None) or profile["profile_key"]
    progression["root_choice_completed"] = bool(root)
    progression["realm"] = _resolve_realm(caller, stage, profile)
    progression["cultivation_exp"] = int(_coalesce(getattr(caller.db, "exp", None), progression.get("cultivation_exp"), profile["exp"]) or 0)

    primary_stats = dict(getattr(caller.db, "primary_stats", None) or {})
    for key, value in DEFAULT_PRIMARY_STATS.items():
        primary_stats[key] = int(primary_stats.get(key, value) or value)

    equipment = dict(getattr(caller.db, "equipment", None) or {})
    slots = dict(equipment.get("slots", {}))
    for slot in EQUIPMENT_SLOTS:
        slots.setdefault(slot, None)
    equipment["slots"] = slots

    affinities = dict(getattr(caller.db, "affinities", None) or {})
    affinities["life"] = list(_build_life_affinity(root))
    affinities["root"] = root
    reserves = dict(getattr(caller.db, "reserves", None) or {})
    reserves.setdefault("spiritual_pet", {"bonded_pet_id": None, "slots": []})

    currencies = dict(getattr(caller.db, "currencies", None) or {})
    currencies["copper"] = int(_coalesce(getattr(caller.db, "copper", None), currencies.get("copper"), profile.get("copper", 0)) or 0)
    currencies["spirit_stone"] = int(
        _coalesce(getattr(caller.db, "spirit_stone", None), currencies.get("spirit_stone"), profile.get("spirit_stone", 0)) or 0
    )
    currencies["primary_currency"] = PRIMARY_CURRENCY_SPIRIT_STONE if stage == CULTIVATOR_STAGE else PRIMARY_CURRENCY_COPPER

    combat_stats = _build_combat_stats(caller, stage, root, primary_stats, profile)

    caller.db.character_stage = stage
    caller.db.spiritual_root = root
    caller.db.identity = identity
    caller.db.progression = progression
    caller.db.primary_stats = primary_stats
    caller.db.combat_stats = combat_stats
    caller.db.equipment = equipment
    caller.db.affinities = affinities
    caller.db.currencies = currencies
    caller.db.reserves = reserves

    # Compatibility fields for existing systems.
    caller.db.realm = progression["realm"]
    caller.db.exp = progression["cultivation_exp"]
    caller.db.hp = combat_stats["hp"]
    caller.db.max_hp = combat_stats["max_hp"]
    caller.db.stamina = combat_stats["stamina"]
    caller.db.max_stamina = combat_stats["max_stamina"]
    caller.db.copper = currencies["copper"]
    caller.db.spirit_stone = currencies["spirit_stone"]
    caller.db.primary_currency = currencies["primary_currency"]
    return _read_character_sheet(caller)


def get_character_sheet(caller):
    return ensure_character_model(caller)


def is_awakened_realm(realm):
    return realm == AWAKENED_REALM


def resolve_character_realm(stage, exp, current_realm=None, root=None):
    current_realm = current_realm or None
    if stage != CULTIVATOR_STAGE:
        return MORTAL_REALM

    if current_realm and current_realm not in (MORTAL_REALM, AWAKENED_REALM):
        return current_realm
    if is_awakened_realm(current_realm):
        return AWAKENED_REALM
    if root:
        return AWAKENED_REALM
    return get_realm_from_exp(int(exp or 0)) or get_default_realm()


def _read_character_sheet(caller):
    return {
        "identity": deepcopy(getattr(caller.db, "identity", {}) or {}),
        "progression": deepcopy(getattr(caller.db, "progression", {}) or {}),
        "primary_stats": deepcopy(getattr(caller.db, "primary_stats", {}) or {}),
        "combat_stats": deepcopy(getattr(caller.db, "combat_stats", {}) or {}),
        "currencies": deepcopy(getattr(caller.db, "currencies", {}) or {}),
        "equipment": deepcopy(getattr(caller.db, "equipment", {}) or {}),
        "affinities": deepcopy(getattr(caller.db, "affinities", {}) or {}),
        "reserves": deepcopy(getattr(caller.db, "reserves", {}) or {}),
    }


def awaken_spiritual_root(caller, root_key, sect=None):
    root_key = _normalize_root(root_key)
    if root_key not in ROOT_DEFINITIONS:
        raise ValueError(f"unknown root: {root_key}")
    ensure_character_model(caller)
    caller.db.character_stage = CULTIVATOR_STAGE
    caller.db.spiritual_root = root_key
    identity = dict(caller.db.identity or {})
    identity["stage"] = CULTIVATOR_STAGE
    identity["is_cultivator"] = True
    identity["root"] = root_key
    if sect is not None:
        identity["sect"] = sect
    caller.db.identity = identity
    progression = dict(caller.db.progression or {})
    progression["root_choice_completed"] = True
    current_realm = getattr(caller.db, "realm", None)
    progression["realm"] = AWAKENED_REALM if current_realm in (None, "", MORTAL_REALM) else current_realm
    caller.db.progression = progression
    caller.db.realm = progression["realm"]
    ensure_character_model(caller)
    return get_character_sheet(caller)


def promote_awakened_realm(caller):
    ensure_character_model(caller)
    if getattr(caller.db, "character_stage", None) != CULTIVATOR_STAGE or not getattr(caller.db, "spiritual_root", None):
        raise ValueError("character has not awakened a spiritual root")
    caller.db.realm = get_default_realm()
    progression = dict(caller.db.progression or {})
    progression["realm"] = caller.db.realm
    caller.db.progression = progression
    return ensure_character_model(caller)


def reset_spiritual_root(caller):
    ensure_character_model(caller)
    caller.db.character_stage = MORTAL_STAGE
    caller.db.spiritual_root = None
    caller.db.mp = 0
    caller.db.max_mp = 0
    identity = dict(caller.db.identity or {})
    identity["stage"] = MORTAL_STAGE
    identity["is_cultivator"] = False
    identity["root"] = None
    identity["sect"] = None
    caller.db.identity = identity
    progression = dict(caller.db.progression or {})
    progression["root_choice_completed"] = False
    progression["realm"] = MORTAL_REALM
    caller.db.progression = progression
    return ensure_character_model(caller)


def get_root_definition(root_key):
    root_key = _normalize_root(root_key)
    return deepcopy(ROOT_DEFINITIONS.get(root_key))


def get_root_label(root_key, default="未觉醒"):
    definition = get_root_definition(root_key)
    return definition.get("label", default) if definition else default


def normalize_root_choice(choice):
    if not choice:
        return None
    return ROOT_CHOICE_ALIASES.get(str(choice).strip().lower()) or ROOT_CHOICE_ALIASES.get(str(choice).strip())


def _resolve_realm(caller, stage, profile):
    exp = int(getattr(caller.db, "exp", profile["exp"]) or 0)
    return resolve_character_realm(
        stage,
        exp,
        current_realm=getattr(caller.db, "realm", None),
        root=_normalize_root(getattr(caller.db, "spiritual_root", None)),
    )


def _build_life_affinity(root):
    root_definition = ROOT_DEFINITIONS.get(root)
    if not root_definition:
        return []
    return root_definition.get("life_affinity", [])


def _build_combat_stats(caller, stage, root, primary_stats, profile):
    stats = deepcopy(DEFAULT_MORTAL_COMBAT)
    stats["max_hp"] = profile["max_hp"] + primary_stats["physique"] * 8 + primary_stats["bone"] * 2
    stats["max_stamina"] = profile["max_stamina"] + primary_stats["physique"] * 2 + primary_stats["agility"]
    stats["attack_power"] = DEFAULT_MORTAL_COMBAT["attack_power"] + primary_stats["physique"] + primary_stats["agility"] // 2
    stats["defense"] = DEFAULT_MORTAL_COMBAT["defense"] + primary_stats["physique"] // 2 + primary_stats["bone"]
    stats["speed"] = DEFAULT_MORTAL_COMBAT["speed"] + primary_stats["agility"] + primary_stats["spirit"] // 3
    stats["max_mp"] = 0 if stage == MORTAL_STAGE else primary_stats["aether"] * 12 + primary_stats["spirit"] * 4
    stats["spell_power"] = 0 if stage == MORTAL_STAGE else primary_stats["aether"] * 2 + primary_stats["spirit"]
    stats["healing_power"] = 0 if stage == MORTAL_STAGE else primary_stats["aether"] + primary_stats["spirit"]
    stats["shield_power"] = 0 if stage == MORTAL_STAGE else primary_stats["aether"] + primary_stats["bone"] // 2
    stats["control_power"] = 0 if stage == MORTAL_STAGE else primary_stats["spirit"] * 2
    stats["control_resist"] = primary_stats["spirit"] + primary_stats["bone"] // 2
    stats["crit_rate"] = primary_stats["agility"]
    stats["crit_damage"] = DEFAULT_MORTAL_COMBAT["crit_damage"] + primary_stats["aether"] * 2
    stats["threat_modifier"] = DEFAULT_MORTAL_COMBAT["threat_modifier"]

    if stage == CULTIVATOR_STAGE:
        _apply_root_bias(stats, root)

    stats["hp"] = int(getattr(caller.db, "hp", None) if getattr(caller.db, "hp", None) is not None else stats["max_hp"])
    stats["max_hp"] = int(stats["max_hp"])
    stats["hp"] = max(0, min(stats["hp"], stats["max_hp"]))
    stats["stamina"] = int(
        getattr(caller.db, "stamina", None) if getattr(caller.db, "stamina", None) is not None else stats["max_stamina"]
    )
    stats["max_stamina"] = int(stats["max_stamina"])
    stats["stamina"] = max(0, min(stats["stamina"], stats["max_stamina"]))
    stats["mp"] = int(getattr(caller.db, "mp", None) if getattr(caller.db, "mp", None) is not None else stats["max_mp"])
    stats["max_mp"] = int(stats["max_mp"])
    stats["mp"] = max(0, min(stats["mp"], stats["max_mp"]))
    return stats


def _apply_root_bias(stats, root):
    if root == ROOT_METAL:
        stats["attack_power"] += 6
        stats["defense"] += 4
        stats["speed"] -= 2
        stats["max_mp"] += 8
    elif root == ROOT_WOOD:
        stats["max_hp"] += 18
        stats["speed"] += 5
        stats["healing_power"] += 4
        stats["attack_power"] -= 2
    elif root == ROOT_WATER:
        stats["healing_power"] += 8
        stats["shield_power"] += 8
        stats["control_resist"] += 6
        stats["speed"] += 3
        stats["attack_power"] -= 4
        stats["spell_power"] -= 2
    elif root == ROOT_FIRE:
        stats["max_mp"] += 24
        stats["crit_rate"] += 8
        stats["crit_damage"] += 16
        stats["spell_power"] += 6
    elif root == ROOT_EARTH:
        stats["defense"] += 8
        stats["max_hp"] += 12
        stats["threat_modifier"] += 30
        stats["speed"] -= 3
        stats["attack_power"] -= 2


def _normalize_root(root_key):
    root_key = (root_key or None)
    if root_key in ("", "none"):
        return None
    return root_key


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None
