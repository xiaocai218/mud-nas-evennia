"""Helpers for reading and updating player stats."""

from .realms import get_realm_from_exp


def get_stats(caller):
    return {
        "realm": caller.db.realm or "炼气一层",
        "hp": 100 if caller.db.hp is None else caller.db.hp,
        "max_hp": 100 if caller.db.max_hp is None else caller.db.max_hp,
        "stamina": 50 if caller.db.stamina is None else caller.db.stamina,
        "max_stamina": 50 if caller.db.max_stamina is None else caller.db.max_stamina,
        "exp": 0 if caller.db.exp is None else caller.db.exp,
    }


def apply_exp(caller, gain):
    exp = 0 if caller.db.exp is None else caller.db.exp
    old_realm = caller.db.realm or get_realm_from_exp(exp)
    exp += gain
    new_realm = get_realm_from_exp(exp)
    caller.db.exp = exp
    caller.db.realm = new_realm
    return old_realm, new_realm, exp


def clamp_hp(caller):
    stats = get_stats(caller)
    caller.db.hp = max(0, min(stats["hp"], stats["max_hp"]))
    return caller.db.hp, stats["max_hp"]


def clamp_stamina(caller):
    stats = get_stats(caller)
    caller.db.stamina = max(0, min(stats["stamina"], stats["max_stamina"]))
    return caller.db.stamina, stats["max_stamina"]
