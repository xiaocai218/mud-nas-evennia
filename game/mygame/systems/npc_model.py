"""Unified NPC model helpers."""

from copy import deepcopy

from .content_loader import load_content
from .entity_gender import GENDER_UNKNOWN, normalize_gender
from .realms import get_recommended_realm_target, normalize_realm_display


PRIMARY_STATS = ("physique", "aether", "spirit", "agility", "bone")
DEFAULT_PRIMARY_STATS = {
    "physique": 4,
    "aether": 4,
    "spirit": 5,
    "agility": 4,
    "bone": 4,
}
DEFAULT_COMBAT_STATS = {
    "hp": 80,
    "max_hp": 80,
    "mp": 10,
    "max_mp": 10,
    "stamina": 40,
    "max_stamina": 40,
    "attack_power": 8,
    "spell_power": 8,
    "defense": 6,
    "speed": 9,
    "crit_rate": 0,
    "crit_damage": 150,
    "healing_power": 4,
    "shield_power": 0,
    "control_power": 0,
    "control_resist": 4,
    "threat_modifier": 100,
}
DEFAULT_RELATIONSHIP_PROFILE = {
    "affection_enabled": False,
    "reputation_enabled": False,
    "trust_enabled": False,
    "quest_state_mode": "per_player",
}
DEFAULT_COMBAT_PROFILE = {
    "attackable": False,
    "joinable": False,
    "battle_profile": None,
    "event_hooks": [],
}
DEFAULT_PROJECTION_POLICY = {
    "mode": "world_anchor",
    "companion_template_id": None,
}
DEFAULT_RELOCATION_POLICY = {
    "mode": "per_player_override",
    "default_room_id": None,
}

NPC_DEFINITIONS = load_content("npcs").get("npcs", [])
ROOM_DEFINITIONS = load_content("rooms").get("rooms", {})
AREA_DEFINITIONS = load_content("areas")
ZONE_DEFINITIONS = load_content("zones")


def get_npc_definition(npc_id):
    raw = next((npc for npc in NPC_DEFINITIONS if npc.get("id") == npc_id), None)
    if not raw:
        return None
    return _normalize_npc_definition(npc_id, raw)


def is_npc(target):
    if not target:
        return False
    identity = getattr(target.db, "identity", None) or {}
    if identity.get("kind") == "npc":
        return True
    return bool(getattr(target.db, "npc_role", None) or getattr(target.db, "talk_route", None) or getattr(target.db, "shop_id", None))


def ensure_npc_model(target):
    definition = _resolve_definition_for_target(target)
    sheet = _build_npc_sheet(target, definition)

    target.db.identity = sheet["identity"]
    target.db.progression = sheet["progression"]
    target.db.primary_stats = sheet["primary_stats"]
    target.db.combat_stats = sheet["combat_stats"]
    target.db.affinities = sheet["affinities"]
    target.db.reserves = sheet["reserves"]
    target.db.npc_meta = sheet["npc_meta"]

    _write_compatibility_fields(target, sheet)
    return {
        "identity": deepcopy(sheet["identity"]),
        "progression": deepcopy(sheet["progression"]),
        "primary_stats": deepcopy(sheet["primary_stats"]),
        "combat_stats": deepcopy(sheet["combat_stats"]),
        "affinities": deepcopy(sheet["affinities"]),
        "reserves": deepcopy(sheet["reserves"]),
        "npc_meta": deepcopy(sheet["npc_meta"]),
    }


def get_npc_sheet(target):
    ensure_npc_model(target)
    return {
        "identity": deepcopy(getattr(target.db, "identity", {}) or {}),
        "progression": deepcopy(getattr(target.db, "progression", {}) or {}),
        "primary_stats": deepcopy(getattr(target.db, "primary_stats", {}) or {}),
        "combat_stats": deepcopy(getattr(target.db, "combat_stats", {}) or {}),
        "affinities": deepcopy(getattr(target.db, "affinities", {}) or {}),
        "reserves": deepcopy(getattr(target.db, "reserves", {}) or {}),
        "npc_meta": deepcopy(getattr(target.db, "npc_meta", {}) or {}),
    }


def _resolve_definition_for_target(target):
    npc_id = getattr(target.db, "template_id", None) or getattr(target.db, "content_id", None) or getattr(target.db, "npc_id", None)
    runtime_identity = getattr(target.db, "identity", None) or {}
    runtime_combat = getattr(target.db, "combat_stats", None) or {}
    runtime_meta = getattr(target.db, "npc_meta", None) or {}
    if runtime_identity.get("kind") == "npc" and runtime_combat:
        return _normalize_structured_npc(
            npc_id or runtime_identity.get("template_id") or runtime_identity.get("content_id") or getattr(target, "key", "npc"),
            {
                "id": runtime_identity.get("content_id"),
                "identity": runtime_identity,
                "progression": getattr(target.db, "progression", None) or {},
                "primary_stats": getattr(target.db, "primary_stats", None) or {},
                "combat_stats": runtime_combat,
                "affinities": getattr(target.db, "affinities", None) or {},
                "reserves": getattr(target.db, "reserves", None) or {},
                "npc_meta": runtime_meta,
            },
        )
    if npc_id:
        definition = get_npc_definition(npc_id)
        if definition:
            return definition
    return _normalize_npc_definition(
        npc_id or getattr(target.db, "content_id", None) or getattr(target, "key", "npc"),
        None,
        target=target,
    )


def _normalize_npc_definition(npc_id, raw, target=None):
    raw = dict(raw or {})
    if raw.get("identity"):
        return _normalize_structured_npc(npc_id, raw)
    return _normalize_legacy_npc(npc_id, raw, target=target)


def _normalize_structured_npc(npc_id, raw):
    identity = dict(raw.get("identity", {}))
    progression = dict(raw.get("progression", {}))
    primary_stats = dict(raw.get("primary_stats", {}))
    combat_stats = dict(raw.get("combat_stats", {}))
    affinities = dict(raw.get("affinities", {}))
    reserves = dict(raw.get("reserves", {}))
    npc_meta = dict(raw.get("npc_meta", {}))

    identity.setdefault("kind", "npc")
    identity.setdefault("name", raw.get("key") or npc_id)
    identity.setdefault("content_id", raw.get("id", npc_id))
    identity.setdefault("template_id", npc_id)
    identity.setdefault("faction", "neutral")
    identity.setdefault("npc_role", identity.get("npc_role") or raw.get("npc_role"))
    identity["gender"] = normalize_gender(identity.get("gender"), default=GENDER_UNKNOWN)
    identity["tags"] = list(identity.get("tags", []))

    room_id = raw.get("room_id") or ((progression.get("spawn_profile") or {}).get("room_id"))
    progression.setdefault("stage", progression.get("stage") or "mortal")
    progression.setdefault("realm", normalize_realm_display(progression.get("realm") or _resolve_realm_for_room(room_id)))
    progression.setdefault("realm_info", {"display_name": progression.get("realm")})
    progression.setdefault("rank_tier", progression.get("rank_tier") or "common")
    progression.setdefault("spawn_profile", {"room_id": room_id})
    progression.setdefault("power_source", progression.get("power_source") or "template")

    normalized_primary = {key: int(primary_stats.get(key, DEFAULT_PRIMARY_STATS[key]) or DEFAULT_PRIMARY_STATS[key]) for key in PRIMARY_STATS}
    normalized_combat = {key: int(combat_stats.get(key, DEFAULT_COMBAT_STATS[key]) or DEFAULT_COMBAT_STATS[key]) for key in DEFAULT_COMBAT_STATS}
    normalized_combat["max_hp"] = max(1, normalized_combat["max_hp"])
    normalized_combat["hp"] = max(0, min(normalized_combat["hp"], normalized_combat["max_hp"]))
    normalized_combat["max_mp"] = max(0, normalized_combat["max_mp"])
    normalized_combat["mp"] = max(0, min(normalized_combat["mp"], normalized_combat["max_mp"]))
    normalized_combat["max_stamina"] = max(0, normalized_combat["max_stamina"])
    normalized_combat["stamina"] = max(0, min(normalized_combat["stamina"], normalized_combat["max_stamina"]))

    affinities.setdefault("element", None)
    affinities["social_tags"] = list(affinities.get("social_tags", []))
    affinities["resist_tags"] = list(affinities.get("resist_tags", []))

    reserves.setdefault("resources", {})

    npc_meta.setdefault("talk_route", npc_meta.get("talk_route") or raw.get("talk_route"))
    npc_meta.setdefault("shop_id", npc_meta.get("shop_id") or raw.get("shop_id"))
    npc_meta.setdefault("interact_modes", list(npc_meta.get("interact_modes", ["talk"])))
    npc_meta.setdefault("combat_profile", deepcopy(DEFAULT_COMBAT_PROFILE))
    npc_meta.setdefault("relationship_profile", deepcopy(DEFAULT_RELATIONSHIP_PROFILE))
    npc_meta.setdefault("projection_policy", deepcopy(DEFAULT_PROJECTION_POLICY))
    npc_meta.setdefault("relocation_policy", deepcopy(DEFAULT_RELOCATION_POLICY))
    npc_meta.setdefault("presentation", deepcopy(npc_meta.get("presentation") or {}))
    npc_meta["combat_profile"] = {**deepcopy(DEFAULT_COMBAT_PROFILE), **dict(npc_meta.get("combat_profile") or {})}
    npc_meta["relationship_profile"] = {
        **deepcopy(DEFAULT_RELATIONSHIP_PROFILE),
        **dict(npc_meta.get("relationship_profile") or {}),
    }
    npc_meta["projection_policy"] = {**deepcopy(DEFAULT_PROJECTION_POLICY), **dict(npc_meta.get("projection_policy") or {})}
    npc_meta["relocation_policy"] = {**deepcopy(DEFAULT_RELOCATION_POLICY), **dict(npc_meta.get("relocation_policy") or {})}
    npc_meta["presentation"]["desc"] = (
        npc_meta["presentation"].get("desc")
        or npc_meta["presentation"].get("description")
        or raw.get("desc")
        or ""
    )

    return {
        "id": raw.get("id", identity["content_id"]),
        "room_id": room_id,
        "identity": identity,
        "progression": progression,
        "primary_stats": normalized_primary,
        "combat_stats": normalized_combat,
        "affinities": affinities,
        "reserves": reserves,
        "npc_meta": npc_meta,
    }


def _normalize_legacy_npc(npc_id, raw, target=None):
    attrs = dict(raw.get("attrs", {}))
    key = raw.get("key") or getattr(target, "key", None) or npc_id or "npc"
    content_id = raw.get("id") or getattr(getattr(target, "db", None), "content_id", None) or npc_id or key
    room_id = raw.get("room_id") or raw.get("room")
    desc = raw.get("desc") or getattr(getattr(target, "db", None), "desc", "") or ""
    identity = {
        "kind": "npc",
        "name": key,
        "gender": normalize_gender(attrs.get("gender") or raw.get("gender") or getattr(getattr(target, "db", None), "gender", None)),
        "faction": attrs.get("faction") or raw.get("faction") or "neutral",
        "content_id": content_id,
        "template_id": npc_id or content_id,
        "tags": list(attrs.get("tags") or raw.get("tags") or []),
        "npc_role": attrs.get("npc_role") or getattr(getattr(target, "db", None), "npc_role", None),
    }
    structured = {
        "id": content_id,
        "room_id": room_id,
        "identity": identity,
        "progression": {
            "stage": raw.get("stage") or "mortal",
            "realm": normalize_realm_display(raw.get("realm") or attrs.get("realm") or _resolve_realm_for_room(room_id)),
            "rank_tier": raw.get("rank_tier", "common"),
            "spawn_profile": {"room_id": room_id},
            "power_source": raw.get("power_source") or "template",
        },
        "primary_stats": deepcopy(raw.get("primary_stats") or attrs.get("primary_stats") or DEFAULT_PRIMARY_STATS),
        "combat_stats": deepcopy(raw.get("combat_stats") or attrs.get("combat_stats") or DEFAULT_COMBAT_STATS),
        "affinities": deepcopy(raw.get("affinities") or attrs.get("affinities") or {"element": None, "social_tags": [], "resist_tags": []}),
        "reserves": deepcopy(raw.get("reserves") or attrs.get("reserves") or {"resources": {}}),
        "npc_meta": {
            "talk_route": attrs.get("talk_route") or raw.get("talk_route"),
            "shop_id": attrs.get("shop_id") or raw.get("shop_id"),
            "interact_modes": list(raw.get("interact_modes") or attrs.get("interact_modes") or ["talk"]),
            "combat_profile": deepcopy(raw.get("combat_profile") or attrs.get("combat_profile") or DEFAULT_COMBAT_PROFILE),
            "relationship_profile": deepcopy(raw.get("relationship_profile") or attrs.get("relationship_profile") or DEFAULT_RELATIONSHIP_PROFILE),
            "projection_policy": deepcopy(raw.get("projection_policy") or attrs.get("projection_policy") or DEFAULT_PROJECTION_POLICY),
            "relocation_policy": deepcopy(raw.get("relocation_policy") or attrs.get("relocation_policy") or DEFAULT_RELOCATION_POLICY),
            "presentation": {"desc": desc},
        },
    }
    return _normalize_structured_npc(npc_id or content_id, structured)


def _build_npc_sheet(target, definition):
    definition = deepcopy(definition)
    combat_stats = definition["combat_stats"]
    runtime_hp = getattr(target.db, "hp", None)
    runtime_max_hp = getattr(target.db, "max_hp", None)
    if runtime_max_hp is not None:
        combat_stats["max_hp"] = int(runtime_max_hp)
    if runtime_hp is not None:
        combat_stats["hp"] = max(0, min(int(runtime_hp), combat_stats["max_hp"]))
    else:
        combat_stats["hp"] = max(0, min(int(combat_stats["hp"]), combat_stats["max_hp"]))
    return definition


def _write_compatibility_fields(target, sheet):
    identity = sheet["identity"]
    progression = sheet["progression"]
    combat_stats = sheet["combat_stats"]
    npc_meta = sheet["npc_meta"]

    target.db.content_id = identity.get("content_id")
    target.db.template_id = identity.get("template_id")
    target.db.npc_id = identity.get("template_id")
    target.db.npc_role = identity.get("npc_role")
    target.db.faction = identity.get("faction")
    target.db.tags = list(identity.get("tags", []))
    target.db.gender = identity.get("gender")
    target.db.realm = progression.get("realm")
    target.db.hp = combat_stats.get("hp")
    target.db.max_hp = combat_stats.get("max_hp")
    target.db.talk_route = npc_meta.get("talk_route")
    target.db.shop_id = npc_meta.get("shop_id")
    target.db.desc = npc_meta.get("presentation", {}).get("desc", getattr(target.db, "desc", "") or "")


def _resolve_realm_for_room(room_id):
    room = ROOM_DEFINITIONS.get(room_id, {})
    if not room:
        room = next((value for value in ROOM_DEFINITIONS.values() if value.get("content_id") == room_id), {})
    area_id = room.get("area_id")
    if area_id:
        area = AREA_DEFINITIONS.get(area_id) or {}
        if area.get("recommended_realm"):
            return get_recommended_realm_target(area["recommended_realm"])
        zone = ZONE_DEFINITIONS.get(area.get("zone_id")) or {}
        if zone.get("recommended_realm"):
            return get_recommended_realm_target(zone["recommended_realm"])
    return get_recommended_realm_target(room.get("recommended_realm")) or "凡人"
