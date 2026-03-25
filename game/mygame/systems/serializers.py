"""H5/API 结构化序列化层。

负责内容：
- 把 Evennia live object、系统状态和静态内容转换成稳定 DTO。
- 为 bootstrap、房间、人物详情、任务、战斗、聊天、商店、坊市等输出统一结构。
- 收口“终端对象模型 -> 客户端可消费 JSON”的映射，尽量避免 action handler 直接拼 payload。

不负责内容：
- 不做 action 分发和协议校验；这些分别在 `action_router.py` 与 `client_protocol.py`。
- 不实现业务规则；这里只读取系统层状态并做结构化表达。

主要输入 / 输出：
- 输入：角色、房间、账号、NPC、敌人、market/shop 定义等。
- 输出：适合 HTTP / WebSocket 返回的 dict / list DTO。

上游调用者：
- `action_router.py`
- `web/api/views.py`
- 未来 H5 bootstrap、详情面板、列表接口

排错优先入口：
- `build_bootstrap_payload`
- `serialize_room`
- `serialize_market`
- `serialize_quest_log`
- `serialize_battle_state`
"""

from systems.areas import get_area_for_room
from systems.battle import get_battle_snapshot, get_recent_combat_logs, list_available_cards, list_available_targets
from systems.chat_payloads import serialize_chat_message
from systems.chat import get_recent_chat_messages, list_channel_status
from systems.character_model import get_root_definition
from systems.content_loader import load_content
from systems.entity_gender import get_gender_label
from systems.enemy_model import get_enemy_definition, get_enemy_sheet, is_enemy
from systems.items import get_inventory_items
from systems.market import get_market_by_id, get_market_in_room, list_market_goods, list_my_market_status
from systems.npc_model import get_npc_definition, get_npc_sheet, is_npc
from systems.player_stats import get_active_effect_text, get_stats
from systems.quests import (
    COMPLETED,
    NOT_STARTED,
    get_active_side_quest_key,
    get_quest_state,
    get_started_side_quest_keys,
    get_side_quest_data,
    get_side_quest_state,
    get_stage_data,
)
from systems.shops import get_shop_by_id, get_shop_in_room
from systems.trade import list_trade_status
from systems.ui_preferences import get_ui_preferences


MAP_DEFINITIONS = load_content("maps")
ZONE_DEFINITIONS = load_content("zones")
AREA_DEFINITIONS = load_content("areas")
ROOM_DEFINITIONS = load_content("rooms").get("rooms", {})
NPC_DEFINITIONS = load_content("npcs").get("npcs", [])
OBJECT_DEFINITIONS = load_content("objects").get("objects", [])
ENEMY_DEFINITIONS = load_content("enemies")


def serialize_map(map_key):
    data = MAP_DEFINITIONS.get(map_key)
    if not data:
        return None
    return {
        "id": data.get("id", map_key),
        "key": data.get("key", map_key),
        "desc": data.get("desc", ""),
    }


def serialize_zone(zone_key):
    data = ZONE_DEFINITIONS.get(zone_key)
    if not data:
        return None
    return {
        "id": data.get("id", zone_key),
        "key": data.get("key", zone_key),
        "desc": data.get("desc", ""),
        "map_id": data.get("map_id"),
        "recommended_realm": data.get("recommended_realm"),
    }


def serialize_area(area_key):
    data = AREA_DEFINITIONS.get(area_key)
    if not data:
        return None
    return {
        "id": data.get("id", area_key),
        "key": data.get("key", area_key),
        "desc": data.get("desc", ""),
        "zone_id": data.get("zone_id"),
        "recommended_realm": data.get("recommended_realm"),
        "facilities": list(data.get("facilities", [])),
        "rooms": list(data.get("rooms", [])),
        "tags": list(data.get("tags", [])),
    }


def serialize_item(item):
    return {
        "id": getattr(item.db, "item_id", None),
        "key": item.key,
        "desc": item.db.desc or "",
    }


def serialize_inventory(caller):
    return [serialize_item(item) for item in get_inventory_items(caller)]


def serialize_character(caller):
    stats = get_stats(caller)
    root_definition = get_root_definition(stats["root"])
    return {
        "name": caller.key,
        "profile": getattr(caller.db, "character_profile", None),
        "stage": stats["stage"],
        "gender": stats.get("gender"),
        "gender_label": get_gender_label(stats.get("gender")),
        "root": stats["root"],
        "root_label": root_definition.get("label") if root_definition else None,
        "realm": stats["realm"],
        "hp": stats["hp"],
        "max_hp": stats["max_hp"],
        "mp": stats["mp"],
        "max_mp": stats["max_mp"],
        "stamina": stats["stamina"],
        "max_stamina": stats["max_stamina"],
        "exp": stats["exp"],
        "copper": stats["copper"],
        "spirit_stone": stats["spirit_stone"],
        "primary_currency": stats["primary_currency"],
        "currencies": stats["currencies"],
        "primary_stats": stats["primary_stats"],
        "combat_stats": stats["combat_stats"],
        "equipment": stats["equipment"],
        "affinities": stats["affinities"],
        "reserves": stats["reserves"],
        "effects_text": get_active_effect_text(caller),
        "inventory_count": len(get_inventory_items(caller)),
    }


def serialize_character_summary(character):
    stats = get_stats(character)
    return {
        "id": getattr(character, "pk", None),
        "key": character.key,
        "stage": stats["stage"],
        "gender": stats.get("gender"),
        "gender_label": get_gender_label(stats.get("gender")),
        "root": stats["root"],
        "realm": stats["realm"],
        "hp": stats["hp"],
        "max_hp": stats["max_hp"],
        "mp": stats["mp"],
        "max_mp": stats["max_mp"],
        "stamina": stats["stamina"],
        "max_stamina": stats["max_stamina"],
        "primary_currency": stats["primary_currency"],
        "area": serialize_world_position(character.location)["area"] if getattr(character, "location", None) else None,
        "room": serialize_room(character.location) if getattr(character, "location", None) else None,
    }


def serialize_account(account):
    return {
        "id": getattr(account, "pk", None),
        "username": getattr(account, "username", None),
        "is_authenticated": bool(getattr(account, "is_authenticated", False)),
    }


def serialize_room(room):
    if not room:
        return None

    room_id = getattr(room.db, "room_id", None)
    room_content_id = getattr(room.db, "content_id", None)
    area = get_area_for_room(room)
    area_key = None
    if area:
        # area helper 当前返回的是结构化 area 数据而不是原始 key。
        # 这里倒查 area_key，是为了让 DTO 同时保留“展示字段”和“可继续回查配置的 key”。
        for key, value in AREA_DEFINITIONS.items():
            if value.get("id") == area.get("id"):
                area_key = key
                break

    exits = []
    room_exits = getattr(room, "exits", None)
    if hasattr(room_exits, "items"):
        for exit_name, exit_obj in room_exits.items():
            exits.append(
                {
                    "key": exit_name,
                    "name": exit_obj.key,
                    "destination": getattr(exit_obj.destination, "key", None),
                }
            )
    elif room_exits:
        for exit_obj in room_exits:
            exits.append(
                {
                    "key": exit_obj.key,
                    "name": exit_obj.key,
                    "destination": getattr(exit_obj.destination, "key", None),
                }
            )

    return {
        "id": room_content_id or room_id,
        "room_key": room_id,
        "key": room.key,
        "desc": room.db.desc or "",
        "area_id": area.get("id") if area else None,
        "area_key": area_key,
        "exits": exits,
        "npcs": _serialize_room_npcs(room_id, room_content_id),
        "objects": _serialize_room_objects(room_id, room_content_id),
        "enemies": _serialize_room_enemies(room_id, room_content_id),
        "shop": serialize_shop_in_room(room),
        "market": serialize_market_in_room(room),
    }


def serialize_person_detail(target):
    if not target:
        return None

    if is_npc(target):
        return _serialize_npc_detail(target)
    if is_enemy(target):
        return _serialize_enemy_detail(target)
    if getattr(getattr(target, "db", None), "character_profile", None) is not None or (getattr(target.db, "identity", None) or {}).get("stage"):
        return _serialize_player_detail(target)
    return None


def serialize_shop_in_room(room):
    shop = get_shop_in_room(room)
    if not shop:
        return None
    return serialize_shop(shop)


def serialize_shop(shop):
    return {
        "id": shop.get("id"),
        "key": shop.get("key"),
        "desc": shop.get("desc", ""),
        "currency": shop.get("currency", "铜钱"),
        "room_id": shop.get("room_id"),
        "npc_id": shop.get("npc_id"),
        "inventory": [
            {
                "item_id": entry["item_id"],
                "key": entry["key"],
                "desc": entry.get("desc", ""),
                "price": entry["price"],
            }
            for entry in shop.get("inventory", [])
        ],
    }


def serialize_shop_by_id(shop_id):
    shop = get_shop_by_id(shop_id)
    if not shop:
        return None
    return serialize_shop(shop)


def serialize_market_in_room(room, page=1, keyword=None):
    market = get_market_in_room(room)
    if not market:
        return None
    return serialize_market(market, page=page, keyword=keyword)


def serialize_market(market, page=1, keyword=None):
    if not market:
        return None
    # list_market_goods 目前以 caller.location 作为坊市定位入口。
    # serializer 这里构造最小 fake caller，是为了复用同一套分页 / 过滤 / 过期逻辑，
    # 避免 market 展示在 action_router 和 detail serializer 中各维护一套查询分支。
    fake_caller = type("MarketCaller", (), {"location": type("MarketRoomHolder", (), {"db": type("Db", (), {})()})(), "id": 0})()
    fake_caller.location.db.room_id = market.get("room_id")
    fake_caller.location.db.content_id = market.get("room_id")
    listings = list_market_goods(fake_caller, page=page, keyword=keyword)
    return {
        "id": market.get("id"),
        "key": market.get("key"),
        "desc": market.get("desc", ""),
        "currency": market.get("currency", "铜钱"),
        "room_id": market.get("room_id"),
        "visible_listings": market.get("visible_listings"),
        "listing_ttl_seconds": market.get("listing_ttl_seconds"),
        "listings": listings.get("listings", []),
        "paging": {
            "page": listings.get("page", 1),
            "per_page": listings.get("per_page", market.get("visible_listings")),
            "total_count": listings.get("total_count", 0),
            "total_pages": listings.get("total_pages", 1),
            "keyword": listings.get("keyword"),
        },
    }


def serialize_market_by_id(market_id, page=1, keyword=None):
    market = get_market_by_id(market_id)
    if not market:
        return None
    return serialize_market(market, page=page, keyword=keyword)


def serialize_my_market_status(caller):
    result = list_my_market_status(caller)
    if not result.get("ok"):
        return None
    return {
        "market": serialize_market(result.get("market")),
        "active": list(result.get("active", [])),
        "sold": list(result.get("sold", [])),
        "reclaimable": list(result.get("reclaimable", [])),
        "pending_earnings": int(result.get("pending_earnings", 0)),
        "summary": dict(result.get("summary", {})),
    }


def serialize_trade_status(caller):
    result = list_trade_status(caller)
    if not result.get("ok"):
        return None
    return {
        "incoming": list(result.get("incoming", [])),
        "outgoing": list(result.get("outgoing", [])),
        "expired_offers_count": int(result.get("expired_offers_count", 0)),
        "summary": {
            "incoming_count": len(result.get("incoming", [])),
            "outgoing_count": len(result.get("outgoing", [])),
            "expired_offers_count": int(result.get("expired_offers_count", 0)),
        },
    }


def serialize_world_position(room):
    room_data = serialize_room(room)
    if not room_data:
        return None

    area = AREA_DEFINITIONS.get(room_data["area_key"]) if room_data.get("area_key") else None
    zone = ZONE_DEFINITIONS.get(area.get("zone_id")) if area else None
    map_data = MAP_DEFINITIONS.get(zone.get("map_id")) if zone else None
    return {
        "map": serialize_map(_find_map_key(map_data)) if map_data else None,
        "zone": serialize_zone(_find_zone_key(zone)) if zone else None,
        "area": serialize_area(room_data["area_key"]) if room_data.get("area_key") else None,
        "room": room_data,
    }


def serialize_quest_state(caller):
    main_state = get_quest_state(caller)
    main_stage = get_stage_data(main_state)
    side_key = get_active_side_quest_key(caller)
    side_stage = get_side_quest_data(side_key) if side_key else None
    return {
        "main": {
            "state": main_state,
            "id": main_stage.get("id") if main_stage else None,
            "title": main_stage.get("title") if main_stage else None,
            "objective": main_stage.get("objective") if main_stage else None,
            "giver": main_stage.get("giver") if main_stage else None,
        },
        "side": {
            "key": side_key,
            "state": get_side_quest_state(caller, side_key) if side_key else None,
            "id": side_stage.get("id") if side_stage else None,
            "title": side_stage.get("title") if side_stage else None,
            "objective": side_stage.get("objective") if side_stage else None,
            "giver": side_stage.get("giver") if side_stage else None,
        },
    }


def serialize_quest_log(caller):
    main_state = get_quest_state(caller)
    main_stage = get_stage_data(main_state)
    main_completed = main_state == COMPLETED

    side_entries = []
    for quest_key in get_started_side_quest_keys(caller, include_completed=True):
        quest = get_side_quest_data(quest_key)
        state = get_side_quest_state(caller, quest_key)
        side_entries.append(
            {
                "key": quest_key,
                "id": quest.get("id"),
                "state": state,
                "title": quest.get("title"),
                "objective": quest.get("objective"),
                "giver": quest.get("giver"),
                "giver_npc_id": quest.get("giver_npc_id"),
                "required_item_id": quest.get("required_item_id"),
                "completed": state == quest.get("completed_state"),
            }
        )

    return {
        "main": {
            "state": main_state,
            "id": main_stage.get("id") if main_stage else None,
            "title": main_stage.get("title") if main_stage else "入门试炼",
            "objective": main_stage.get("objective") if main_stage else None,
            "giver": main_stage.get("giver") if main_stage else None,
            "giver_npc_id": main_stage.get("giver_npc_id") if main_stage else None,
            "completed": main_completed,
            "available": main_state != NOT_STARTED,
        },
        "side": side_entries,
    }


def build_bootstrap_payload(caller):
    # bootstrap 是 H5 首屏最关键的聚合 DTO。
    # 这里的字段改动会同时影响登录后初始化、页面骨架渲染和本地缓存恢复。
    return {
        "character": serialize_character(caller),
        "position": serialize_world_position(caller.location),
        "quests": serialize_quest_log(caller),
        "inventory": serialize_inventory(caller),
        "battle": serialize_battle_state(caller),
        "chat": serialize_chat_status(caller),
        "ui_preferences": serialize_ui_preferences(caller),
    }


def serialize_ui_preferences(caller_or_account):
    return get_ui_preferences(caller_or_account)


def serialize_chat_status(caller, limit=40):
    return {
        "channels": list_channel_status(caller),
        "recent_messages": get_recent_chat_messages(caller, limit=limit),
        "recent_combat_logs": get_recent_combat_logs(caller, limit=max(10, min(int(limit or 40), 20))),
    }


def serialize_battle_state(caller):
    snapshot = get_battle_snapshot(caller)
    if not snapshot:
        return None
    return {
        **snapshot,
        "available_cards": list_available_cards(caller),
        "available_targets": list_available_targets(caller),
    }


def _serialize_player_detail(target):
    stats = get_stats(target)
    return {
        "id": str(getattr(target, "pk", None) or getattr(target, "id", None) or target.key),
        "key": target.key,
        "type": "player",
        "tag": "玩家",
        "title": stats["stage"] == "cultivator" and "修士" or "凡人",
        "desc": getattr(target.db, "desc", None) or "",
        "gender": stats.get("gender"),
        "gender_label": get_gender_label(stats.get("gender")),
        "realm": stats["realm"],
        "stats": [
            {"label": "阶段", "value": "修士" if stats["stage"] == "cultivator" else "凡人"},
            {"label": "气血", "value": f"{stats['hp']}/{stats['max_hp']}"},
            {"label": "灵力", "value": f"{stats['mp']}/{stats['max_mp']}"},
            {"label": "体力", "value": f"{stats['stamina']}/{stats['max_stamina']}"},
        ],
        "actions": [],
    }


def _serialize_npc_detail(target):
    sheet = get_npc_sheet(target)
    identity = sheet["identity"]
    progression = sheet["progression"]
    combat = sheet["combat_stats"]
    meta = sheet["npc_meta"]
    actions = []
    if meta.get("talk_route") or identity.get("npc_role"):
        actions.append("交谈")
    if meta.get("shop_id"):
        actions.append("商店")
    return {
        "id": identity.get("content_id") or str(getattr(target, "id", None) or target.key),
        "key": identity.get("name") or target.key,
        "type": "npc",
        "tag": "NPC",
        "title": identity.get("npc_role") or "人物",
        "desc": meta.get("presentation", {}).get("desc") or getattr(target.db, "desc", "") or "",
        "gender": identity.get("gender"),
        "gender_label": get_gender_label(identity.get("gender")),
        "realm": progression.get("realm"),
        "stats": [
            {"label": "身份", "value": identity.get("npc_role") or "npc"},
            {"label": "气血", "value": f"{combat['hp']}/{combat['max_hp']}"},
            {"label": "灵力", "value": f"{combat['mp']}/{combat['max_mp']}"},
            {"label": "体力", "value": f"{combat['stamina']}/{combat['max_stamina']}"},
            {"label": "攻击", "value": str(combat["attack_power"])},
            {"label": "防御", "value": str(combat["defense"])},
            {"label": "速度", "value": str(combat["speed"])},
        ],
        "actions": actions,
    }


def _serialize_enemy_detail(target):
    sheet = get_enemy_sheet(target)
    identity = sheet["identity"]
    progression = sheet["progression"]
    combat = sheet["combat_stats"]
    return {
        "id": identity.get("content_id") or str(getattr(target, "id", None) or target.key),
        "key": identity.get("name") or target.key,
        "type": "enemy",
        "tag": "敌人",
        "title": identity.get("enemy_type") or "敌人",
        "desc": sheet["enemy_meta"].get("presentation", {}).get("desc") or getattr(target.db, "desc", "") or "",
        "gender": identity.get("gender"),
        "gender_label": get_gender_label(identity.get("gender")),
        "realm": progression.get("realm"),
        "stats": [
            {"label": "类型", "value": identity.get("enemy_type") or "enemy"},
            {"label": "气血", "value": f"{combat['hp']}/{combat['max_hp']}"},
            {"label": "灵力", "value": f"{combat['mp']}/{combat['max_mp']}"},
            {"label": "体力", "value": f"{combat['stamina']}/{combat['max_stamina']}"},
            {"label": "攻击", "value": str(combat["attack_power"])},
            {"label": "防御", "value": str(combat["defense"])},
            {"label": "速度", "value": str(combat["speed"])},
        ],
        "actions": ["攻击"],
    }


def _serialize_room_npcs(room_id, room_content_id):
    payload = []
    for npc in NPC_DEFINITIONS:
        npc_def = get_npc_definition(npc.get("id"))
        if not npc_def or npc_def.get("room_id") not in {room_id, room_content_id}:
            continue
        identity = npc_def["identity"]
        progression = npc_def["progression"]
        payload.append(
            {
                "id": identity.get("content_id"),
                "key": identity.get("name"),
                "npc_type": identity.get("npc_role"),
                "npc_role": identity.get("npc_role"),
                "gender": identity.get("gender"),
                "gender_label": get_gender_label(identity.get("gender")),
                "realm": progression.get("realm"),
            }
        )
    return payload


def _serialize_room_objects(room_id, room_content_id):
    return [
        {
            "id": obj.get("id"),
            "key": obj.get("key"),
            "object_type": obj.get("object_type"),
        }
        for obj in OBJECT_DEFINITIONS
        if obj.get("room_id") in {room_id, room_content_id}
    ]


def _serialize_room_enemies(room_id, room_content_id):
    payload = []
    for enemy_key, enemy in ENEMY_DEFINITIONS.items():
        enemy_def = get_enemy_definition(enemy_key)
        if not enemy_def or enemy_def.get("room_id") not in {room_id, room_content_id}:
            continue
        identity = enemy_def["identity"]
        combat = enemy_def["combat_stats"]
        affinities = enemy_def["affinities"]
        payload.append(
            {
                "id": identity.get("content_id"),
                "key": identity.get("name"),
                "enemy_type": identity.get("enemy_type"),
                "gender": identity.get("gender"),
                "gender_label": get_gender_label(identity.get("gender")),
                "realm": enemy_def["progression"].get("realm"),
                "max_hp": combat.get("max_hp"),
                "attack_power": combat.get("attack_power"),
                "drop_item_id": enemy_def["enemy_meta"].get("drop_item_id"),
                "element": affinities.get("element"),
            }
        )
    return payload


def _find_zone_key(zone_data):
    if not zone_data:
        return None
    for key, value in ZONE_DEFINITIONS.items():
        if value.get("id") == zone_data.get("id"):
            return key
    return None


def _find_map_key(map_data):
    if not map_data:
        return None
    for key, value in MAP_DEFINITIONS.items():
        if value.get("id") == map_data.get("id"):
            return key
    return None
