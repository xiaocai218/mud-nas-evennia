"""Helpers for per-character NPC relationship state."""

from copy import deepcopy


DEFAULT_RELATIONSHIP = {
    "npc_id": None,
    "affection": 0,
    "reputation": 0,
    "trust": 0,
    "quest_flags": [],
    "companion_unlocked": False,
    "projection_state": {
        "active": False,
        "projection_mode": None,
        "projection_template_id": None,
    },
    "relocation_state": {
        "hidden": False,
        "room_id_override": None,
        "content_id_override": None,
    },
}


def ensure_npc_relationships(caller):
    relationships = getattr(caller.db, "npc_relationships", None)
    if not isinstance(relationships, dict):
        relationships = {}
    caller.db.npc_relationships = relationships
    return relationships


def build_default_relationship(npc_id):
    record = deepcopy(DEFAULT_RELATIONSHIP)
    record["npc_id"] = npc_id
    return record


def get_npc_relationship(caller, npc_id):
    relationships = ensure_npc_relationships(caller)
    raw = relationships.get(npc_id) or {}
    record = build_default_relationship(npc_id)
    record.update({key: value for key, value in raw.items() if key in record})
    record["quest_flags"] = list(raw.get("quest_flags", record["quest_flags"]))
    record["projection_state"] = {**record["projection_state"], **dict(raw.get("projection_state") or {})}
    record["relocation_state"] = {**record["relocation_state"], **dict(raw.get("relocation_state") or {})}
    return record


def set_npc_relationship(caller, npc_id, updates):
    relationships = ensure_npc_relationships(caller)
    current = get_npc_relationship(caller, npc_id)
    updates = dict(updates or {})
    merged = {**current, **{key: value for key, value in updates.items() if key in current}}
    if "quest_flags" in updates:
        merged["quest_flags"] = list(updates.get("quest_flags") or [])
    if "projection_state" in updates:
        merged["projection_state"] = {**current["projection_state"], **dict(updates.get("projection_state") or {})}
    if "relocation_state" in updates:
        merged["relocation_state"] = {**current["relocation_state"], **dict(updates.get("relocation_state") or {})}
    relationships[npc_id] = merged
    caller.db.npc_relationships = relationships
    return deepcopy(merged)


def adjust_npc_relationship_metric(caller, npc_id, metric, delta):
    if metric not in {"affection", "reputation", "trust"}:
        raise ValueError("unsupported_metric")
    current = get_npc_relationship(caller, npc_id)
    return set_npc_relationship(caller, npc_id, {metric: int(current.get(metric, 0)) + int(delta)})


def clear_npc_relationship(caller, npc_id):
    relationships = ensure_npc_relationships(caller)
    relationships.pop(npc_id, None)
    caller.db.npc_relationships = relationships
