"""Helpers for reading and updating player stats."""

import time

from .character_profiles import get_character_profile
from .content_loader import load_content
from .realms import get_default_realm, get_realm_from_exp


EFFECT_DEFINITIONS = load_content("effects")


def get_stats(caller):
    profile = get_character_profile(getattr(caller.db, "character_profile", None))
    return {
        "realm": caller.db.realm or profile["realm"] or get_default_realm(),
        "hp": profile["hp"] if caller.db.hp is None else caller.db.hp,
        "max_hp": profile["max_hp"] if caller.db.max_hp is None else caller.db.max_hp,
        "stamina": profile["stamina"] if caller.db.stamina is None else caller.db.stamina,
        "max_stamina": profile["max_stamina"] if caller.db.max_stamina is None else caller.db.max_stamina,
        "exp": profile["exp"] if caller.db.exp is None else caller.db.exp,
        "copper": profile.get("copper", 0) if caller.db.copper is None else caller.db.copper,
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
    effect_def = EFFECT_DEFINITIONS.get(effect_key, {})
    effects[effect_key] = {
        "effect_type": effect_def.get("effect_type", "buff"),
        "label": label or effect_def.get("label", "临时效果"),
        "modifiers": effect_def.get("modifiers", {"bonus": bonus}),
        "bonus": bonus,
        "expires_at": time.time() + duration,
    }
    _set_temp_effects(caller, effects)
    return effects[effect_key]


def get_temporary_effect(caller, effect_key):
    return prune_expired_effects(caller).get(effect_key)


def get_effect_modifier(caller, modifier_key):
    effects = prune_expired_effects(caller)
    total = 0
    for effect in effects.values():
        modifiers = effect.get("modifiers", {})
        total += int(modifiers.get(modifier_key, 0) or 0)
    return total


def get_cultivation_bonus(caller):
    return get_effect_modifier(caller, "cultivation_gain")


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
        effect_type = effect.get("effect_type", "buff")
        modifiers = effect.get("modifiers", {})
        modifier_parts = []
        for key, value in modifiers.items():
            if key == "cultivation_gain":
                modifier_parts.append(f"修炼{'+' if value >= 0 else ''}{value}")
            else:
                modifier_parts.append(f"{key}={'+' if value >= 0 else ''}{value}")
        modifier_text = f" [{'，'.join(modifier_parts)}]" if modifier_parts else ""
        prefix = "增益" if effect_type == "buff" else "减益"
        parts.append(f"{prefix}:{label}{modifier_text}({minutes}分{seconds}秒)")
    return "，".join(parts)


def get_currency(caller):
    return get_stats(caller)["copper"]


def add_currency(caller, amount):
    caller.db.copper = get_currency(caller) + int(amount)
    return caller.db.copper


def spend_currency(caller, amount):
    amount = int(amount)
    current = get_currency(caller)
    if current < amount:
        return False, current
    caller.db.copper = current - amount
    return True, caller.db.copper
