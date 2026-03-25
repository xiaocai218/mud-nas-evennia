"""Helpers for reading and updating player stats."""

import time

from .character_model import (
    CULTIVATOR_STAGE,
    MORTAL_REALM,
    PRIMARY_CURRENCY_COPPER,
    ensure_character_model,
    is_awakened_realm,
    resolve_character_realm,
)
from .content_loader import load_content
from .realms import get_realm_from_exp


EFFECT_DEFINITIONS = load_content("effects")


def get_stats(caller):
    sheet = ensure_character_model(caller)
    combat = sheet["combat_stats"]
    currencies = sheet["currencies"]
    progression = sheet["progression"]
    identity = sheet["identity"]
    return {
        "stage": identity["stage"],
        "root": identity["root"],
        "sect": identity.get("sect"),
        "realm": progression["realm"],
        "hp": combat["hp"],
        "max_hp": combat["max_hp"],
        "mp": combat["mp"],
        "max_mp": combat["max_mp"],
        "stamina": combat["stamina"],
        "max_stamina": combat["max_stamina"],
        "exp": progression["cultivation_exp"],
        "copper": currencies["copper"],
        "spirit_stone": currencies["spirit_stone"],
        "primary_currency": currencies["primary_currency"],
        "currencies": currencies,
        "primary_stats": sheet["primary_stats"],
        "combat_stats": combat,
        "equipment": sheet["equipment"],
        "affinities": sheet["affinities"],
        "reserves": sheet["reserves"],
    }


def apply_exp(caller, gain):
    ensure_character_model(caller)
    gain = int(gain or 0)
    exp = 0 if caller.db.exp is None else caller.db.exp
    stage = getattr(caller.db, "character_stage", None)
    root = getattr(caller.db, "spiritual_root", None)
    current_realm = getattr(caller.db, "realm", None)
    old_realm = resolve_character_realm(stage, exp, current_realm=current_realm, root=root)
    if gain <= 0:
        normalized_realm = old_realm
        if stage == CULTIVATOR_STAGE and current_realm not in (None, "", MORTAL_REALM) and not is_awakened_realm(current_realm):
            normalized_realm = get_realm_from_exp(exp)
        caller.db.realm = normalized_realm
        return normalized_realm, normalized_realm, exp
    exp += gain
    if stage == CULTIVATOR_STAGE:
        new_realm = old_realm if is_awakened_realm(old_realm) else get_realm_from_exp(exp)
    else:
        new_realm = resolve_character_realm(stage, exp, current_realm=None, root=root)
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
    stats = get_stats(caller)
    if stats["primary_currency"] == PRIMARY_CURRENCY_COPPER:
        return stats["copper"]
    return stats["spirit_stone"]


def add_currency(caller, amount):
    sheet = ensure_character_model(caller)
    amount = int(amount)
    return _set_primary_currency_balance(caller, sheet, get_currency(caller) + amount)


def spend_currency(caller, amount):
    sheet = ensure_character_model(caller)
    amount = int(amount)
    current = get_currency(caller)
    if current < amount:
        return False, current
    return True, _set_primary_currency_balance(caller, sheet, current - amount)


def _set_primary_currency_balance(caller, sheet, amount):
    amount = int(amount)
    primary_currency = sheet["currencies"]["primary_currency"]
    if primary_currency == PRIMARY_CURRENCY_COPPER:
        caller.db.copper = amount
        caller.db.currencies["copper"] = amount
        return caller.db.copper
    caller.db.spirit_stone = amount
    caller.db.currencies["spirit_stone"] = amount
    return caller.db.spirit_stone
