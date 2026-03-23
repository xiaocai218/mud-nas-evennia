"""
Command sets
"""

from evennia import default_cmds

from .combat import CmdAttack, CmdTrain
from .core import CmdGather, CmdNewbie, CmdRead, CmdStatus, CmdTrigger
from .cultivation import CmdCultivate, CmdRecoverHp, CmdRest
from .devtools import CmdContent
from .inventory import CmdInventory, CmdRefine, CmdUseItem
from .social import CmdQuest, CmdTalk


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdNewbie())
        self.add(CmdStatus())
        self.add(CmdRead())
        self.add(CmdGather())
        self.add(CmdTrigger())
        self.add(CmdCultivate())
        self.add(CmdRest())
        self.add(CmdRecoverHp())
        self.add(CmdTrain())
        self.add(CmdTalk())
        self.add(CmdAttack())
        self.add(CmdInventory())
        self.add(CmdRefine())
        self.add(CmdUseItem())
        self.add(CmdQuest())
        self.add(CmdContent())


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
