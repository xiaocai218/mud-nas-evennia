"""Shared effect execution helpers for items, objects and future skills."""

from .player_stats import add_temporary_effect, get_stats


def execute_effect(caller, effect):
    if not effect:
        return {"ok": False, "reason": "missing_effect"}

    effect_type = effect.get("type")
    if effect_type in {"restore_hp", "restore_stamina", "restore_both", "restore"}:
        return _execute_restore_effect(caller, effect, effect_type)
    if effect_type == "buff":
        return _execute_buff_effect(caller, effect)
    return {"ok": False, "reason": "unknown_effect"}


def _execute_restore_effect(caller, effect, effect_type):
    stats = get_stats(caller)
    hp_gain = 0
    stamina_gain = 0

    if effect_type in {"restore_hp", "restore_both", "restore"}:
        hp_gain = min(stats["max_hp"], stats["hp"] + int(effect.get("hp", 0) or 0)) - stats["hp"]
    if effect_type in {"restore_stamina", "restore_both", "restore"}:
        stamina_gain = min(stats["max_stamina"], stats["stamina"] + int(effect.get("stamina", 0) or 0)) - stats["stamina"]

    if effect_type == "restore_hp" and hp_gain <= 0:
        return {"ok": False, "reason": "hp_full"}
    if effect_type == "restore_stamina" and stamina_gain <= 0:
        return {"ok": False, "reason": "stamina_full"}
    if effect_type in {"restore_both", "restore"} and hp_gain <= 0 and stamina_gain <= 0:
        return {
            "ok": False,
            "reason": "all_full",
            "text": effect.get("full_text") or effect.get("text") or "你此刻状态安稳，暂时用不上这股灵息。",
        }

    caller.db.hp = stats["hp"] + hp_gain
    caller.db.stamina = stats["stamina"] + stamina_gain
    return {
        "ok": True,
        "effect_type": effect_type,
        "text": effect.get("text") or effect.get("full_text") or "一股温和气息在你体内散开。",
        "hp_gain": hp_gain,
        "hp_now": caller.db.hp,
        "max_hp": stats["max_hp"],
        "stamina_gain": stamina_gain,
        "stamina_now": caller.db.stamina,
        "max_stamina": stats["max_stamina"],
    }


def _execute_buff_effect(caller, effect):
    effect_key = effect.get("buff_key")
    if not effect_key:
        return {"ok": False, "reason": "missing_buff_key"}

    applied = add_temporary_effect(
        caller,
        effect_key,
        int(effect.get("buff_bonus", 0) or 0),
        int(effect.get("buff_duration", 0) or 0),
        effect.get("buff_label"),
    )
    return {
        "ok": True,
        "effect_type": effect_type_from_effect(applied),
        "text": effect.get("text") or effect.get("full_text") or "一股灵息短暂落在你身上。",
        "effect": applied,
    }


def effect_type_from_effect(effect):
    return effect.get("effect_type", "buff") if effect else "buff"


def format_effect_result(result, summary_title):
    if result.get("effect"):
        return f"{result['text']}\n|g{summary_title}|n: {result['effect']['label']}"

    hp_gain = result.get("hp_gain", 0)
    stamina_gain = result.get("stamina_gain", 0)
    parts = []
    if hp_gain:
        parts.append(f"气血 +{hp_gain}")
    if stamina_gain:
        parts.append(f"体力 +{stamina_gain}")
    summary = "，".join(parts) if parts else "状态未变化"

    status_parts = []
    if "hp_now" in result:
        status_parts.append(f"气血 {result['hp_now']}/{result['max_hp']}")
    if "stamina_now" in result:
        status_parts.append(f"体力 {result['stamina_now']}/{result['max_stamina']}")
    status_line = f"\n|g当前状态|n: {'，'.join(status_parts)}" if status_parts else ""
    return f"{result['text']}\n|g{summary_title}|n: {summary}{status_line}"
