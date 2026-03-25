"""Shop lookups and purchase helpers."""

from .chat import notify_player
from .commerce import build_commerce_error, build_commerce_success, get_facility_in_room
from .content_loader import load_content
from .items import create_reward_item, get_item_definition_by_id
from .player_stats import get_currency, spend_currency


SHOP_DEFINITIONS = load_content("shops")


def get_shop_by_id(shop_id):
    for shop in SHOP_DEFINITIONS.values():
        if shop.get("id") == shop_id:
            return shop
    return None


def get_shop_in_room(room):
    return get_facility_in_room(room, SHOP_DEFINITIONS, normalize=_normalize_shop)


def _normalize_shop(shop):
    entries = []
    for entry in shop.get("inventory", []):
        item_def = get_item_definition_by_id(entry["item_id"])
        if not item_def:
            continue
        entries.append(
            {
                "item_id": entry["item_id"],
                "key": item_def["key"],
                "desc": item_def.get("desc", ""),
                "price": int(entry.get("price", 0)),
            }
        )
    return {**shop, "inventory": entries}


def list_shop_goods(caller):
    shop = get_shop_in_room(caller.location)
    if not shop:
        return None
    return shop


def buy_item(caller, item_name):
    shop = get_shop_in_room(caller.location)
    if not shop:
        return build_commerce_error("no_shop")

    entry = next((entry for entry in shop["inventory"] if entry["key"] == item_name), None)
    if not entry:
        return build_commerce_error("not_found", shop=shop)

    success, remaining = spend_currency(caller, entry["price"])
    if not success:
        return build_commerce_error(
            "not_enough_money",
            price=entry["price"],
            current=remaining,
            currency=shop.get("currency", "铜钱"),
        )

    item = create_reward_item(caller, item_id=entry["item_id"])
    notify_player(
        caller,
        f"购买成功：{item.key}，花费 {entry['price']} {shop.get('currency', '铜钱')}。",
        code="shop_purchase",
    )
    return build_commerce_success(
        item=item,
        price=entry["price"],
        remaining=remaining,
        currency=shop.get("currency", "铜钱"),
        shop=shop,
        summary={
            "item_name": item.key,
            "price": entry["price"],
            "currency": shop.get("currency", "铜钱"),
            "remaining": remaining,
        },
    )
