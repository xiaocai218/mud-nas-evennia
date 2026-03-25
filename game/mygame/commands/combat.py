"""Combat and battle commands."""

from .command import Command
from systems.battle import get_battle_snapshot, list_available_cards, list_available_targets, submit_action
from systems.combat import attack_enemy
from systems.player_stats import apply_exp, get_stats


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if isinstance(results, list) and results else results


class CmdTrain(Command):
    key = "练拳"
    aliases = ["train", "practice"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        target = get_target(caller, "木人桩")
        if not target:
            caller.msg("你环顾四周，没有找到适合练拳的木人桩。")
            return
        stats = get_stats(caller)
        cost = 5
        gain = 8
        if stats["stamina"] < cost:
            caller.msg(f"你刚摆开架势就觉得双臂发沉，至少需要 |w{cost}|n 点体力才能继续练拳。")
            return
        caller.db.stamina = max(0, stats["stamina"] - cost)
        old_realm, new_realm, exp = apply_exp(caller, gain)
        caller.msg(
            "你对着木人桩反复演练基础拳架，出拳、收势、转身都比刚才稳了几分。\n"
            f"|g本次练拳收获|n: 修为 +{gain}，体力 -{cost}\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}，体力 {caller.db.stamina}/{stats['max_stamina']}"
        )
        if new_realm != old_realm:
            caller.msg(f"|y你的气息在练拳中愈发凝练，境界提升至 {new_realm}。|n")


class CmdAttack(Command):
    key = "攻击"
    aliases = ["attack", "fight", "打"]
    locks = "cmd:all()"
    help_category = "战斗"
    battle_allowed = True

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要攻击谁？用法：|w攻击 青木傀儡|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近找到这个目标。")
            return
        if not getattr(target.db, "combat_target", False):
            caller.msg(f"{target.key} 并不是适合出手的目标。")
            return
        result = attack_enemy(caller, target)
        if not result.get("ok"):
            caller.msg("你现在无法完成这次攻击。")
            return
        battle = result.get("battle")
        if not battle:
            caller.msg("战斗未能正确建立。")
            return
        caller.msg(_render_battle_summary(battle))


class CmdBattleStatus(Command):
    key = "战况"
    aliases = ["battle", "battle_status"]
    locks = "cmd:all()"
    help_category = "战斗"
    battle_allowed = True

    def func(self):
        battle = get_battle_snapshot(self.caller)
        if not battle:
            self.caller.msg("你当前没有进入战斗。")
            return
        self.caller.msg(_render_battle_summary(battle))


class CmdPlayCard(Command):
    key = "出牌"
    aliases = [
        "playcard",
        "play",
        "普通攻击",
        "防御",
        "使用战斗物品",
        "物品",
        "灵击",
        "金锋术",
        "回春诀",
        "水幕诀",
        "炽焰诀",
        "岩甲诀",
    ]
    locks = "cmd:all()"
    help_category = "战斗"
    battle_allowed = True

    def func(self):
        caller = self.caller
        battle = get_battle_snapshot(caller)
        if not battle:
            caller.msg("你当前没有进入战斗。")
            return
        raw = self.args.strip()
        invoked_as = (getattr(self, "cmdstring", "") or "").strip()
        direct_card_invocation = invoked_as and invoked_as != self.key and invoked_as in self.aliases
        if direct_card_invocation:
            raw = f"{invoked_as} {raw}".strip()
        if not raw:
            caller.msg("用法：|w出牌 普通攻击 目标名|n、|w出牌 防御|n、|w出牌 灵击 目标名|n、|w出牌 物品 物品ID|n")
            return
        parts = raw.split()
        card_name = parts[0]
        mapping = {
            "普通攻击": "basic_attack",
            "攻击": "basic_attack",
            "防御": "guard",
            "格挡": "guard",
            "灵击": "spirit_blast",
            "金锋术": "metal_edge",
            "回春诀": "wood_rejuvenation",
            "水幕诀": "water_barrier",
            "炽焰诀": "fire_burst",
            "岩甲诀": "earth_guard",
            "物品": "use_combat_item",
        }
        card_id = mapping.get(card_name, card_name)
        target_id = None
        item_id = None
        if card_id == "use_combat_item":
            item_id = parts[1] if len(parts) > 1 else None
        elif len(parts) > 1:
            target_name = " ".join(parts[1:])
            for target in list_available_targets(caller):
                if target["name"] == target_name:
                    target_id = target["combatant_id"]
                    break
        result = submit_action(caller, card_id, target_id=target_id, item_id=item_id)
        if not result.get("ok"):
            caller.msg(f"出牌失败：{result.get('reason')}。")
            return
        caller.msg(_render_battle_summary(result["battle"]))


def _render_battle_summary(battle):
    current_actor = battle.get("current_actor_name") or "无"
    participants = battle.get("participants", []) or []
    player_side = [combatant for combatant in participants if combatant.get("side") == "player"]
    enemy_side = [combatant for combatant in participants if combatant.get("side") == "enemy"]
    current_actor_side = _resolve_current_actor_side(battle)
    turn_hint = _render_turn_hint(current_actor, current_actor_side)

    lines = [
        f"|g战斗状态|n: {battle['status']} / 回合数 {battle['turn_count']}",
        f"|g当前行动者|n: {current_actor}",
        f"|g当前节奏|n: {turn_hint}",
        "|g我方状态|n:",
    ]
    for combatant in player_side:
        lines.append(_render_combatant_line(combatant, highlight=combatant["name"] == current_actor))
    lines.append("|g敌方状态|n:")
    for combatant in enemy_side:
        lines.append(_render_combatant_line(combatant, highlight=combatant["name"] == current_actor))
    if player_side or enemy_side:
        lines.append("|g当前对阵|n: " + _render_battle_state_overview(player_side, enemy_side))
    recent_reports = battle.get("round_reports")[-3:] if battle.get("round_reports") else []
    if recent_reports:
        lines.append("|g最近回合战报|n:")
        for report in recent_reports:
            lines.extend(_render_round_report(report))
    elif battle.get("log"):
        lines.append("|g最近战报|n:")
        for entry in battle.get("log")[-3:]:
            lines.append(f"- {_format_battle_log_entry(entry)}")
    if battle.get("current_actor_name") and battle["status"] == "active":
        lines.append("|g可用卡牌|n: " + "、".join(card["name"] for card in battle.get("available_cards", []) or []))
        lines.append("|g出牌方式|n: 直接输入卡牌名，或使用 |w出牌 卡牌名 [目标]|n")
    return "\n".join(lines)


def _display_name_for_log_entry(entry):
    card_id = entry.get("card_id")
    if card_id:
        return {
            "basic_attack": "普通攻击",
            "guard": "防御",
            "use_combat_item": "使用战斗物品",
            "spirit_blast": "灵击",
            "metal_edge": "金锋术",
            "wood_rejuvenation": "回春诀",
            "water_barrier": "水幕诀",
            "fire_burst": "炽焰诀",
            "earth_guard": "岩甲诀",
            "recover_instinct": "兽性回生",
        }.get(card_id, card_id)
    return {
        "basic_attack": "普通攻击",
        "guard": "防御",
        "use_combat_item": "使用战斗物品",
        "skill_card": "技能",
    }.get(entry.get("type"), entry.get("type", "unknown"))


def _render_turn_hint(current_actor_name, current_actor_side):
    if current_actor_name == "无":
        return "当前没有可行动单位。"
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
    parts = [
        f"{marker}{combatant['name']}",
        f"气血 {combatant['hp']}/{combatant['max_hp']}",
        f"灵力 {combatant['mp']}/{combatant['max_mp']}",
        f"体力 {combatant['stamina']}/{combatant['max_stamina']}",
        f"护盾 {combatant.get('shield', 0)}",
        state,
    ]
    cooldowns = combatant.get("cooldowns") or {}
    if cooldowns:
        parts.append("冷却 " + "、".join(f"{name}:{value}" for name, value in cooldowns.items()))
    return " / ".join(parts)


def _format_battle_log_entry(entry):
    actor_name = entry.get("actor_name", "未知")
    target_name = entry.get("target_name")
    value = entry.get("value", 0)
    action_name = _display_name_for_log_entry(entry)
    entry_type = entry.get("type")

    if entry_type == "basic_attack":
        return f"{actor_name} 对 {target_name} 造成 {value} 点伤害。"
    if entry_type == "guard":
        return f"{actor_name} 使用 {action_name}，获得 {value} 点护盾。"
    if entry_type == "use_combat_item":
        text = entry.get("text") or "使用了战斗物品"
        return f"{actor_name}{text}，效果值 {value}。"
    if entry_type == "skill_card":
        if target_name:
            return f"{actor_name} 使用 {action_name} 命中 {target_name}，效果值 {value}。"
        return f"{actor_name} 使用 {action_name}，效果值 {value}。"
    return f"{actor_name} 执行了 {action_name}。"


def _render_battle_state_overview(player_side, enemy_side):
    left = "；".join(_render_state_chip(combatant) for combatant in player_side) or "我方无可行动单位"
    right = "；".join(_render_state_chip(combatant) for combatant in enemy_side) or "敌方无可行动单位"
    return f"我方 {left} / 敌方 {right}"


def _render_state_chip(combatant):
    stamina = combatant.get("stamina")
    max_stamina = combatant.get("max_stamina")
    stamina_text = "" if stamina is None or max_stamina is None else f", 体力 {stamina}/{max_stamina}"
    return (
        f"{combatant['name']}("
        f"气血 {combatant['hp']}/{combatant['max_hp']}, "
        f"灵力 {combatant['mp']}/{combatant['max_mp']}, "
        f"护盾 {combatant.get('shield', 0)}"
        f"{stamina_text}"
        f")"
    )


def _render_round_report(report):
    actor_side_label = "我方回合" if report.get("actor_side") == "player" else "敌方回合"
    lines = [
        f"- 回合 {report.get('turn_count')} | {actor_side_label} | {report.get('actor_name')}",
        f"  出手前: {_render_snapshot_overview(report.get('before') or {})}",
        f"  行动: {_format_battle_log_entry(report.get('entry') or {})}",
        f"  出手后: {_render_snapshot_overview(report.get('after') or {})}",
    ]
    return lines


def _render_snapshot_overview(snapshot):
    player_text = "；".join(_render_state_chip(entry) for entry in snapshot.get("player", []) or []) or "我方无可行动单位"
    enemy_text = "；".join(_render_state_chip(entry) for entry in snapshot.get("enemy", []) or []) or "敌方无可行动单位"
    return f"我方 {player_text} / 敌方 {enemy_text}"
