"""玩家寄售坊市系统。

负责内容：
- 管理坊市挂牌、购买、下架 / 取回、收益待领取和过期状态。
- 维护 ServerConfig 中的寄售 registry，并把 live item 暂时托管出玩家背包。
- 为命令层和 H5 提供统一的坊市列表、个人状态和结算结果。

不负责内容：
- 不负责房间设施发现规则；坊市是否存在于当前房间由 `commerce.py` 处理。
- 不做拍卖、议价、批量挂牌或复杂订单撮合。

主要输入 / 输出：
- 输入：玩家对象、挂牌 id、物品名、价格、页码、关键字。
- 输出：统一 commerce success/error 结构和 listing 摘要。

上游调用者：
- `commands/market.py`
- `serializers.py`
- `action_router.py`

排错优先入口：
- `list_market_goods`
- `list_my_market_status`
- `create_market_listing`
- `buy_market_listing`
- `cancel_market_listing`
- `claim_market_earnings`
"""

from __future__ import annotations

import time

import evennia
from evennia.server.models import ServerConfig

from .chat import notify_player
from .commerce import (
    build_commerce_error,
    build_commerce_success,
    build_page_slice,
    build_trade_or_listing_summary,
    get_facility_in_room,
)
from .content_loader import load_content
from .items import find_item
from .player_stats import add_currency, spend_currency


MARKET_DEFINITIONS = load_content("markets")
MARKET_REGISTRY_KEY = "prototype_market_state"
MARKET_DEFAULT_TTL_SECONDS = 86400
MARKET_DEFAULT_VISIBLE_LISTINGS = 20


def get_market_by_id(market_id):
    for market in MARKET_DEFINITIONS.values():
        if market.get("id") == market_id:
            return _normalize_market(market)
    return None


def get_market_in_room(room):
    return get_facility_in_room(room, MARKET_DEFINITIONS, normalize=_normalize_market)


def list_market_goods(caller, page=1, keyword=None):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    state = _load_state()
    _expire_listings(state)
    page = max(1, int(page or 1))
    keyword = (keyword or "").strip().lower()
    active_listings = [
        listing
        for listing in _sorted_listings(state)
        if listing["market_id"] == market["id"]
        and listing["status"] == "active"
        and (not keyword or keyword in listing["item_name"].lower() or keyword in listing["seller_name"].lower())
    ]
    per_page = market["visible_listings"]
    paging = build_page_slice(active_listings, page=page, per_page=per_page)
    listings = [_serialize_listing(listing) for listing in paging["entries"]]
    pending = int(state.get("pending_earnings", {}).get(str(_get_character_id(caller)), 0))
    return build_commerce_success(
        market=market,
        listings=listings,
        pending_earnings=pending,
        page=paging["page"],
        per_page=paging["per_page"],
        total_count=paging["total_count"],
        total_pages=paging["total_pages"],
        keyword=keyword,
    )


def list_my_market_status(caller):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    state = _load_state()
    _expire_listings(state)
    seller_id = _get_character_id(caller)
    mine = [listing for listing in _sorted_listings(state) if listing["seller_id"] == seller_id]
    return build_commerce_success(
        market=market,
        active=[_serialize_listing(listing) for listing in mine if listing["status"] == "active"],
        sold=[_serialize_listing(listing) for listing in mine if listing["status"] == "sold"],
        reclaimable=[
            _serialize_listing(listing)
            for listing in mine
            if listing["status"] == "expired" and not listing.get("reclaimed_at")
        ],
        pending_earnings=int(state.get("pending_earnings", {}).get(str(seller_id), 0)),
        summary={
            "active_count": sum(1 for listing in mine if listing["status"] == "active"),
            "sold_count": sum(1 for listing in mine if listing["status"] == "sold"),
            "reclaimable_count": sum(
                1 for listing in mine if listing["status"] == "expired" and not listing.get("reclaimed_at")
            ),
        },
    )


def create_market_listing(caller, item_name, price):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    item = find_item(caller, item_name=item_name)
    if not item:
        return build_commerce_error("item_not_found")

    price = int(price or 0)
    if price < 0:
        return build_commerce_error("invalid_price", price=price)

    state = _load_state()
    _expire_listings(state)
    item_id = _get_object_id(item)
    if any(
        listing["item_object_id"] == item_id and listing["status"] in {"active", "expired"}
        for listing in state["listings"].values()
    ):
        # expired 但未 reclaim 的物品仍视为“占用中的挂牌”。
        # 否则同一个 live item 会在 registry 里出现多条记录，后续取回 / 售出时很难判断归属。
        return build_commerce_error("item_already_listed", item_name=item.key)

    listing_id = _next_listing_id(state)
    listing = {
        "id": listing_id,
        "market_id": market["id"],
        "seller_id": _get_character_id(caller),
        "seller_name": caller.key,
        "item_object_id": item_id,
        "item_name": item.key,
        "price": price,
        "currency": market["currency"],
        "status": "active",
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + market["listing_ttl_seconds"],
    }
    _store_item(item, listing_id)
    state["listings"][listing_id] = listing
    _save_state(state)
    notify_player(
        caller,
        f"你已在 {market['key']} 挂牌 #{listing_id}：{item.key}（{price} {market['currency']}）。"
        f" 可用 下架 {listing_id} 取回。",
        code="market_listing_created",
    )
    serialized = _serialize_listing(listing)
    return build_commerce_success(listing=serialized, market=market, summary=serialized)


def buy_market_listing(caller, listing_id):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    state = _load_state()
    _expire_listings(state)
    listing = state["listings"].get(str(listing_id))
    if not listing or listing["market_id"] != market["id"]:
        return build_commerce_error("listing_not_found", listing_id=str(listing_id))
    if listing["status"] != "active":
        return build_commerce_error("listing_not_available", listing_id=str(listing_id), status=listing["status"])
    if listing["seller_id"] == _get_character_id(caller):
        return build_commerce_error("cannot_buy_own_listing", listing_id=str(listing_id))

    success, current = spend_currency(caller, listing["price"])
    if not success:
        return build_commerce_error(
            "not_enough_money",
            listing_id=str(listing_id),
            price=listing["price"],
            currency=listing["currency"],
            current=current,
        )

    item = _get_object_by_id(listing["item_object_id"])
    if not item:
        # registry 里有挂牌，但物品实体已丢失时，直接把挂牌降级为 canceled。
        # 继续保留 active 只会让玩家反复点到一个永远买不到的脏 listing。
        listing["status"] = "canceled"
        listing["updated_at"] = int(time.time())
        _save_state(state)
        return build_commerce_error("item_unavailable", listing_id=str(listing_id))

    _release_item(item, caller)
    listing["status"] = "sold"
    listing["buyer_id"] = _get_character_id(caller)
    listing["buyer_name"] = caller.key
    listing["sold_at"] = int(time.time())
    # 收益先进入 pending_earnings，而不是直接打给卖家。
    # 这样卖家离线时也不会丢账，并且能保持“领取坊市”这条显式反馈链路。
    state["pending_earnings"][str(listing["seller_id"])] = (
        int(state["pending_earnings"].get(str(listing["seller_id"]), 0)) + int(listing["price"])
    )
    _save_state(state)

    notify_player(
        caller,
        f"你在 {market['key']} 买下了 {listing['item_name']}，花费 {listing['price']} {listing['currency']}。",
        code="market_listing_bought",
    )
    seller = _get_character_by_id(listing["seller_id"])
    if seller:
        notify_player(
            seller,
            f"{caller.key} 购买了你在 {market['key']} 挂牌的 {listing['item_name']}，收益可用 领取坊市 取出。",
            code="market_listing_sold",
        )
    serialized = _serialize_listing(listing)
    return build_commerce_success(listing=serialized, item=item, market=market, summary=serialized)


def cancel_market_listing(caller, listing_id):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    state = _load_state()
    _expire_listings(state)
    listing = state["listings"].get(str(listing_id))
    if not listing or listing["market_id"] != market["id"]:
        return build_commerce_error("listing_not_found", listing_id=str(listing_id))
    if listing["seller_id"] != _get_character_id(caller):
        return build_commerce_error("not_listing_owner", listing_id=str(listing_id))
    if listing["status"] == "sold":
        return build_commerce_error("listing_already_sold", listing_id=str(listing_id))
    if listing["status"] == "canceled":
        return build_commerce_error("listing_not_available", listing_id=str(listing_id), status=listing["status"])

    item = _get_object_by_id(listing["item_object_id"])
    if not item:
        listing["status"] = "canceled"
        listing["updated_at"] = int(time.time())
        _save_state(state)
        return build_commerce_error("item_unavailable", listing_id=str(listing_id))

    _release_item(item, caller)
    was_active = listing["status"] == "active"
    if was_active:
        listing["status"] = "canceled"
        listing["canceled_at"] = int(time.time())
    else:
        listing["reclaimed_at"] = int(time.time())
    _save_state(state)
    # 这里根据取消前状态决定提示文案，而不是根据写回后的 status。
    # expired 物品取回后本身仍保留 expired 状态，只是多了 reclaimed_at，方便区分“已过期且已处理”。
    verb = "下架" if was_active else "取回"
    notify_player(
        caller,
        f"你已从 {market['key']}{verb} {listing['item_name']}。",
        code="market_listing_canceled",
    )
    serialized = _serialize_listing(listing)
    return build_commerce_success(listing=serialized, market=market, summary=serialized)


def claim_market_earnings(caller):
    market = get_market_in_room(getattr(caller, "location", None))
    if not market:
        return build_commerce_error("market_not_available")

    state = _load_state()
    seller_key = str(_get_character_id(caller))
    amount = int(state["pending_earnings"].get(seller_key, 0))
    if amount <= 0:
        return build_commerce_error("no_pending_earnings")

    current = add_currency(caller, amount)
    state["pending_earnings"][seller_key] = 0
    _save_state(state)
    notify_player(
        caller,
        f"你从 {market['key']} 领取了 {amount} {market['currency']}，当前铜钱 {current}。",
        code="market_earnings_claimed",
    )
    return build_commerce_success(
        amount=amount,
        currency=market["currency"],
        current=current,
        market=market,
        remaining_pending=0,
        summary={
            "amount": amount,
            "currency": market["currency"],
            "current": current,
        },
    )


def _normalize_market(market):
    return {
        **market,
        "facility_key": market.get("facility_key") or market.get("market_key"),
        "visible_listings": int(market.get("visible_listings", MARKET_DEFAULT_VISIBLE_LISTINGS)),
        "listing_ttl_seconds": int(market.get("listing_ttl_seconds", MARKET_DEFAULT_TTL_SECONDS)),
        "currency": market.get("currency", "铜钱"),
    }


def _load_state():
    state = ServerConfig.objects.conf(MARKET_REGISTRY_KEY, default=dict) or {}
    return {
        "counter": int(state.get("counter", 0)),
        "listings": dict(state.get("listings", {})),
        "pending_earnings": {str(key): int(value) for key, value in dict(state.get("pending_earnings", {})).items()},
    }


def _save_state(state):
    ServerConfig.objects.conf(
        MARKET_REGISTRY_KEY,
        value={
            "counter": int(state.get("counter", 0)),
            "listings": dict(state.get("listings", {})),
            "pending_earnings": dict(state.get("pending_earnings", {})),
        },
    )


def _next_listing_id(state):
    state["counter"] = int(state.get("counter", 0)) + 1
    return str(state["counter"])


def _expire_listings(state):
    now = int(time.time())
    changed = False
    for listing in state["listings"].values():
        if listing["status"] == "active" and listing.get("expires_at", 0) <= now:
            # 过期不会自动把物品塞回背包，只是转成 reclaimable。
            # 这样可以避免玩家离线或背包状态复杂时发生隐式移动。
            listing["status"] = "expired"
            listing["expired_at"] = now
            changed = True
    if changed:
        _save_state(state)


def _sorted_listings(state):
    return sorted(state["listings"].values(), key=lambda listing: listing.get("created_at", 0), reverse=True)


def _serialize_listing(listing):
    expires_in = 0
    if listing["status"] == "active":
        expires_in = max(0, int(listing.get("expires_at", 0)) - int(time.time()))
    return {
        **build_trade_or_listing_summary(
            entry_id=listing["id"],
            item_name=listing["item_name"],
            price=listing["price"],
            currency=listing["currency"],
            seller_name=listing["seller_name"],
            buyer_name=listing.get("buyer_name"),
            status=listing["status"],
            status_label=_get_status_label(listing["status"]),
            expires_in=expires_in,
        ),
        "market_id": listing["market_id"],
        "created_at": listing.get("created_at"),
    }


def _get_status_label(status):
    return {
        "active": "在售",
        "sold": "已售",
        "expired": "可取回",
        "canceled": "已下架",
    }.get(status, status)


def _store_item(item, listing_id):
    if hasattr(item, "db"):
        item.db.market_listing_id = listing_id
    # 挂牌时先把物品脱离玩家 location，视为进入坊市托管。
    # 后续一切售出 / 取回都以 registry 和 market_listing_id 为准，不再依赖背包遍历。
    item.location = None
    if hasattr(item, "save"):
        item.save()


def _release_item(item, owner):
    if hasattr(item, "db"):
        item.db.market_listing_id = None
    if hasattr(item, "move_to"):
        item.move_to(owner, quiet=True, move_type="market")
        return
    item.location = owner
    if hasattr(item, "save"):
        item.save()


def _get_character_id(caller):
    return getattr(caller, "id", None) or getattr(caller, "pk", None)


def _get_object_id(obj):
    return getattr(obj, "id", None) or getattr(obj, "dbid", None) or getattr(obj, "pk", None)


def _get_character_by_id(character_id):
    matches = evennia.search_object(f"#{character_id}")
    return matches[0] if matches else None


def _get_object_by_id(object_id):
    matches = evennia.search_object(f"#{object_id}")
    return matches[0] if matches else None
