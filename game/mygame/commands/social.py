"""NPC interaction and quest commands."""

from .command import Command
from systems.quests import (
    NOT_STARTED,
    STAGE_ONE,
    STAGE_ONE_DONE,
    STAGE_TWO,
    STAGE_THREE,
    STAGE_THREE_READY,
    can_complete_stage_one,
    can_complete_stage_two,
    can_complete_stage_three,
    can_complete_side_herb_quest,
    complete_stage_one,
    complete_stage_two,
    complete_stage_three,
    complete_side_herb_quest,
    get_quest_state,
    get_quest_status_text,
    get_side_quest_state,
    grant_side_quest_rewards,
    grant_stage_rewards,
    start_side_herb_quest,
    start_third_stage,
    start_guide_quest,
    unlock_second_stage,
)


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
        quest_state = get_quest_state(caller)
        side_quest_state = get_side_quest_state(caller)
        if target.key == "巡山弟子":
            if quest_state == STAGE_THREE_READY:
                start_third_stage(caller)
                caller.msg(
                    "巡山弟子抬手向栈道深处一指，低声说道：\n"
                    "“近来溪谷边有只|w雾行山魈|n常来试探，你既然已经过了前两道关，就替我们去压一压它的凶性。”\n"
                    "“击退它一次，再回来报我。”\n"
                    "|g任务已接取|n: 击败一次雾行山魈。"
                )
                return
            if can_complete_stage_three(caller):
                complete_stage_three(caller)
                rewards = grant_stage_rewards(caller, STAGE_THREE)
                reward = rewards["reward"]
                caller.msg(
                    "巡山弟子掂了掂你带回的气息，神色终于缓了几分：\n"
                    "“不错，至少说明你遇事不会只顾着后退。这块木牌你收着，以后过外岗也方便些。”\n"
                    f"|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。"
                )
                if rewards["new_realm"] != rewards["old_realm"]:
                    caller.msg(f"|y这一路实战积累下来，你的境界提升至 {rewards['new_realm']}。|n")
                return
            if quest_state == STAGE_THREE:
                caller.msg("巡山弟子抱臂看着你，语气不高不低：\n“先去把雾行山魈压回溪谷里，再回来见我。”")
                return
            caller.msg("巡山弟子朝你略一点头：\n“我这里暂时没有新的差事，你先把手上的事办妥。”")
            return

        if target.key == "药庐学徒":
            if side_quest_state == NOT_STARTED:
                start_side_herb_quest(caller)
                caller.msg(
                    "药庐学徒抱着竹筛，闻了闻你身上的山雾气息，小声说道：\n"
                    "“溪谷那边偶尔能采到|w雾露果|n，我正缺一枚入药。若你手头有，就带回来给我。”\n"
                    "|g支线已接取|n: 交付一个雾露果。"
                )
                return
            if can_complete_side_herb_quest(caller):
                complete_side_herb_quest(caller)
                rewards = grant_side_quest_rewards(caller, "herb_delivery")
                reward = rewards["reward"]
                caller.msg(
                    "药庐学徒接过雾露果，立刻小心收进药囊里，神色明显轻松了不少：\n"
                    f"“太好了，这样今日的药就不耽误了。这包|w{reward.key}|n你拿着，算是谢礼。”\n"
                    f"|g支线完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。"
                )
                if rewards["new_realm"] != rewards["old_realm"]:
                    caller.msg(f"|y在药气与灵息交汇之间，你的境界提升至 {rewards['new_realm']}。|n")
                return
            if side_quest_state != NOT_STARTED:
                caller.msg("药庐学徒把竹筛抱得更紧了些：\n“若你带回了雾露果，就直接交给我。我今日只缺这一味。”")
                return

        if target.key != "守渡老人":
            caller.msg(f"{target.key} 朝你点了点头，却没有多说什么。")
            return

        if quest_state == NOT_STARTED:
            start_guide_quest(caller)
            caller.msg(
                "守渡老人抬眼看了你一会儿，慢声说道：\n"
                "“初来乍到，不必心急。先去古松林击倒一次|w青木傀儡|n，再回来见我。”\n"
                "“记住，体力不足就|w休息|n，气血受损就|w调息|n。”\n"
                "|g任务已接取|n: 击败一次青木傀儡。"
            )
            return
        if can_complete_stage_one(caller):
            complete_stage_one(caller)
            rewards = grant_stage_rewards(caller, STAGE_ONE)
            reward = rewards["reward"]
            caller.msg(
                "守渡老人看你气息沉稳了几分，微微点头：\n"
                "“不错，至少不是站都站不稳的新雏了。这点东西你先拿着。”\n"
                f"|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。"
            )
            if rewards["new_realm"] != rewards["old_realm"]:
                caller.msg(f"|y在这一番历练之后，你的境界提升至 {rewards['new_realm']}。|n")
            return
        if quest_state == STAGE_ONE:
            caller.msg("守渡老人拄着旧杖，朝东边古松林扬了扬下巴：\n“先去把青木傀儡打倒一次，再回来见我。”")
            return
        if quest_state == STAGE_ONE_DONE:
            unlock_second_stage(caller)
            caller.msg(
                "守渡老人略一沉吟，又抬杖指向北边石阶：\n"
                "“既然木傀儡难不住你，就再去|w问道石阶|n试试。”\n"
                "“那边有一尊|w山石傀儡|n，动作更沉更稳。击倒它一次，再回来。”\n"
                "|g任务已更新|n: 击败一次山石傀儡。"
            )
            return
        if can_complete_stage_two(caller):
            complete_stage_two(caller)
            rewards = grant_stage_rewards(caller, STAGE_TWO)
            reward = rewards["reward"]
            caller.msg(
                "守渡老人看着你带回的尘土气息，终于露出一点笑意：\n"
                "“能在石阶上站稳脚跟，才算真正迈出第一步。”\n"
                f"|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。"
            )
            if rewards["new_realm"] != rewards["old_realm"]:
                caller.msg(f"|y历练之后，你的境界提升至 {rewards['new_realm']}。|n")
            return
        if quest_state == STAGE_TWO:
            caller.msg("守渡老人敲了敲地面，提醒道：\n“去问道石阶，把山石傀儡击倒一次，再回来见我。”")
            return
        if quest_state == STAGE_THREE_READY:
            caller.msg(
                "守渡老人望向更高处的山道，声音仍旧平稳：\n"
                "“你可以去|w溪谷栈道|n看看，那里常有|w巡山弟子|n值守。”\n"
                "“若他愿意给你差事，便说明你已经够资格往前再走一步了。”"
            )
            return
        if quest_state == STAGE_THREE:
            caller.msg("守渡老人微微颔首：\n“既然已经接了巡山弟子的差事，就先去把它办妥。”")
            return
        caller.msg("守渡老人淡淡一笑：\n“该教你的入门路数，你已经走过一遍了。接下来，就看你自己能走多远。”")


class CmdQuest(Command):
    key = "任务"
    aliases = ["quest", "missions"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        caller.msg(get_quest_status_text(caller))
