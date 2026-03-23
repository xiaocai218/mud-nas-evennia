"""Inventory and item usage commands."""

from evennia.utils import evtable

from .command import Command
from systems.items import find_item, get_inventory_items, refine_item, use_item


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
        result = refine_item(caller, item)
        if not result["ok"]:
            caller.msg(f"{item.key} 现在还无法炼化。")
            return
        caller.msg(
            f"你将 {result['item_key']} 捧在掌心，缓缓炼化其中残存的灵息。\n"
            f"|g炼化收获|n: 修为 +{result['gain']}\n"
            f"|g当前状态|n: {result['new_realm']}，修为 {result['exp']}"
        )
        if result["new_realm"] != result["old_realm"]:
            caller.msg(f"|y借这一缕灵息之助，你的境界提升至 {result['new_realm']}。|n")


class CmdUseItem(Command):
    key = "使用"
    aliases = ["use", "服用"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要使用什么？用法：|w使用 渡口药包|n")
            return
        item = find_item(caller, self.args.strip())
        if not item:
            caller.msg("你的背包里没有这个物品。")
            return
        result = use_item(caller, item)
        if not result["ok"]:
            reason = result["reason"]
            if reason == "hp_full":
                caller.msg(f"你现在气血充盈，暂时没必要使用 {item.key}。")
                return
            if reason == "stamina_full":
                caller.msg(f"你现在气息平稳，暂时不需要借助 {item.key}。")
                return
            if reason == "all_full":
                caller.msg(f"你现在状态正好，暂时不必使用 {item.key}。")
                return
            caller.msg(f"{item.key} 现在还不能直接使用。")
            return

        if result["effect_type"] == "restore_hp":
            caller.msg(
                f"{result['text']}\n"
                f"|g使用效果|n: 气血 +{result['hp_gain']}，当前气血 {result['hp_now']}/{result['max_hp']}"
            )
            return

        if result["effect_type"] == "restore_stamina":
            caller.msg(
                f"{result['text']}\n"
                f"|g使用效果|n: 体力 +{result['stamina_gain']}，当前体力 {result['stamina_now']}/{result['max_stamina']}"
            )
            return

        if result["effect_type"] == "restore_both":
            caller.msg(
                f"{result['text']}\n"
                f"|g使用效果|n: 气血 +{result['hp_gain']}，体力 +{result['stamina_gain']}"
            )
            return
