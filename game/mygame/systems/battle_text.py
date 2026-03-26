"""Shared battle text formatting helpers."""

from systems.battle_cards import get_card_display_name


def format_battle_log_entry(entry, turn_count=None):
    resolved_turn_count = entry.get("turn_count") if turn_count is None else turn_count
    actor_name = entry.get("actor_name", "未知")
    target_name = entry.get("target_name")
    action_name = _display_name_for_log_entry(entry)
    entry_type = entry.get("type")
    action_result = entry.get("action_result") or {}
    result = action_result.get("result") or {}
    modifiers = action_result.get("modifiers") or {}
    value = result.get("damage", entry.get("value", 0)) if entry_type == "basic_attack" else entry.get("value", 0)
    prefix = _render_turn_prefix(resolved_turn_count)

    if entry_type == "basic_attack":
        if modifiers.get("guard_blocked", entry.get("guard_blocked")):
            return f"{prefix}{actor_name} 对 {target_name} 发起普通攻击，但被防御完全格挡。"
        notes = []
        guard_reduced = modifiers.get("guard_reduced", entry.get("guard_reduced"))
        shield_absorbed = modifiers.get("shield_absorbed", entry.get("shield_absorbed"))
        if guard_reduced:
            notes.append(f"防御减免 {guard_reduced}")
        if shield_absorbed:
            notes.append(f"护盾吸收 {shield_absorbed}")
        suffix = _render_note_suffix(notes)
        return f"{prefix}{actor_name} 对 {target_name} 造成 {value} 点伤害。{suffix}"
    if entry_type == "guard":
        block_chance_pct = entry.get("block_chance_pct", 0)
        resource_delta = action_result.get("resource_delta") or {}
        notes = []
        if resource_delta.get("source_mp"):
            notes.append(f"灵力 {resource_delta['source_mp']}")
        suffix = _render_note_suffix(notes)
        return f"{prefix}{actor_name} 使用 {action_name}，进入防御架势：普通攻击减伤 {value}%，并有 {block_chance_pct}% 概率完全格挡。{suffix}"
    if entry_type == "use_combat_item":
        text = entry.get("text") or "使用了战斗物品"
        return f"{prefix}{actor_name}{text}，效果值 {value}。"
    if entry_type == "skill_card":
        value = result.get("damage", result.get("heal", result.get("shield_gain", entry.get("value", 0))))
        resource_delta = action_result.get("resource_delta") or {}
        if target_name:
            notes = []
            shield_absorbed = modifiers.get("shield_absorbed", entry.get("shield_absorbed"))
            if shield_absorbed:
                notes.append(f"护盾吸收 {shield_absorbed}")
            if resource_delta.get("source_mp"):
                notes.append(f"灵力 {resource_delta['source_mp']}")
            suffix = _render_note_suffix(notes)
            return f"{prefix}{actor_name} 使用 {action_name} 命中 {target_name}，效果值 {value}。{suffix}"
        notes = []
        if result.get("shield_gain"):
            notes.append(f"获得护盾 {result['shield_gain']}")
        if result.get("heal"):
            notes.append(f"恢复气血 {result['heal']}")
        if resource_delta.get("source_mp"):
            notes.append(f"灵力 {resource_delta['source_mp']}")
        suffix = _render_note_suffix(notes)
        return f"{prefix}{actor_name} 使用 {action_name}，效果值 {value}。{suffix}"
    return f"{prefix}{actor_name} 执行了 {action_name}。"


def format_battle_finished_summary(battle):
    result = battle.get("result")
    defeated = [entry["name"] for entry in battle.get("participants", []) if entry.get("side") == "enemy" and not entry.get("alive")]
    if result == "victory":
        target_text = "、".join(defeated) if defeated else "敌人"
        return f"[战斗结束] {target_text} 倒下。"
    if result == "defeat":
        return "[战斗结束] 你不敌对手，战斗落败。"
    if result == "cancelled":
        return "[战斗结束] 战斗已取消。"
    return "[战斗结束] 战斗结束。"


def format_disengaged_notice():
    return "[脱战] 你已脱离战斗。"


def format_turn_ready_entry(actor_name, turn_count):
    if not actor_name or not turn_count:
        return ""
    return f"{_render_turn_prefix(turn_count)}轮到 {actor_name} 出手。"


def _render_turn_prefix(turn_count):
    return f"回合 {turn_count} | " if turn_count else ""


def _render_note_suffix(notes):
    return f"（{'，'.join(notes)}）" if notes else ""


def _display_name_for_log_entry(entry):
    card_id = entry.get("card_id")
    if card_id:
        return get_card_display_name(card_id=card_id)
    return get_card_display_name(entry_type=entry.get("type"))
