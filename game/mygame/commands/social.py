"""NPC interaction and quest commands."""

from .command import Command
from systems.dialogues import get_dialogue
from systems.interaction_errors import resolve_interaction_error_message
from systems.npc_routes import run_npc_route
from systems.quests import get_quest_status_text, reset_all_quest_progress
from systems.serializers import serialize_npc_relationship_detail, serialize_person_detail
from systems.terminal_presenters import render_npc_relationship_detail, render_person_detail
from systems.targeting import find_target_in_room


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
        target = find_target_in_room(caller, self.args.strip())
        if not target:
            caller.msg(resolve_interaction_error_message("target_not_found"))
            return
        if not getattr(target.db, "npc_role", None):
            caller.msg(resolve_interaction_error_message("target_not_talkable", target=target.key))
            return
        if run_npc_route(caller, getattr(target.db, "talk_route", None)):
            return
        caller.msg(get_dialogue("common", "generic_npc", target=target.key))


class CmdQuest(Command):
    key = "任务"
    aliases = ["quest", "missions"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        caller.msg(get_quest_status_text(caller))


class CmdPersonInfo(Command):
    key = "信息"
    aliases = ["info", "查看", "inspect", "观察"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("用法：信息 目标名")
            return
        target = find_target_in_room(caller, self.args.strip())
        if not target:
            caller.msg(resolve_interaction_error_message("target_not_found"))
            return
        detail = serialize_person_detail(target, viewer=caller)
        if not detail:
            caller.msg(resolve_interaction_error_message("target_not_person", target=target.key))
            return
        caller.msg(render_person_detail(detail))


class CmdNpcRelationship(Command):
    key = "关系"
    aliases = ["favor", "好感", "relation", "关系查看"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("用法：关系 NPC名")
            return
        target = find_target_in_room(caller, self.args.strip())
        if not target:
            caller.msg(resolve_interaction_error_message("target_not_found"))
            return
        detail = serialize_npc_relationship_detail(caller, target)
        if not detail:
            caller.msg(resolve_interaction_error_message("npc_relationship_unavailable", target=target.key))
            return
        caller.msg(render_npc_relationship_detail(detail))


class CmdResetQuest(Command):
    key = "重置任务"
    aliases = ["questreset", "任务重置"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        reset_all_quest_progress(caller)
        caller.msg("任务状态已重置。你现在已回到接取任务之前的状态。当前只重置任务进度，不移除已有奖励物品。")
