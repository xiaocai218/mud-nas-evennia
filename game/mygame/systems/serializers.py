"""Structured serializers for future H5/API clients."""

from systems.areas import get_area_for_room
from systems.content_loader import load_content
from systems.items import get_inventory_items
from systems.player_stats import get_active_effect_text, get_stats
from systems.quests import (
    get_active_side_quest_key,
    get_quest_state,
    get_side_quest_data,
    get_side_quest_state,
    get_stage_data,
)
from systems.shops import get_shop_in_room


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
    return {
        "name": caller.key,
        "profile": getattr(caller.db, "character_profile", None),
        "realm": stats["realm"],
        "hp": stats["hp"],
        "max_hp": stats["max_hp"],
        "stamina": stats["stamina"],
        "max_stamina": stats["max_stamina"],
        "exp": stats["exp"],
        "copper": stats["copper"],
        "effects_text": get_active_effect_text(caller),
        "inventory_count": len(get_inventory_items(caller)),
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
    }


def serialize_shop_in_room(room):
    shop = get_shop_in_room(room)
    if not shop:
        return None
    return {
        "id": shop.get("id"),
        "key": shop.get("key"),
        "currency": shop.get("currency", "铜钱"),
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


def build_bootstrap_payload(caller):
    return {
        "character": serialize_character(caller),
        "position": serialize_world_position(caller.location),
        "quests": serialize_quest_state(caller),
        "inventory": serialize_inventory(caller),
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
        if enemy.get("room_id") not in {room_id, room_content_id}:
            continue
        payload.append(
            {
                "id": enemy.get("id"),
                "key": enemy.get("enemy_key", enemy_key),
                "max_hp": enemy.get("max_hp"),
                "damage": enemy.get("damage"),
                "drop_item_id": enemy.get("drop_item_id"),
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
