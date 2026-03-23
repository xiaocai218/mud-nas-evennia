"""Core player-facing commands."""

from evennia.utils import evtable

from .command import Command
from systems.items import get_inventory_items
from systems.player_stats import get_stats


class CmdNewbie(Command):
    key = "新手"
    aliases = ["begin", "guide", "入门"]
    locks = "cmd:all()"
    help_category = "入门"

    def func(self):
        self.caller.msg(
            "|g新手指引|n\n\n"
            "欢迎来到这个中文 MUD 原型服，目前已经可以完成最基础的登录与探索。\n\n"
            "你现在最推荐先试这些命令：\n"
            "  |wlook|n        查看当前场景\n"
            "  |whelp 新手|n   查看新手帮助条目\n"
            "  |w状态|n        查看当前角色状态\n"
            "  |w任务|n        查看当前新手任务\n"
            "  |w修炼|n        消耗体力获取修为\n"
            "  |w休息|n        恢复体力\n"
            "  |w调息|n        恢复气血\n"
            "  |w攻击 青木傀儡|n  进行最基础战斗测试\n"
            "  |w背包|n        查看当前获得的物品\n"
            "  |w炼化 青木碎片|n  将掉落物转成修为\n"
        )


class CmdStatus(Command):
    key = "状态"
    aliases = ["status", "stat", "属性"]
    locks = "cmd:all()"
    help_category = "角色"

    def func(self):
        caller = self.caller
        stats = get_stats(caller)
        location = caller.location.key if caller.location else "未知"
        item_count = len(get_inventory_items(caller))

        table = evtable.EvTable(border="cells", pad_width=1)
        table.add_row("姓名", caller.key)
        table.add_row("境界", stats["realm"])
        table.add_row("气血", f"{stats['hp']}/{stats['max_hp']}")
        table.add_row("体力", f"{stats['stamina']}/{stats['max_stamina']}")
        table.add_row("修为", str(stats["exp"]))
        table.add_row("位置", location)
        table.add_row("背包", f"{item_count} 件")
        self.caller.msg("|g角色状态|n\n%s" % table)
