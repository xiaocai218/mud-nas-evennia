"""
Commands

Commands describe the input the account can do to the game.
"""

from evennia.commands.default.muxcommand import MuxCommand
from systems.battle import is_character_in_battle


class Command(MuxCommand):
    """
    Base command for project-specific commands.
    """

    battle_allowed = False

    def at_pre_cmd(self):
        if is_character_in_battle(self.caller) and not getattr(self, "battle_allowed", False):
            self.caller.msg("你正处于战斗中，现在只能执行战斗相关操作。可使用：攻击、出牌、战况、队伍。")
            return True
        return super().at_pre_cmd()
