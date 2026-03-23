"""NPC interaction and quest commands."""

from evennia.utils.create import create_object

from .command import Command
from systems.player_stats import apply_exp
from systems.quests import can_complete_guide_quest, complete_guide_quest, get_quest_state, start_guide_quest


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if results else None


class CmdTalk(Command):
    key = "交谈"
    aliases = ["talk", "对话", "问询"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想和谁交谈？用法：|w交谈 守渡老人|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not getattr(target.db, "npc_role", None):
            caller.msg(f"{target.key} 看起来并不打算和你搭话。")
            return
        if target.key != "守渡老人":
            caller.msg(f"{target.key} 朝你点了点头，却没有多说什么。")
            return

        quest_state = get_quest_state(caller)
        if quest_state == "not_started":
            start_guide_quest(caller)
            caller.msg(
                "守渡老人抬眼看了你一会儿，慢声说道：\n"
                "“初来乍到，不必心急。先去古松林击倒一次|w青木傀儡|n，再回来见我。”\n"
                "“记住，体力不足就|w休息|n，气血受损就|w调息|n。”\n"
                "|g任务已接取|n: 击败一次青木傀儡。"
            )
            return
        if can_complete_guide_quest(caller):
            complete_guide_quest(caller)
            old_realm, new_realm, exp = apply_exp(caller, 20)
            reward = create_object("typeclasses.items.Item", key="渡口药包", location=caller)
            reward.db.desc = "守渡老人交给你的简陋药包，带着些草木辛气，也许日后会派上用场。"
            caller.msg(
                "守渡老人看你气息沉稳了几分，微微点头：\n"
                "“不错，至少不是站都站不稳的新雏了。这点东西你先拿着。”\n"
                f"|g任务完成|n: 修为 +20，获得 |w{reward.key}|n。"
            )
            if new_realm != old_realm:
                caller.msg(f"|y在这一番历练之后，你的境界提升至 {new_realm}。|n")
            return
        if quest_state == "started":
            caller.msg("守渡老人拄着旧杖，朝东边古松林扬了扬下巴：\n“先去把青木傀儡打倒一次，再回来见我。”")
            return
        caller.msg("守渡老人淡淡一笑：\n“该教你的入门路数，你已经走过一遍了。接下来，就看你自己能走多远。”")


class CmdQuest(Command):
    key = "任务"
    aliases = ["quest", "missions"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        state = get_quest_state(caller)
        if state == "not_started":
            caller.msg("你暂时还没有接到任务。可以试试 |w交谈 守渡老人|n。")
            return
        if state == "started":
            done = "已完成" if caller.db.guide_quest_dummy_kill else "未完成"
            caller.msg("|g当前任务|n\n任务名: 渡口试手\n目标: 击败一次青木傀儡 [%s]\n交付人: 守渡老人" % done)
            return
        caller.msg("|g当前任务|n\n任务名: 渡口试手\n状态: 已完成\n守渡老人已经认可你完成了最基础的入门试炼。")
