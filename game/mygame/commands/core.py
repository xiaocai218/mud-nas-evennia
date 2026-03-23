"""Core player-facing commands."""

from evennia.utils import evtable

from .command import Command
from systems.items import get_inventory_items
from systems.player_stats import get_stats
from systems.world_objects import (
    gather_from_object,
    get_readable_text,
    is_gatherable,
    is_readable,
    is_teleportable,
    teleport_via_object,
)


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if results else None


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
            "  |w阅读 渡口告示牌|n  查看当前渡口公告\n"
            "  |w采集 松纹草丛|n  在古松林采集基础草药\n"
            "  |w触发 回渡石|n  从溪谷栈道快速返回青云渡\n"
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


class CmdRead(Command):
    key = "阅读"
    aliases = ["read", "查看告示", "读"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想阅读什么？用法：|w阅读 渡口告示牌|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_readable(target):
            caller.msg(f"{target.key} 上并没有什么可读的内容。")
            return
        caller.msg(get_readable_text(caller, target))


class CmdGather(Command):
    key = "采集"
    aliases = ["gather", "采药", "收集"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想采集什么？用法：|w采集 松纹草丛|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_gatherable(target):
            caller.msg(f"{target.key} 看起来并不适合采集。")
            return
        result = gather_from_object(caller, target)
        if not result["ok"]:
            caller.msg(result["text"])
            return
        caller.msg(
            f"{result['text']}\n"
            f"|g采集收获|n: 获得 |w{result['item'].key}|n，体力 -{result['cost']}\n"
            f"|g当前体力|n: {result['stamina_now']}/{result['max_stamina']}"
        )


class CmdTrigger(Command):
    key = "触发"
    aliases = ["trigger", "激活", "touch"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想触发什么？用法：|w触发 回渡石|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_teleportable(target):
            caller.msg(f"{target.key} 看起来并不会回应你的触碰。")
            return
        result = teleport_via_object(caller, target)
        if not result["ok"]:
            caller.msg(result["text"])
            return
        caller.msg(result["text"])
