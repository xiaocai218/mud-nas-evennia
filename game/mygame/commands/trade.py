"""Minimal player trade commands."""

from .command import Command
from systems.trade import (
    accept_trade_offer,
    cancel_trade_offer,
    create_trade_offer,
    list_trade_status,
    reject_trade_offer,
)


TRADE_ERROR_MESSAGES = {
    "target_not_found": "没有找到你要交易的玩家。",
    "target_is_self": "不能和自己交易。",
    "target_not_nearby": "交易双方需要站在同一个房间内。",
    "item_not_found": "你背包里没有这个物品。",
    "invalid_price": "交易价格必须是 0 或正整数。",
    "offer_not_found": "没有找到可处理的交易邀约。",
    "offer_expired": "当前没有有效交易邀约，旧邀约可能已经过期。",
    "sender_not_found": "发起交易的玩家当前不可用。",
    "item_unavailable": "该交易物品已经不可用，可能已被使用、丢弃或交易走。",
    "not_enough_money": "你的铜钱不足，无法接受这笔交易。",
}


def _render_trade_error(caller, result):
    if result.get("reason") == "not_enough_money":
        caller.msg(
            f"你的 {result['currency']} 不够。需要 {result['price']}，当前只有 {result['current']}。"
        )
        return
    caller.msg(TRADE_ERROR_MESSAGES.get(result.get("reason"), "交易操作失败。"))


def _format_offers(title, offers):
    if not offers:
        return f"{title}：无"
    rows = [f"{title}："]
    for offer in offers:
        ttl_minutes = max(1, offer["expires_in"] // 60) if offer["expires_in"] else 0
        price_text = f" / {offer['price']} {offer['currency']}" if offer["price"] else " / 免费"
        rows.append(
            f"- {offer['sender_name']} -> {offer['target_name']} / {offer['item_name']}{price_text}"
            f" / 约剩 {ttl_minutes} 分钟"
        )
    return "\n".join(rows)


def _send_trade_action_or_error(caller, action, *args):
    result = action(caller, *args)
    if not result["ok"]:
        _render_trade_error(caller, result)
    return result


class CmdTrade(Command):
    key = "交易"
    aliases = ["trade"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        raw = self.args.strip()
        if not raw:
            result = list_trade_status(self.caller)
            extra = ""
            if result.get("expired_offers_count"):
                extra = f"\n已自动清理过期交易邀约 {result['expired_offers_count']} 条。"
            self.caller.msg(
                _format_offers("收到的交易", result["incoming"])
                + "\n"
                + _format_offers("发出的交易", result["outgoing"])
                + extra
                + "\n\n用法：交易 玩家名 物品名 [价格]"
            )
            return

        parts = raw.split()
        if len(parts) < 2:
            self.caller.msg("用法：交易 玩家名 物品名 [价格]")
            return

        price = 0
        if parts[-1].isdigit():
            price = int(parts[-1])
            parts = parts[:-1]
        if len(parts) < 2:
            self.caller.msg("用法：交易 玩家名 物品名 [价格]")
            return

        target_name = parts[0]
        item_name = " ".join(parts[1:])
        _send_trade_action_or_error(self.caller, create_trade_offer, target_name, item_name, price)


class CmdAcceptTrade(Command):
    key = "接受交易"
    aliases = ["accepttrade"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_trade_action_or_error(self.caller, accept_trade_offer, self.args.strip() or None)


class CmdRejectTrade(Command):
    key = "拒绝交易"
    aliases = ["rejecttrade"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_trade_action_or_error(self.caller, reject_trade_offer, self.args.strip() or None)


class CmdCancelTrade(Command):
    key = "取消交易"
    aliases = ["canceltrade"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_trade_action_or_error(self.caller, cancel_trade_offer, self.args.strip() or None)
