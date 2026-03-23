"""Inventory and item usage commands."""

from evennia.utils import evtable

from .command import Command
from systems.items import find_item, get_inventory_items
from systems.player_stats import apply_exp, get_stats


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
        exp_map = {"青木碎片": 10, "山纹石屑": 16}
        if item.key not in exp_map:
            caller.msg(f"{item.key} 现在还无法炼化。")
            return
        gain = exp_map[item.key]
        old_realm, new_realm, exp = apply_exp(caller, gain)
        item.delete()
        caller.msg(
            f"你将 {item.key} 捧在掌心，缓缓炼化其中残存的灵息。\n"
            f"|g炼化收获|n: 修为 +{gain}\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}"
        )
        if new_realm != old_realm:
            caller.msg(f"|y借这一缕灵息之助，你的境界提升至 {new_realm}。|n")


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

        if item.key == "渡口药包":
            stats = get_stats(caller)
            if stats["hp"] >= stats["max_hp"]:
                caller.msg("你现在气血充盈，暂时没必要拆开渡口药包。")
                return
            gain = 35
            caller.db.hp = min(stats["max_hp"], stats["hp"] + gain)
            recovered = caller.db.hp - stats["hp"]
            item.delete()
            caller.msg(
                "你拆开渡口药包，将其中草药简单敷用，只觉胸腹间的闷痛渐渐消退。\n"
                f"|g使用效果|n: 气血 +{recovered}，当前气血 {caller.db.hp}/{stats['max_hp']}"
            )
            return

        if item.key == "石阶护符":
            stats = get_stats(caller)
            if stats["stamina"] >= stats["max_stamina"]:
                caller.msg("你现在气息平稳，暂时不需要借助石阶护符。")
                return
            gain = 20
            caller.db.stamina = min(stats["max_stamina"], stats["stamina"] + gain)
            recovered = caller.db.stamina - stats["stamina"]
            item.delete()
            caller.msg(
                "你握住石阶护符，护符表面的凉意缓缓散开，紊乱的呼吸重新平顺下来。\n"
                f"|g使用效果|n: 体力 +{recovered}，当前体力 {caller.db.stamina}/{stats['max_stamina']}"
            )
            return

        if item.key == "雾露果":
            stats = get_stats(caller)
            if stats["hp"] >= stats["max_hp"] and stats["stamina"] >= stats["max_stamina"]:
                caller.msg("你现在状态正好，暂时不必服下雾露果。")
                return
            hp_gain = min(stats["max_hp"], stats["hp"] + 18) - stats["hp"]
            stamina_gain = min(stats["max_stamina"], stats["stamina"] + 12) - stats["stamina"]
            caller.db.hp = stats["hp"] + hp_gain
            caller.db.stamina = stats["stamina"] + stamina_gain
            item.delete()
            caller.msg(
                "你将雾露果咬开，清凉果汁顺着喉间滑下，胸腹与四肢都轻快了几分。\n"
                f"|g使用效果|n: 气血 +{hp_gain}，体力 +{stamina_gain}"
            )
            return

        caller.msg(f"{item.key} 现在还不能直接使用。")
