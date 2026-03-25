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
    lines = [
        f"|g战斗状态|n: {battle['status']} / 回合数 {battle['turn_count']}",
        f"|g当前行动者|n: {battle.get('current_actor_name') or '无'}",
        "|g参战单位|n:",
    ]
    for combatant in battle.get("participants", []):
        state = "存活" if combatant["alive"] else "倒下"
        lines.append(
            f"- {combatant['name']} [{combatant['side']}] HP {combatant['hp']}/{combatant['max_hp']} MP {combatant['mp']}/{combatant['max_mp']} 护盾 {combatant.get('shield', 0)} [{state}]"
        )
    if battle.get("log"):
        last = battle["log"][-1]
        action_name = _display_name_for_log_entry(last)
        lines.append(f"|g最近行动|n: {last.get('actor_name', '系统')} -> {action_name} ({last.get('value', 0)})")
    if battle.get("current_actor_name"):
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
