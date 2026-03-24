"""Minimal player-to-player trade offers for text gameplay."""

from __future__ import annotations

import time
from typing import Dict, List

import evennia
from evennia.server.models import ServerConfig

from .chat import notify_player
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
    return {
        "ok": True,
        "incoming": incoming,
        "outgoing": outgoing,
        "expired_offers_count": expired_count,
    }


def create_trade_offer(caller, target_name, item_name, price=0):
    target = _find_target_character(target_name)
    if not target:
        return {"ok": False, "reason": "target_not_found"}
    if target == caller:
        return {"ok": False, "reason": "target_is_self"}
    if getattr(caller, "location", None) is None or target.location != caller.location:
        return {"ok": False, "reason": "target_not_nearby"}

    item = find_item(caller, item_name=item_name)
    if not item:
        return {"ok": False, "reason": "item_not_found"}

    price = int(price or 0)
    if price < 0:
        return {"ok": False, "reason": "invalid_price"}

    active_offers, _ = _load_active_offers()
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
    return {"ok": True, "offer": offer, "target": target.key}


def accept_trade_offer(caller, sender_name=None):
    active_offers, expired_count = _load_active_offers()
    incoming = [offer for offer in active_offers if offer["target_id"] == _get_character_id(caller)]
    if not incoming:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return {"ok": False, "reason": reason}

    offer = _select_offer(incoming, sender_name)
    if not offer:
        return {"ok": False, "reason": "offer_not_found"}

    sender = _get_character_by_id(offer["sender_id"])
    if not sender:
        _remove_offer(offer["id"], active_offers)
        return {"ok": False, "reason": "sender_not_found"}
    if getattr(sender, "location", None) != getattr(caller, "location", None):
        return {"ok": False, "reason": "target_not_nearby"}

    item = _get_object_by_id(offer["item_object_id"])
    if not item or getattr(item, "location", None) != sender:
        _remove_offer(offer["id"], active_offers)
        return {"ok": False, "reason": "item_unavailable"}

    if offer["price"]:
        success, current = spend_currency(caller, offer["price"])
        if not success:
            return {
                "ok": False,
                "reason": "not_enough_money",
                "price": offer["price"],
                "currency": offer["currency"],
                "current": current,
            }
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
    return {"ok": True, "offer": offer, "item": item}


def reject_trade_offer(caller, sender_name=None):
    active_offers, expired_count = _load_active_offers()
    incoming = [offer for offer in active_offers if offer["target_id"] == _get_character_id(caller)]
    if not incoming:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return {"ok": False, "reason": reason}

    offer = _select_offer(incoming, sender_name)
    if not offer:
        return {"ok": False, "reason": "offer_not_found"}

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
    return {"ok": True, "offer": offer}


def cancel_trade_offer(caller, target_name=None):
    active_offers, expired_count = _load_active_offers()
    outgoing = [offer for offer in active_offers if offer["sender_id"] == _get_character_id(caller)]
    if not outgoing:
        reason = "offer_expired" if expired_count else "offer_not_found"
        return {"ok": False, "reason": reason}

    offer = _select_offer(outgoing, target_name, target_field="target_name")
    if not offer:
        return {"ok": False, "reason": "offer_not_found"}

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
    return {"ok": True, "offer": offer}


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
    if expired_count:
        _save_registry({offer["id"]: offer for offer in active})
    return active, expired_count


def _remove_offer(offer_id, active_offers):
    remaining = [offer for offer in active_offers if offer["id"] != offer_id]
    _save_registry({offer["id"]: offer for offer in remaining})


def _serialize_offer(offer):
    expires_in = max(0, int(offer.get("expires_at", 0)) - int(time.time()))
    return {
        "id": offer["id"],
        "sender_name": offer["sender_name"],
        "target_name": offer["target_name"],
        "item_name": offer["item_name"],
        "price": offer["price"],
        "currency": offer["currency"],
        "expires_in": expires_in,
    }


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
