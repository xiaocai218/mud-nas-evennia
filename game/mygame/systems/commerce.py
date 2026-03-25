"""商店 / 坊市 / 交易共用辅助层。

负责内容：
- 提供房间设施定位、分页切片、统一 success/error 包装和交易/挂牌摘要构造。
- 让 shop / market / trade 三条链路复用同一套基础返回外形。

不负责内容：
- 不保存任何业务状态。
- 不做货币、库存、所有权和结算规则判断。

主要输入 / 输出：
- 输入：房间对象、设施定义、分页参数、错误原因、交易/挂牌元数据。
- 输出：标准化设施 payload、分页结果、commerce success/error 结构。

上游调用者：
- `shops.py`
- `market.py`
- `trade.py`
- `serializers.py`

排错优先入口：
- `get_facility_in_room`
- `build_page_slice`
- `build_commerce_error`
- `build_trade_or_listing_summary`
"""


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
        # facility 统一返回 facility_key，便于上层同时拿到“原始配置键”和“规范化后的展示字段”。
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
    # 保持 error.code 与顶层 reason 双写，便于旧命令层和新 H5 层逐步共存。
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
    # trade 和 market 列表当前共用同一套摘要结构，便于前端列表组件模板化复用。
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
