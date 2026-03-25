"""Player market commands."""

from evennia.utils import evtable

from .command import Command
from systems.market import (
    buy_market_listing,
    cancel_market_listing,
    claim_market_earnings,
    create_market_listing,
    list_market_goods,
    list_my_market_status,
)


MARKET_ERROR_MESSAGES = {
    "market_not_available": "这里只有在坊市里才能操作寄售。请前往指定坊市地点。",
    "item_not_found": "你的背包里没有这个物品。",
    "item_already_listed": "这件物品已经在坊市挂牌，不能重复上架。",
    "invalid_price": "挂牌价格必须是 0 或正整数。",
    "listing_not_found": "没有找到对应的坊市挂牌。",
    "listing_not_available": "这条坊市挂牌当前无法购买或操作。",
    "cannot_buy_own_listing": "不能购买自己挂出的物品。",
    "not_listing_owner": "这不是你挂出的坊市商品。",
    "listing_already_sold": "这条坊市挂牌已经售出，不能再下架。",
    "item_unavailable": "这条坊市挂牌对应的物品已经不可用。",
    "not_enough_money": "你的铜钱不足，无法买下这条坊市挂牌。",
    "no_pending_earnings": "你当前没有可领取的坊市收益。",
}


MARKET_USAGE_TEXT = (
    "可用命令：坊市 [页码] [关键词]、上架 <物品> <价格>、购买坊市 <挂牌编号>、"
    "下架 <挂牌编号>、我的坊市、领取坊市"
)


def _render_market_error(caller, result):
    if result.get("reason") == "not_enough_money":
        caller.msg(
            f"你的 {result['currency']} 不够。需要 {result['price']}，当前只有 {result['current']}。"
        )
        return
    caller.msg(MARKET_ERROR_MESSAGES.get(result.get("reason"), "坊市操作失败。"))


def _send_market_action_or_error(caller, action, *args):
    result = action(caller, *args)
    if not result["ok"]:
        _render_market_error(caller, result)
    return result


def _format_minutes(expires_in):
    if not expires_in:
        return "-"
    return f"{max(1, expires_in // 60)} 分钟"


def _build_market_table(listings):
    table = evtable.EvTable("编号", "物品", "价格", "卖家", "状态/剩余", border="cells", pad_width=1)
    if not listings:
        table.add_row("-", "暂无挂牌", "-", "-", "-")
        return table

    for listing in listings:
        tail = _format_minutes(listing["expires_in"]) if listing["status"] == "active" else listing["status_label"]
        table.add_row(
            f"#{listing['id']}",
            listing["item_name"],
            f"{listing['price']} {listing['currency']}",
            listing["seller_name"],
            tail,
        )
    return table


def _build_my_market_section(title, listings):
    if not listings:
        return f"{title}：无"
    return f"{title}：\n{_build_market_table(listings)}"


def _parse_market_query(raw):
    raw = (raw or "").strip()
    if not raw:
        return 1, None

    parts = raw.split(maxsplit=1)
    if parts[0].isdigit():
        page = max(1, int(parts[0]))
        keyword = parts[1].strip() if len(parts) > 1 else None
        return page, keyword or None
    return 1, raw


class CmdMarket(Command):
    key = "坊市"
    aliases = ["market"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        page, keyword = _parse_market_query(self.args)
        result = list_market_goods(self.caller, page=page, keyword=keyword)
        if not result["ok"]:
            _render_market_error(self.caller, result)
            return

        market = result["market"]
        table = _build_market_table(result["listings"])
        filter_text = f" / 筛选：{result['keyword']}" if result.get("keyword") else ""
        self.caller.msg(
            f"|g{market['key']}|n\n{market['desc']}\n\n{table}\n"
            f"|g页码|n: 第 {result['page']} / {result['total_pages']} 页，共 {result['total_count']} 条{filter_text}\n"
            f"|g待领取收益|n: {result['pending_earnings']} {market['currency']}\n"
            f"{MARKET_USAGE_TEXT}"
        )


class CmdListMyMarket(Command):
    key = "我的坊市"
    aliases = ["mymarket"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        result = list_my_market_status(self.caller)
        if not result["ok"]:
            _render_market_error(self.caller, result)
            return

        summary = result["summary"]
        rows = [
            f"当前坊市：{result['market']['key']}",
            (
                f"概览：在售 {summary['active_count']} 条 / 已售 {summary['sold_count']} 条 / "
                f"可取回 {summary['reclaimable_count']} 条"
            ),
            _build_my_market_section("在售", result["active"]),
            _build_my_market_section("已售", result["sold"]),
            _build_my_market_section("可取回", result["reclaimable"]),
            f"待领取收益：{result['pending_earnings']} {result['market']['currency']}",
            MARKET_USAGE_TEXT,
        ]
        self.caller.msg("\n".join(rows))


class CmdListMarketItem(Command):
    key = "上架"
    aliases = ["listmarket"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        raw = self.args.strip()
        if not raw:
            self.caller.msg("用法：上架 物品名 价格")
            return
        parts = raw.split()
        if len(parts) < 2:
            self.caller.msg("用法：上架 物品名 价格")
            return
        try:
            price = int(parts[-1])
        except ValueError:
            self.caller.msg("用法：上架 物品名 价格")
            return
        item_name = " ".join(parts[:-1])
        result = _send_market_action_or_error(self.caller, create_market_listing, item_name, price)
        if result.get("ok"):
            listing = result["listing"]
            self.caller.msg(
                f"挂牌成功：#{listing['id']} / {listing['item_name']} / {listing['price']} {listing['currency']}。"
            )


class CmdBuyMarketItem(Command):
    key = "购买坊市"
    aliases = ["buymarket"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        listing_id = self.args.strip().lstrip("#")
        if not listing_id:
            self.caller.msg("用法：购买坊市 挂牌编号")
            return
        result = _send_market_action_or_error(self.caller, buy_market_listing, listing_id)
        if result.get("ok"):
            listing = result["listing"]
            self.caller.msg(
                f"购买成功：#{listing['id']} / {listing['item_name']} / {listing['price']} {listing['currency']}。"
            )


class CmdCancelMarketListing(Command):
    key = "下架"
    aliases = ["cancelmarket"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        listing_id = self.args.strip().lstrip("#")
        if not listing_id:
            self.caller.msg("用法：下架 挂牌编号")
            return
        result = _send_market_action_or_error(self.caller, cancel_market_listing, listing_id)
        if result.get("ok"):
            listing = result["listing"]
            action = "取回" if listing["status"] == "expired" else "下架"
            self.caller.msg(f"{action}成功：#{listing['id']} / {listing['item_name']}。")


class CmdClaimMarketEarnings(Command):
    key = "领取坊市"
    aliases = ["claimmarket"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        result = _send_market_action_or_error(self.caller, claim_market_earnings)
        if result.get("ok"):
            self.caller.msg(
                f"领取完成：{result['amount']} {result['currency']}。当前铜钱 {result['current']}。"
            )
