"""NPC interaction and quest commands."""

from .command import Command
from systems.dialogues import get_dialogue
from systems.npc_routes import run_npc_route
from systems.quests import get_quest_status_text


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
