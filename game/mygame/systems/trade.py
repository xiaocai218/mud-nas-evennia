"""玩家间最小交易邀约系统。

负责内容：
- 维护文本 MUD 内的单物品交易邀约、接受、拒绝、取消和过期清理。
- 使用 ServerConfig 保存挂起 offer，并在成交时完成货币结算与物品转移。
- 为命令层和 H5 提供统一的交易状态与摘要结构。

不负责内容：
- 不实现多物品、多阶段确认、担保、拍卖或跨房间交易。
- 不托管物品；交易挂起期间物品仍留在发起方身上，成交时再校验是否仍可用。

主要输入 / 输出：
- 输入：玩家对象、目标名、物品名、价格。
- 输出：统一 commerce success/error 结构和 offer 摘要。

上游调用者：
- `commands/trade.py`
- `action_router.py`
- `serializers.py`

排错优先入口：
- `list_trade_status`
- `create_trade_offer`
- `accept_trade_offer`
- `reject_trade_offer`
- `cancel_trade_offer`
- `_load_active_offers`
"""

from __future__ import annotations

import time
from typing import Dict, List

import evennia
from evennia.server.models import ServerConfig

from .chat import notify_player
from .commerce import build_commerce_error, build_commerce_success, build_trade_or_listing_summary
from .items import find_item
from .player_stats import add_currency, get_currency, spend_currency


TRADE_REGISTRY_KEY = "prototype_trade_offers"
TRADE_TTL_SECONDS = 1800
TRADE_CURRENCY_LABEL = "铜钱"


def list_trade_status(caller):
    active_offers, expired_count = _load_active_offers()
    caller_id = _get_character_id(caller)
    incoming = [_serialize_offer(offer) for offer in active_offers if offer["target_id"] == caller_id]
    outgoing = [_serialize_offer(offer) for offer in active_offers if offer["sender_id"] == caller_id]
    return build_commerce_success(
        incoming=incoming,
        outgoing=outgoing,
        expired_offers_count=expired_count,
    )


def create_trade_offer(caller, target_name, item_name, price=0):
    target = _find_target_character(target_name)
    if not target:
        return build_commerce_error("target_not_found", target_name=target_name)
    if target == caller:
        return build_commerce_error("target_is_self")
    if getattr(caller, "location", None) is None or target.location != caller.location:
        return build_commerce_error("target_not_nearby", target_name=target.key)

    item = find_item(caller, item_name=item_name)
    if not item:
        return build_commerce_error("item_not_found", item_name=item_name)

    price = int(price or 0)
    if price < 0:
        return build_commerce_error("invalid_price", price=price)

    active_offers, _ = _load_active_offers()
    if any(
        offer["sender_id"] == _get_character_id(caller) and offer["item_object_id"] == _get_object_id(item)
        for offer in active_offers
    ):
        # 同一个 live item 只允许挂一条待处理交易。
        # 否则 A、B 两个人都可能看到自己能接受同一件物品，最终成交顺序会变得不可预测。
        return build_commerce_error("item_already_offered", item_name=item.key)

    offer = {
        "id": _build_offer_id(caller),
        "sender_id": _get_character_id(caller),
        "sender_name": caller.key,
        "target_id": _get_character_id(target),
        "target_name": target.key,
        "item_object_id": _get_object_id(item),
        "item_name": item.key,
        "price": price,
        "currency": TRADE_CURRENCY_LABEL,
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + TRADE_TTL_SECONDS,
    }
    active_offers.append(offer)
    _save_registry({entry["id"]: entry for entry in active_offers})

    if price:
        target_message = (
            f"{caller.key} 向你发起交易：|w{item.key}|n，价格 {price} {TRADE_CURRENCY_LABEL}。"
            f" 可输入 接受交易 {caller.key}。"
        )
    else:
        target_message = f"{caller.key} 向你发起交易：|w{item.key}|n。可输入 接受交易 {caller.key}。"

    notify_player(
        caller,
        f"已向 {target.key} 发起交易：{item.key}" + (f"（{price} {TRADE_CURRENCY_LABEL}）" if price else "") + "。",
        code="trade_offer_created",
    )
    notify_player(target, target_message, code="trade_offer_received")
    return build_commerce_success(offer=_serialize_offer(offer), target=target.key, summary=_serialize_offer(offer))


def accept_trade_offer(caller, sender_name=None):
    active_offers, expired_count = _load_active_offers()
    incoming = [offer for offer in active_offers if offer["target_id"] == _get_character_id(caller)]
    if not incoming:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return build_commerce_error(reason)

    offer = _select_offer(incoming, sender_name)
    if not offer:
        return build_commerce_error("offer_not_found", sender_name=sender_name)

    sender = _get_character_by_id(offer["sender_id"])
    if not sender:
        # 发起方已不存在时，顺手清掉悬空 offer，避免目标玩家反复看到一条永远无法完成的邀约。
        _remove_offer(offer["id"], active_offers)
        return build_commerce_error("sender_not_found", sender_name=offer["sender_name"])
    if getattr(sender, "location", None) != getattr(caller, "location", None):
        return build_commerce_error("target_not_nearby", target_name=offer["sender_name"])

    item = _get_object_by_id(offer["item_object_id"])
    if not item or getattr(item, "location", None) != sender:
        # 交易期间物品并未托管，发起方可能已使用、丢弃或转移该物品。
        # 这里必须在成交前做最终校验，否则会出现扣了钱但没有物品的严重脏状态。
        _remove_offer(offer["id"], active_offers)
        return build_commerce_error("item_unavailable", item_name=offer["item_name"])

    if offer["price"]:
        success, current = spend_currency(caller, offer["price"])
        if not success:
            return build_commerce_error(
                "not_enough_money",
                price=offer["price"],
                currency=offer["currency"],
                current=current,
            )
        sender_balance = add_currency(sender, offer["price"])
    else:
        sender_balance = get_currency(sender)

    _move_item_to_owner(item, caller)
    _remove_offer(offer["id"], active_offers)

    notify_player(
        caller,
        f"你接受了来自 {offer['sender_name']} 的交易，获得 {offer['item_name']}。"
        + (f" 支付 {offer['price']} {offer['currency']}。" if offer["price"] else ""),
        code="trade_offer_accepted",
    )
    notify_player(
        sender,
        f"{caller.key} 接受了你的交易：{offer['item_name']}。"
        + (f" 你获得 {offer['price']} {offer['currency']}，当前铜钱 {sender_balance}。" if offer["price"] else ""),
        code="trade_offer_completed",
    )
    return build_commerce_success(offer=_serialize_offer(offer), item=item, summary=_serialize_offer(offer))


def reject_trade_offer(caller, sender_name=None):
    active_offers, expired_count = _load_active_offers()
    incoming = [offer for offer in active_offers if offer["target_id"] == _get_character_id(caller)]
    if not incoming:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return build_commerce_error(reason)

    offer = _select_offer(incoming, sender_name)
    if not offer:
        return build_commerce_error("offer_not_found", sender_name=sender_name)

    _remove_offer(offer["id"], active_offers)
    notify_player(
        caller,
        f"你已拒绝来自 {offer['sender_name']} 的交易：{offer['item_name']}。",
        code="trade_offer_rejected",
    )
    sender = _get_character_by_id(offer["sender_id"])
    if sender:
        notify_player(
            sender,
            f"{caller.key} 拒绝了你的交易：{offer['item_name']}。",
            code="trade_offer_declined",
        )
    return build_commerce_success(offer=_serialize_offer(offer), summary=_serialize_offer(offer))


def cancel_trade_offer(caller, target_name=None):
    active_offers, expired_count = _load_active_offers()
    outgoing = [offer for offer in active_offers if offer["sender_id"] == _get_character_id(caller)]
    if not outgoing:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return build_commerce_error(reason)

    offer = _select_offer(outgoing, target_name, target_field="target_name")
    if not offer:
        return build_commerce_error("offer_not_found", target_name=target_name)

    _remove_offer(offer["id"], active_offers)
    notify_player(
        caller,
        f"你已取消发给 {offer['target_name']} 的交易：{offer['item_name']}。",
        code="trade_offer_canceled",
    )
    target = _get_character_by_id(offer["target_id"])
    if target:
        notify_player(
            target,
            f"{caller.key} 取消了发给你的交易：{offer['item_name']}。",
            code="trade_offer_withdrawn",
        )
    return build_commerce_success(offer=_serialize_offer(offer), summary=_serialize_offer(offer))


def _load_registry() -> Dict[str, dict]:
    return ServerConfig.objects.conf(TRADE_REGISTRY_KEY, default=dict) or {}


def _save_registry(registry):
    ServerConfig.objects.conf(TRADE_REGISTRY_KEY, value=registry)


def _load_active_offers():
    registry = _load_registry()
    offers = list(registry.values())
    now = int(time.time())
    active = [offer for offer in offers if offer.get("expires_at", 0) > now]
    expired_count = len(offers) - len(active)
    # 读取时就做过期清理，确保“状态面板”和“接受/拒绝”共用同一批有效 offers。
    if expired_count:
        _save_registry({offer["id"]: offer for offer in active})
    return active, expired_count


def _remove_offer(offer_id, active_offers):
    remaining = [offer for offer in active_offers if offer["id"] != offer_id]
    _save_registry({offer["id"]: offer for offer in remaining})


def _serialize_offer(offer):
    expires_in = max(0, int(offer.get("expires_at", 0)) - int(time.time()))
    return build_trade_or_listing_summary(
        entry_id=offer["id"],
        sender_name=offer["sender_name"],
        target_name=offer["target_name"],
        item_name=offer["item_name"],
        price=offer["price"],
        currency=offer["currency"],
        status="pending",
        status_label="待处理",
        expires_in=expires_in,
    )


def _select_offer(offers, name=None, target_field="sender_name"):
    if not name:
        return sorted(offers, key=lambda offer: offer.get("created_at", 0), reverse=True)[0]
    normalized = name.strip().lower()
    for offer in sorted(offers, key=lambda offer: offer.get("created_at", 0), reverse=True):
        if offer.get(target_field, "").lower() == normalized:
            return offer
    return None


def _build_offer_id(caller):
    return f"trade_{int(time.time() * 1000)}_{_get_character_id(caller)}"


def _find_target_character(target_name):
    matches = evennia.search_object(target_name)
    if matches:
        return matches[0]
    matches = evennia.search_account(target_name)
    if matches:
        return getattr(matches[0].db, "_last_puppet", None)
    return None


def _get_character_id(caller):
    return getattr(caller, "id", None) or getattr(caller, "pk", None)


def _get_character_by_id(character_id):
    matches = evennia.search_object(f"#{character_id}")
    return matches[0] if matches else None


def _get_object_by_id(object_id):
    matches = evennia.search_object(f"#{object_id}")
    return matches[0] if matches else None


def _get_object_id(obj):
    return getattr(obj, "id", None) or getattr(obj, "dbid", None) or getattr(obj, "pk", None)


def _move_item_to_owner(item, owner):
    if hasattr(item, "move_to"):
        item.move_to(owner, quiet=True, move_type="trade")
        return
    item.location = owner
