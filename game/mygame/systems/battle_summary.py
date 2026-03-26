"""Battle HUD rendering shared by commands and terminal sync."""

from systems.battle_cards import get_card_display_name
from systems.battle_text import format_battle_finished_summary, format_battle_log_entry


def render_battle_summary(battle, viewer_name=None):
    current_actor = battle.get("current_actor_name") or "无"
    current_actor_display = battle.get("current_actor_display_name") or current_actor
    participants = battle.get("participants", []) or []
    player_side = [combatant for combatant in participants if combatant.get("side") == "player"]
    enemy_side = [combatant for combatant in participants if combatant.get("side") == "enemy"]
    current_actor_side = _resolve_current_actor_side(battle)
    turn_hint = _render_turn_hint(current_actor, current_actor_side, viewer_name=viewer_name)

    current_actor_line = current_actor_display if current_actor_display == current_actor else f"{current_actor} / {current_actor_display}"

    lines = [
        f"|g战斗状态|n: {battle['status']} / 回合数 {battle['turn_count']}",
        f"|g当前行动者|n: {current_actor_line}",
        f"|g当前节奏|n: {turn_hint}",
        "|g战场摘要|n: " + _render_battle_meta_summary(battle),
        "|g我方状态|n:",
    ]
    for combatant in player_side:
        lines.append(_render_combatant_line(combatant, highlight=combatant["name"] == current_actor))
    lines.append("|g敌方状态|n:")
    for combatant in enemy_side:
        lines.append(_render_combatant_line(combatant, highlight=combatant["name"] == current_actor))
    if player_side or enemy_side:
        lines.append("|g当前对阵|n: " + _render_battle_state_overview(player_side, enemy_side))
    latest_entry = _get_latest_log_entry(battle)
    if latest_entry:
        lines.append(_render_latest_action_line(latest_entry))
    lines.extend(_render_battle_footer(battle, current_actor, current_actor_side, viewer_name=viewer_name, current_actor_display=current_actor_display))
    return "\n".join(lines)


def _render_battle_footer(battle, current_actor, current_actor_side, viewer_name=None, current_actor_display=None):
    if battle["status"] == "finished":
        return _render_finished_footer(battle)
    if not battle.get("current_actor_name"):
        return []
    if current_actor == viewer_name:
        return _render_current_actor_footer(battle)
    if current_actor_side == "player":
        return _render_teammate_waiting_footer(current_actor_display or current_actor)
    return []


def _get_latest_log_entry(battle):
    log = battle.get("log") or []
    return log[-1] if log else None


def _render_latest_action_line(entry):
    return "|g上一次动作|n: " + format_battle_log_entry(entry)


def _render_finished_footer(battle):
    return [
        "|g战斗结束|n: " + format_battle_finished_summary(battle).replace("[战斗结束] ", ""),
        "|g脱战提示|n: 你已脱离战斗。",
    ]


def _render_current_actor_footer(battle):
    return [
        "|g可用卡牌|n: " + "、".join(card["name"] for card in battle.get("available_cards", []) or []),
        "|g出牌方式|n: 直接输入卡牌名，或使用 |w出牌 卡牌名 [目标]|n",
    ]


def _render_teammate_waiting_footer(current_actor):
    return [f"|g行动提示|n: 当前由队友 {current_actor} 行动，你可等待其出手或查看战斗记录。"]


def _render_turn_hint(current_actor_name, current_actor_side, viewer_name=None):
    if current_actor_name == "无":
        return "当前没有可行动单位。"
    if current_actor_side == "player" and viewer_name and current_actor_name == viewer_name:
        return "轮到你出手。"
    if current_actor_side == "player" and viewer_name and current_actor_name != viewer_name:
        return f"轮到队友 {current_actor_name} 出手。"
    if current_actor_side == "player":
        return f"轮到你方行动，由 {current_actor_name} 出手。"
    if current_actor_side == "enemy":
        return f"轮到敌方行动，由 {current_actor_name} 出手。"
    return f"当前由 {current_actor_name} 行动。"


def _resolve_current_actor_side(battle):
    current_actor = battle.get("current_actor_name")
    for combatant in battle.get("participants", []) or []:
        if combatant.get("name") == current_actor:
            return combatant.get("side")
    return None


def _render_combatant_line(combatant, highlight=False):
    state = "存活" if combatant["alive"] else "倒下"
    marker = ">> " if highlight else "- "
    resources = _get_resources(combatant)
    parts = [
        f"{marker}{combatant.get('display_name') or combatant['name']}",
        f"气血 {resources['hp']}/{resources['max_hp']}",
        f"灵力 {resources['mp']}/{resources['max_mp']}",
        f"体力 {resources['stamina']}/{resources['max_stamina']}",
        f"护盾 {resources['shield']}",
        state,
    ]
    effects = _render_effects_text(combatant.get("effects") or [])
    if effects:
        parts.append(f"状态 {effects}")
    cooldowns = combatant.get("cooldowns") or {}
    if cooldowns:
        parts.append("冷却 " + "、".join(f"{name}:{value}" for name, value in cooldowns.items()))
    return " / ".join(parts)


def _render_battle_state_overview(player_side, enemy_side):
    left = "；".join(_render_state_chip(combatant) for combatant in player_side) or "我方无可行动单位"
    right = "；".join(_render_state_chip(combatant) for combatant in enemy_side) or "敌方无可行动单位"
    return f"我方 {left} / 敌方 {right}"


def _render_state_chip(combatant):
    resources = _get_resources(combatant)
    stamina = resources.get("stamina")
    max_stamina = resources.get("max_stamina")
    stamina_text = "" if stamina is None or max_stamina is None else f", 体力 {stamina}/{max_stamina}"
    effects = _render_effects_text(combatant.get("effects") or [])
    effect_text = "" if not effects else f", 状态 {effects}"
    return (
        f"{combatant.get('display_name') or combatant['name']}("
        f"气血 {resources['hp']}/{resources['max_hp']}, "
        f"灵力 {resources['mp']}/{resources['max_mp']}, "
        f"护盾 {resources['shield']}"
        f"{stamina_text}"
        f"{effect_text}"
        f")"
    )


def _render_effects_text(effects):
    labels = []
    for effect in effects:
        effect_type = effect.get("type")
        if effect_type == "guard":
            reduce_pct = int(effect.get("damage_reduction_pct", 0) or 0)
            block_pct = int(effect.get("block_chance_pct", 0) or 0)
            labels.append(f"防御(减普攻{reduce_pct}%, 格挡{block_pct}%)")
        elif effect.get("shield", 0) > 0:
            labels.append(f"{_display_name_for_log_entry({'card_id': effect_type})}(护盾中)")
        elif effect_type:
            labels.append(_display_name_for_log_entry({"card_id": effect_type}))
    return "、".join(labels)


def _get_resources(combatant):
    resources = dict(combatant.get("resources") or {})
    if resources:
        return {
            "hp": resources.get("hp", combatant.get("hp", 0)),
            "max_hp": resources.get("max_hp", combatant.get("max_hp", 0)),
            "mp": resources.get("mp", combatant.get("mp", 0)),
            "max_mp": resources.get("max_mp", combatant.get("max_mp", 0)),
            "stamina": resources.get("stamina", combatant.get("stamina", 0)),
            "max_stamina": resources.get("max_stamina", combatant.get("max_stamina", 0)),
            "shield": resources.get("shield", combatant.get("shield", 0)),
        }
    return {
        "hp": combatant.get("hp", 0),
        "max_hp": combatant.get("max_hp", 0),
        "mp": combatant.get("mp", 0),
        "max_mp": combatant.get("max_mp", 0),
        "stamina": combatant.get("stamina", 0),
        "max_stamina": combatant.get("max_stamina", 0),
        "shield": combatant.get("shield", 0),
    }


def _render_battle_meta_summary(battle):
    if battle.get("round_reports"):
        latest = battle["round_reports"][-1]
        after = latest.get("after") or {}
        meta = after.get("meta") or {}
        if meta:
            return f"我方存活 {meta.get('alive_player_count', 0)} 人 / 敌方存活 {meta.get('alive_enemy_count', 0)} 人"
    player_alive = sum(1 for entry in battle.get("participants", []) if entry.get("side") == "player" and entry.get("alive"))
    enemy_alive = sum(1 for entry in battle.get("participants", []) if entry.get("side") == "enemy" and entry.get("alive"))
    return f"我方存活 {player_alive} 人 / 敌方存活 {enemy_alive} 人"


def _display_name_for_log_entry(entry):
    card_id = entry.get("card_id")
    if card_id:
        return get_card_display_name(card_id=card_id)
    return get_card_display_name(entry_type=entry.get("type"))
