"""Combat and battle commands."""

from .command import Command
from systems.battle_cards import get_direct_card_aliases, resolve_card_alias
from systems.battle import get_battle_snapshot, list_available_targets, submit_action
from systems.battle_summary import render_battle_summary
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
        self.caller.msg(_render_battle_summary(battle, viewer_name=self.caller.key))


class CmdPlayCard(Command):
    key = "出牌"
    aliases = ["playcard", "play", *get_direct_card_aliases()]
    locks = "cmd:all()"
    help_category = "战斗"
    battle_allowed = True

    def func(self):
        caller = self.caller
        battle = get_battle_snapshot(caller)
        if not battle:
            caller.msg("你当前没有进入战斗。")
            return
        request = _parse_play_card_request(self)
        if not request:
            caller.msg("用法：|w出牌 普通攻击 目标名|n、|w出牌 防御|n、|w出牌 灵击 目标名|n、|w出牌 物品 物品ID|n")
            return
        result = submit_action(caller, request["card_id"], target_id=request["target_id"], item_id=request["item_id"])
        if not result.get("ok"):
            caller.msg(f"出牌失败：{result.get('reason')}。")
            return
        return


def _render_battle_summary(battle, viewer_name=None):
    return render_battle_summary(battle, viewer_name=viewer_name)


def _parse_play_card_request(command):
    # 命令层只负责把“出牌/卡牌别名/目标文本”转成统一 submit_action 参数，
    # 后续如果再扩展快捷键或按钮入口，也应优先复用这个解析结果。
    caller = command.caller
    raw = command.args.strip()
    invoked_as = (getattr(command, "cmdstring", "") or "").strip()
    direct_card_invocation = invoked_as and invoked_as != command.key and invoked_as in command.aliases
    if direct_card_invocation:
        raw = f"{invoked_as} {raw}".strip()
    if not raw:
        return None

    parts = raw.split()
    card_id = resolve_card_alias(parts[0])
    target_id = None
    item_id = None
    if card_id == "use_combat_item":
        item_id = parts[1] if len(parts) > 1 else None
    elif len(parts) > 1:
        target_name = " ".join(parts[1:])
        target_id = _resolve_named_target_id(caller, target_name)
    return {"card_id": card_id, "target_id": target_id, "item_id": item_id}


def _resolve_named_target_id(caller, target_name):
    # 这里保持“只按当前战斗可选目标解析”，避免命令层误把房间内同名非战斗对象当作战斗目标。
    for target in list_available_targets(caller):
        if target["name"] == target_name:
            return target["combatant_id"]
    return None
