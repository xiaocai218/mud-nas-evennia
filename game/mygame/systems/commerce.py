"""Shared helpers for shop/market style systems."""


def get_facility_in_room(room, definitions, normalize=None):
    if not room:
        return None

    room_keys = {
        getattr(getattr(room, "db", None), "room_id", None),
        getattr(getattr(room, "db", None), "content_id", None),
    }
    room_keys.discard(None)
    if not room_keys:
        return None

    for facility_key, facility in definitions.items():
        if facility.get("room_id") not in room_keys:
            continue
        payload = {"facility_key": facility_key, **facility}
        return normalize(payload) if normalize else payload
    return None


def build_page_slice(entries, page=1, per_page=20):
    entries = list(entries or [])
    per_page = max(1, int(per_page or 1))
    total_count = len(entries)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "entries": entries[start:end],
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


def build_commerce_error(reason, **extra):
    payload = {
        "ok": False,
        "reason": reason,
        "error": {
            "code": reason,
        },
    }
    payload.update(extra)
    payload["error"].update({key: value for key, value in extra.items() if value is not None})
    return payload


def build_commerce_success(**payload):
    return {"ok": True, **payload}


def build_trade_or_listing_summary(
    *,
    entry_id=None,
    item_name=None,
    price=0,
    currency="铜钱",
    seller_name=None,
    buyer_name=None,
    sender_name=None,
    target_name=None,
    status=None,
    status_label=None,
    expires_in=None,
):
    return {
        "id": entry_id,
        "item_name": item_name,
        "price": int(price or 0),
        "currency": currency,
        "seller_name": seller_name,
        "buyer_name": buyer_name,
        "sender_name": sender_name,
        "target_name": target_name,
        "status": status,
        "status_label": status_label,
        "expires_in": expires_in,
    }
