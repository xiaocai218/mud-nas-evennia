"""
Command sets
"""

from evennia.commands.default.cmdset_character import CharacterCmdSet as EvenniaCharacterCmdSet

from .chat import (
    CmdChannels,
    CmdMuteChannel,
    CmdPrivateChat,
    CmdTeamChat,
    CmdUnmuteChannel,
    CmdWorldChat,
)
from .combat import CmdAttack, CmdTrain
from .core import CmdGather, CmdNewbie, CmdRead, CmdStatus, CmdTrigger
from .cultivation import CmdCultivate, CmdRecoverHp, CmdRest
from .devtools import CmdContent
from .inventory import CmdInventory, CmdRefine, CmdUseItem
from .shop import CmdBuy, CmdShop
from .social import CmdQuest, CmdTalk
from .team import CmdAcceptTeamInvite, CmdCreateTeam, CmdInviteTeam, CmdLeaveTeam, CmdTeamStatus


class CharacterCmdSet(EvenniaCharacterCmdSet):
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
        self.add(CmdWorldChat())
        self.add(CmdTeamChat())
        self.add(CmdPrivateChat())
        self.add(CmdChannels())
        self.add(CmdMuteChannel())
        self.add(CmdUnmuteChannel())
        self.add(CmdTeamStatus())
        self.add(CmdCreateTeam())
        self.add(CmdInviteTeam())
        self.add(CmdAcceptTeamInvite())
        self.add(CmdLeaveTeam())
        self.add(CmdShop())
        self.add(CmdBuy())
        self.add(CmdQuest())
        self.add(CmdContent())
