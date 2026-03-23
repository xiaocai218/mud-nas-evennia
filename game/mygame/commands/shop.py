"""Shop commands."""

from evennia.utils import evtable

from .command import Command
from systems.shops import buy_item, list_shop_goods


class CmdShop(Command):
    key = "商店"
    aliases = ["shop", "store"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        shop = list_shop_goods(caller)
        if not shop:
            caller.msg("这里没有正在营业的商店。")
            return

        table = evtable.EvTable("物品", "价格", "说明", border="cells", pad_width=1)
        for entry in shop["inventory"]:
            table.add_row(entry["key"], f"{entry['price']} {shop['currency']}", entry["desc"])
        caller.msg(f"|g{shop['key']}|n\n{shop['desc']}\n\n{table}")


class CmdBuy(Command):
    key = "购买"
    aliases = ["buy"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要购买什么？用法：|w购买 松纹草|n")
            return

        result = buy_item(caller, self.args.strip())
        if not result["ok"]:
            if result["reason"] == "no_shop":
                caller.msg("这里没有正在营业的商店。")
                return
            if result["reason"] == "not_found":
                caller.msg("这家店里没有你要买的东西。先用 |w商店|n 看看货架。")
                return
            if result["reason"] == "not_enough_money":
                caller.msg(
                    f"你的 {result['currency']} 不够。需要 {result['price']}，当前只有 {result['current']}。"
                )
                return

        caller.msg(
            f"你付出 {result['price']} {result['currency']}，从 {result['shop']['key']} 买下了 |w{result['item'].key}|n。\n"
            f"|g剩余铜钱|n: {result['remaining']}"
        )
