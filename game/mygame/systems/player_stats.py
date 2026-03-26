"""玩家运行态数值与临时效果层。

负责内容：
- 基于统一角色模型输出便于其他系统消费的 stats 视图。
- 处理经验增长、气血 / 体力夹取、临时效果、主货币增减等运行态变化。
- 在不破坏角色模型结构的前提下，对旧字段进行最小写回。

不负责内容：
- 不定义角色基础模板和属性成长；这些在 `character_model.py`。
- 不实现具体物品 / 对象效果；这里只负责承接效果结果与查询状态。

主要输入 / 输出：
- 输入：玩家对象、经验变化、货币变化、effect key、duration。
- 输出：结构化 stats、境界变化结果、当前货币余额和效果文本。

上游调用者：
- `items.py`
- `effect_executor.py`
- `battle.py`
- `serializers.py`

排错优先入口：
- `get_stats`
- `apply_exp`
- `prune_expired_effects`
- `get_effect_modifier`
- `spend_currency`
"""

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
from .realms import (
    evaluate_breakthrough_requirements,
    format_entity_realm_display,
    get_default_realm_key,
    resolve_realm_progression,
)


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
        "gender": identity.get("gender"),
        "realm": progression["realm"],
        "realm_info": progression,
        "realm_display": progression.get("display_name", progression["realm"]),
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


def sync_cultivation_progression(caller, *, exp_total=None, current_realm=None, realm_key=None):
    """Resolve and write the structured cultivation progression back in one place."""
    ensure_character_model(caller)
    exp_total = int(getattr(caller.db, "exp", 0) if exp_total is None else exp_total)
    current_realm = getattr(caller.db, "realm", None) if current_realm is None else current_realm
    stored_progression = dict(getattr(caller.db, "progression", None) or {})
    resolved_realm_key = realm_key if realm_key is not None else stored_progression.get("realm_key") or get_default_realm_key()
    progression = resolve_realm_progression(exp_total, current_realm=current_realm, realm_key=resolved_realm_key)
    caller.db.exp = exp_total
    caller.db.progression = stored_progression
    caller.db.progression.update(progression)
    caller.db.realm = caller.db.progression["display_name"]
    ensure_character_model(caller)
    return dict(caller.db.progression)


def set_total_cultivation_exp(caller, exp_total):
    exp_total = int(exp_total or 0)
    if exp_total < 0:
        raise ValueError("cultivation exp cannot be negative")
    progression = sync_cultivation_progression(caller, exp_total=exp_total)
    return {"realm": progression["display_name"], "realm_info": progression, "exp": exp_total}


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
        # 0 或负向经验变化不推进境界，但会顺手把旧号的 realm 标准化一次。
        # 这样只要读到 stats，就能逐步把历史脏值纠正到当前境界规则。
        if stage == CULTIVATOR_STAGE:
            if current_realm not in (None, "", MORTAL_REALM) and not is_awakened_realm(current_realm):
                normalized_realm = sync_cultivation_progression(caller, exp_total=exp, current_realm=current_realm)["display_name"]
            elif is_awakened_realm(current_realm):
                normalized_realm = sync_cultivation_progression(caller, exp_total=exp, current_realm=current_realm)["display_name"]
            else:
                caller.db.exp = exp
                caller.db.realm = normalized_realm
        else:
            caller.db.realm = normalized_realm
        return normalized_realm, normalized_realm, exp
    exp += gain
    if stage == CULTIVATOR_STAGE:
        progression = sync_cultivation_progression(caller, exp_total=exp, current_realm=current_realm or old_realm)
        new_realm = progression["display_name"]
    else:
        new_realm = resolve_character_realm(stage, exp, current_realm=None, root=root)
        caller.db.exp = exp
    caller.db.realm = new_realm
    return old_realm, new_realm, exp


def try_breakthrough(caller):
    sheet = ensure_character_model(caller)
    progression = dict(sheet["progression"])
    target_realm_key = progression.get("next_realm_key")
    if not progression.get("can_breakthrough"):
        return {"ok": False, "reason": "not_ready", "realm": progression.get("display_name")}
    result = evaluate_breakthrough_requirements(caller, target_realm_key)
    if not result.get("can_breakthrough"):
        return {"ok": False, "reason": "requirements_not_met", "requirements": result, "realm": progression.get("display_name")}
    progression = sync_cultivation_progression(caller, exp_total=int(caller.db.exp or 0), realm_key=target_realm_key)
    return {"ok": True, "realm": progression["display_name"], "realm_info": progression}


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
    # 读取时即时清理过期效果，避免“面板已消失但数值仍生效”或相反的分裂状态。
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
    # 当前货币入口始终跟随主货币类型走，凡人默认铜钱，修士默认灵石。
    # 如果后续要支持混合扣费，需要在更高层显式指定币种，而不是改这个 helper 的语义。
    if primary_currency == PRIMARY_CURRENCY_COPPER:
        caller.db.copper = amount
        caller.db.currencies["copper"] = amount
        return caller.db.copper
    caller.db.spirit_stone = amount
    caller.db.currencies["spirit_stone"] = amount
    return caller.db.spirit_stone
