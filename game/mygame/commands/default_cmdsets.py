"""
Command sets
"""

from evennia.commands.default.cmdset_character import CharacterCmdSet as EvenniaCharacterCmdSet

from .chat import (
    CmdChannels,
    CmdMuteChannel,
    CmdPrivateChat,
    CmdSystemChannel,
    CmdTeamChat,
    CmdUnmuteChannel,
    CmdWorldChat,
)
from .combat import CmdAttack, CmdBattleStatus, CmdPlayCard, CmdTrain
from .core import CmdGather, CmdNewbie, CmdRead, CmdStatus, CmdTrigger
from .cultivation import CmdCultivate, CmdRecoverHp, CmdRest
from .devtools import (
    CmdContent,
    CmdTestAddMoney,
    CmdTestBattleRoom,
    CmdTestChooseRoot,
    CmdTestGoto,
    CmdTestRefreshEnemy,
    CmdTestResetBattle,
    CmdTestResetRoot,
)
from .inventory import CmdInventory, CmdRefine, CmdUseItem
from .market import (
    CmdBuyMarketItem,
    CmdCancelMarketListing,
    CmdClaimMarketEarnings,
    CmdListMarketItem,
    CmdListMyMarket,
    CmdMarket,
)
from .shop import CmdBuy, CmdShop
from .social import CmdQuest, CmdResetQuest, CmdTalk
from .team import (
    CmdAcceptTeamInvite,
    CmdCreateTeam,
    CmdInviteTeam,
    CmdLeaveTeam,
    CmdListTeamInvites,
    CmdRejectTeamInvite,
    CmdTeamStatus,
)
from .trade import CmdAcceptTrade, CmdCancelTrade, CmdRejectTrade, CmdTrade


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
        self.add(CmdBattleStatus())
        self.add(CmdPlayCard())
        self.add(CmdInventory())
        self.add(CmdRefine())
        self.add(CmdUseItem())
        self.add(CmdWorldChat())
        self.add(CmdTeamChat())
        self.add(CmdPrivateChat())
        self.add(CmdSystemChannel())
        self.add(CmdChannels())
        self.add(CmdMuteChannel())
        self.add(CmdUnmuteChannel())
        self.add(CmdTeamStatus())
        self.add(CmdCreateTeam())
        self.add(CmdInviteTeam())
        self.add(CmdAcceptTeamInvite())
        self.add(CmdRejectTeamInvite())
        self.add(CmdListTeamInvites())
        self.add(CmdLeaveTeam())
        self.add(CmdTrade())
        self.add(CmdAcceptTrade())
        self.add(CmdRejectTrade())
        self.add(CmdCancelTrade())
        self.add(CmdMarket())
        self.add(CmdListMarketItem())
        self.add(CmdBuyMarketItem())
        self.add(CmdCancelMarketListing())
        self.add(CmdListMyMarket())
        self.add(CmdClaimMarketEarnings())
        self.add(CmdShop())
        self.add(CmdBuy())
        self.add(CmdQuest())
        self.add(CmdResetQuest())
        self.add(CmdContent())
        self.add(CmdTestGoto())
        self.add(CmdTestAddMoney())
        self.add(CmdTestBattleRoom())
        self.add(CmdTestRefreshEnemy())
        self.add(CmdTestResetBattle())
        self.add(CmdTestChooseRoot())
        self.add(CmdTestResetRoot())
