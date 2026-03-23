"""Inventory and item usage commands."""

from evennia.utils import evtable

from .command import Command
from systems.items import find_item, get_inventory_items
from systems.player_stats import apply_exp


class CmdInventory(Command):
    key = "背包"
    aliases = ["inventory", "inv", "bag"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        items = get_inventory_items(caller)
        if not items:
            caller.msg("你的背包里空空如也。")
            return
        table = evtable.EvTable("名称", "说明", border="cells", pad_width=1)
        for item in items:
            table.add_row(item.key, item.db.desc or "暂无说明")
        caller.msg("|g背包|n\n%s" % table)


class CmdRefine(Command):
    key = "炼化"
    aliases = ["refine", "absorb"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要炼化什么？用法：|w炼化 青木碎片|n")
            return
        item = find_item(caller, self.args.strip())
        if not item:
            caller.msg("你的背包里没有这个物品。")
            return
        if item.key != "青木碎片":
            caller.msg(f"{item.key} 现在还无法炼化。")
            return
        old_realm, new_realm, exp = apply_exp(caller, 10)
        item.delete()
        caller.msg(
            f"你将 青木碎片 捧在掌心，缓缓炼化其中残存的灵息。\n"
            f"|g炼化收获|n: 修为 +10\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}"
        )
        if new_realm != old_realm:
            caller.msg(f"|y借这一缕灵息之助，你的境界提升至 {new_realm}。|n")
