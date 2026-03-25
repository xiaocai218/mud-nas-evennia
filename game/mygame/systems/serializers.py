"""Structured serializers for future H5/API clients."""

from systems.areas import get_area_for_room
from systems.battle import get_battle_snapshot, list_available_cards, list_available_targets
from systems.chat_payloads import serialize_chat_message
from systems.character_model import get_root_definition
from systems.content_loader import load_content
from systems.enemy_model import get_enemy_definition
from systems.items import get_inventory_items
from systems.market import get_market_by_id, get_market_in_room, list_market_goods, list_my_market_status
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
    return {
        "character": serialize_character(caller),
        "position": serialize_world_position(caller.location),
        "quests": serialize_quest_log(caller),
        "inventory": serialize_inventory(caller),
        "battle": serialize_battle_state(caller),
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


def _serialize_room_npcs(room_id, room_content_id):
    return [
        {
            "id": npc.get("id"),
            "key": npc.get("key"),
            "npc_type": npc.get("npc_type"),
        }
        for npc in NPC_DEFINITIONS
        if npc.get("room_id") in {room_id, room_content_id}
    ]


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
