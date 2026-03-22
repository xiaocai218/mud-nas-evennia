"""
Command sets
"""

from evennia import default_cmds

from .newbie import CmdAttack, CmdCultivate, CmdInventory, CmdNewbie, CmdRest, CmdStatus, CmdTalk, CmdTrain


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdNewbie())
        self.add(CmdStatus())
        self.add(CmdCultivate())
        self.add(CmdRest())
        self.add(CmdTrain())
        self.add(CmdTalk())
        self.add(CmdAttack())
        self.add(CmdInventory())


class AccountCmdSet(default_cmds.AccountCmdSet):
    key = "DefaultAccount"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class SessionCmdSet(default_cmds.SessionCmdSet):
    key = "DefaultSession"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
