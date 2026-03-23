"""NPC interaction and quest commands."""

from .command import Command
from systems.dialogues import get_dialogue
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
            caller.msg(get_dialogue("common", "talk_usage"))
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg(get_dialogue("common", "not_found"))
            return
        if not getattr(target.db, "npc_role", None):
            caller.msg(get_dialogue("common", "not_talkable", target=target.key))
            return
        quest_state = get_quest_state(caller)
        side_quest_state = get_side_quest_state(caller)
        if target.key == "巡山弟子":
            if quest_state == STAGE_THREE_READY:
                start_third_stage(caller)
                caller.msg(get_dialogue("scout", "stage_three_start"))
                return
            if can_complete_stage_three(caller):
                complete_stage_three(caller)
                rewards = grant_stage_rewards(caller, STAGE_THREE)
                reward = rewards["reward"]
                caller.msg(f"{get_dialogue('scout', 'stage_three_complete')}\n|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。")
                if rewards["new_realm"] != rewards["old_realm"]:
                    caller.msg(f"|y这一路实战积累下来，你的境界提升至 {rewards['new_realm']}。|n")
                return
            if quest_state == STAGE_THREE:
                caller.msg(get_dialogue("scout", "stage_three_remind"))
                return
            caller.msg(get_dialogue("scout", "idle"))
            return

        if target.key == "药庐学徒":
            if side_quest_state == NOT_STARTED:
                start_side_herb_quest(caller)
                caller.msg(get_dialogue("herbalist", "side_start"))
                return
            if can_complete_side_herb_quest(caller):
                complete_side_herb_quest(caller)
                rewards = grant_side_quest_rewards(caller, "herb_delivery")
                reward = rewards["reward"]
                caller.msg(f"{get_dialogue('herbalist', 'side_complete', reward_key=reward.key)}\n|g支线完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。")
                if rewards["new_realm"] != rewards["old_realm"]:
                    caller.msg(f"|y在药气与灵息交汇之间，你的境界提升至 {rewards['new_realm']}。|n")
                return
            if side_quest_state != NOT_STARTED:
                caller.msg(get_dialogue("herbalist", "side_remind"))
                return

        if target.key != "守渡老人":
            caller.msg(get_dialogue("common", "generic_npc", target=target.key))
            return

        if quest_state == NOT_STARTED:
            start_guide_quest(caller)
            caller.msg(get_dialogue("guide", "start"))
            return
        if can_complete_stage_one(caller):
            complete_stage_one(caller)
            rewards = grant_stage_rewards(caller, STAGE_ONE)
            reward = rewards["reward"]
            caller.msg(f"{get_dialogue('guide', 'stage_one_complete')}\n|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。")
            if rewards["new_realm"] != rewards["old_realm"]:
                caller.msg(f"|y在这一番历练之后，你的境界提升至 {rewards['new_realm']}。|n")
            return
        if quest_state == STAGE_ONE:
            caller.msg(get_dialogue("guide", "stage_one_remind"))
            return
        if quest_state == STAGE_ONE_DONE:
            unlock_second_stage(caller)
            caller.msg(get_dialogue("guide", "stage_two_unlock"))
            return
        if can_complete_stage_two(caller):
            complete_stage_two(caller)
            rewards = grant_stage_rewards(caller, STAGE_TWO)
            reward = rewards["reward"]
            caller.msg(f"{get_dialogue('guide', 'stage_two_complete')}\n|g任务完成|n: 修为 +{rewards['reward_exp']}，获得 |w{reward.key}|n。")
            if rewards["new_realm"] != rewards["old_realm"]:
                caller.msg(f"|y历练之后，你的境界提升至 {rewards['new_realm']}。|n")
            return
        if quest_state == STAGE_TWO:
            caller.msg(get_dialogue("guide", "stage_two_remind"))
            return
        if quest_state == STAGE_THREE_READY:
            caller.msg(get_dialogue("guide", "stage_three_ready"))
            return
        if quest_state == STAGE_THREE:
            caller.msg(get_dialogue("guide", "stage_three_remind"))
            return
        caller.msg(get_dialogue("guide", "done"))


class CmdQuest(Command):
    key = "任务"
    aliases = ["quest", "missions"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        caller.msg(get_quest_status_text(caller))
