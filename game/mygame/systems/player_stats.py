"""Helpers for reading and updating player stats."""

import time

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


def _get_temp_effects(caller):
    return dict(caller.db.temp_effects or {})


def _set_temp_effects(caller, effects):
    caller.db.temp_effects = effects


def prune_expired_effects(caller):
    effects = _get_temp_effects(caller)
    now = time.time()
    active = {key: value for key, value in effects.items() if value.get("expires_at", 0) > now}
    if active != effects:
        _set_temp_effects(caller, active)
    return active


def add_temporary_effect(caller, effect_key, bonus, duration, label):
    effects = prune_expired_effects(caller)
    effects[effect_key] = {
        "bonus": bonus,
        "expires_at": time.time() + duration,
        "label": label,
    }
    _set_temp_effects(caller, effects)
    return effects[effect_key]


def get_temporary_effect(caller, effect_key):
    return prune_expired_effects(caller).get(effect_key)


def get_cultivation_bonus(caller):
    effect = get_temporary_effect(caller, "cultivation_bonus")
    if not effect:
        return 0
    return int(effect.get("bonus", 0) or 0)


def get_active_effect_text(caller):
    effects = prune_expired_effects(caller)
    if not effects:
        return "无"
    now = time.time()
    parts = []
    for effect in effects.values():
        remaining = max(0, int(effect["expires_at"] - now))
        minutes, seconds = divmod(remaining, 60)
        label = effect.get("label", "临时效果")
        parts.append(f"{label}({minutes}分{seconds}秒)")
    return "，".join(parts)
