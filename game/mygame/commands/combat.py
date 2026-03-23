"""Combat and combat-adjacent commands."""

from .command import Command
from systems.combat import attack_training_target
from systems.player_stats import apply_exp, get_stats
from systems.quests import get_quest_state


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if results else None


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
        result = attack_training_target(caller, target)
        if not result["ok"]:
            caller.msg(f"你提气欲上，却发现体力不足。至少需要 |w{result['cost']}|n 点体力才能出手。")
            return
        if result["result"] == "kill":
            caller.msg(
                f"你一掌击中 {target.key} 的胸口，木屑四散，傀儡轰然倒退。\n"
                f"|g战斗收获|n: 修为 +{result['reward_exp']}，体力 -{result['cost']}\n"
                f"你拾起了 |w{result['drop'].key}|n。\n"
                f"{target.key} 很快被重新扶正，似乎又能继续陪练了。"
            )
            if result["new_realm"] != result["old_realm"]:
                caller.msg(f"|y在实战磨砺之下，你的境界提升至 {result['new_realm']}。|n")
            return
        caller.msg(
            f"你朝 {target.key} 猛然出手，打得桩身一震。\n"
            f"{target.key} 随即回震而来，撞得你胸口微微发闷。\n"
            f"|g当前效果|n: {target.key} 气血 {result['target_hp']}/{result['target_max_hp']}，你的体力 {result['stamina_after']}/{result['max_stamina']}，你的气血 {result['hp_after']}/{result['max_hp']}"
        )
        if result["hp_after"] <= 0:
            stats = get_stats(caller)
            caller.db.hp = stats["max_hp"]
            caller.db.stamina = stats["max_stamina"]
            if caller.location and caller.location.key != "青云渡":
                home = caller.search("青云渡", global_search=True, quiet=True)
                if home:
                    caller.move_to(home[0], quiet=True)
            caller.msg("|r你被反震得眼前发黑，只得狼狈退回青云渡重新调息。|n")
