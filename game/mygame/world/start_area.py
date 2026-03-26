"""
Starter area builder for the localized prototype.

This script is safe to run multiple times. It updates existing rooms/exits
in place and creates any missing ones.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB
from systems.enemy_model import get_enemy_definition
from systems.npc_model import get_npc_definition, ensure_npc_model
from systems.object_index import get_object_by_content_id


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
OBJECT_TYPECLASS = "typeclasses.objects.Object"
DATA_DIR = Path(__file__).resolve().parent / "data"
ROOM_DATA_PATH = DATA_DIR / "rooms.json"
NPC_DATA_PATH = DATA_DIR / "npcs.json"
OBJECT_DATA_PATH = DATA_DIR / "objects.json"
ENEMY_DATA_PATH = DATA_DIR / "enemies.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def get_room_by_id(room_id, key, desc, content_id=None, room_key=None):
    room = ObjectDB.objects.get(id=room_id)
    room.key = key
    room.db.desc = desc
    if room_key:
        room.db.room_id = room_key
    if content_id:
        room.db.content_id = content_id
    room.save()
    return room


def get_or_create_room(key, desc, content_id=None, room_key=None):
    room = ObjectDB.objects.filter(db_key=key).first()
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key)
    room.db.desc = desc
    if room_key:
        room.db.room_id = room_key
    if content_id:
        room.db.content_id = content_id
    room.save()
    return room


def ensure_exit(location, destination, key, aliases):
    exit_obj = ObjectDB.objects.filter(db_location=location, db_key=key).first()
    if not exit_obj:
        exit_obj = create_object(
            EXIT_TYPECLASS,
            key=key,
            location=location,
            destination=destination,
            aliases=aliases,
        )
    else:
        exit_obj.destination = destination
        exit_obj.aliases.clear()
        for alias in aliases:
            exit_obj.aliases.add(alias)
        exit_obj.save()
    return exit_obj


def ensure_object(location, key, desc, attrs=None):
    attrs = dict(attrs or {})
    content_id = attrs.get("content_id")
    obj = get_object_by_content_id(content_id)
    if not obj:
        obj = ObjectDB.objects.filter(db_location=location, db_key=key).first()
    if not obj:
        obj = create_object(OBJECT_TYPECLASS, key=key, location=location)
    else:
        obj.key = key
        obj.location = location
    obj.db.desc = desc
    for attr_key, attr_value in attrs.items():
        setattr(obj.db, attr_key, attr_value)
    obj.save()
    return obj


def build_rooms(room_defs):
    rooms = {}
    for room_id, room_data in room_defs.items():
        if room_data.get("id"):
            room = get_room_by_id(
                room_data["id"],
                room_data["key"],
                room_data["desc"],
                content_id=room_data.get("content_id", room_id),
                room_key=room_id,
            )
        else:
            room = get_or_create_room(
                room_data["key"],
                room_data["desc"],
                content_id=room_data.get("content_id", room_id),
                room_key=room_id,
            )
        if room_data.get("area_id"):
            room.db.area_id = room_data["area_id"]
        rooms[room_id] = room
    return rooms


def build_exits(rooms, exit_defs):
    for exit_data in exit_defs:
        ensure_exit(
            rooms[exit_data["from"]],
            rooms[exit_data["to"]],
            exit_data["key"],
            exit_data["aliases"],
        )


def build_objects(rooms, object_defs):
    for obj in object_defs:
        attrs = dict(obj.get("attrs", {}))
        if obj.get("object_type"):
            attrs["object_type"] = obj["object_type"]
        if obj.get("id"):
            attrs["content_id"] = obj["id"]
        room_key = obj.get("room_id") or obj.get("room")
        ensure_object(rooms[room_key], obj["key"], obj["desc"], attrs)


def build_npcs(rooms, npc_defs):
    for npc in npc_defs:
        npc_id = npc.get("id")
        npc_def = get_npc_definition(npc_id) if npc_id else None
        room_key = (npc_def or {}).get("room_id") or npc.get("room_id") or npc.get("room")
        room = rooms.get(room_key)
        if not room and room_key:
            room = next((candidate for candidate in rooms.values() if getattr(candidate.db, "content_id", None) == room_key), None)
        if not room:
            continue
        identity = (npc_def or {}).get("identity", {})
        progression = (npc_def or {}).get("progression", {})
        combat_stats = (npc_def or {}).get("combat_stats", {})
        npc_meta = (npc_def or {}).get("npc_meta", {})
        obj = ensure_object(
            room,
            identity.get("name") or npc["key"],
            npc_meta.get("presentation", {}).get("desc") or npc.get("desc", ""),
            {
                **dict(npc.get("attrs", {})),
                "content_id": identity.get("content_id") or npc.get("id"),
                "template_id": identity.get("template_id") or npc.get("id"),
                "npc_id": identity.get("template_id") or npc.get("id"),
                "identity": identity,
                "progression": progression,
                "primary_stats": (npc_def or {}).get("primary_stats", {}),
                "combat_stats": combat_stats,
                "affinities": (npc_def or {}).get("affinities", {}),
                "reserves": (npc_def or {}).get("reserves", {}),
                "npc_meta": npc_meta,
                "npc_role": identity.get("npc_role") or (npc.get("attrs", {}) or {}).get("npc_role"),
                "talk_route": npc_meta.get("talk_route") or (npc.get("attrs", {}) or {}).get("talk_route"),
                "shop_id": npc_meta.get("shop_id") or (npc.get("attrs", {}) or {}).get("shop_id"),
                "gender": identity.get("gender"),
                "realm": progression.get("realm"),
                "hp": combat_stats.get("hp"),
                "max_hp": combat_stats.get("max_hp"),
            },
        )
        ensure_npc_model(obj)


def build_enemies(rooms, enemy_defs):
    for enemy_id in enemy_defs:
        enemy = get_enemy_definition(enemy_id)
        if not enemy:
            continue
        room_id = enemy.get("room_id")
        identity = enemy["identity"]
        combat_stats = enemy["combat_stats"]
        enemy_meta = enemy["enemy_meta"]
        ensure_object(
            rooms[room_id],
            identity["name"],
            enemy_meta.get("presentation", {}).get("desc") or enemy_meta.get("presentation", {}).get("description") or "",
            {
                "combat_target": True,
                "content_id": identity["content_id"],
                "enemy_id": identity["template_id"],
                "template_id": identity["template_id"],
                "identity": identity,
                "progression": enemy["progression"],
                "primary_stats": enemy["primary_stats"],
                "combat_stats": combat_stats,
                "affinities": enemy["affinities"],
                "reserves": enemy["reserves"],
                "enemy_meta": enemy_meta,
                "enemy_type": identity["enemy_type"],
                "faction": identity["faction"],
                "is_boss": identity["is_boss"],
                "tags": identity["tags"],
                "hp": combat_stats["hp"],
                "max_hp": combat_stats["max_hp"],
                "reward_exp": enemy_meta.get("reward_exp"),
                "counter_damage": enemy_meta.get("counter_damage"),
                "damage_taken": enemy_meta.get("damage_taken"),
                "stamina_cost": enemy_meta.get("stamina_cost"),
                "drop_item_id": enemy_meta.get("drop_item_id"),
                "drop_key": enemy_meta.get("drop_key"),
                "drop_desc": enemy_meta.get("drop_desc"),
                "quest_flag": (enemy_meta.get("quest_hooks") or {}).get("quest_flag"),
            },
        )


def main():
    room_data = load_json(ROOM_DATA_PATH)
    npc_data = load_json(NPC_DATA_PATH)
    object_data = load_json(OBJECT_DATA_PATH)
    enemy_data = load_json(ENEMY_DATA_PATH)

    rooms = build_rooms(room_data["rooms"])
    build_exits(rooms, room_data["exits"])
    build_npcs(rooms, npc_data["npcs"])
    build_objects(rooms, object_data["objects"])
    build_enemies(rooms, enemy_data)

    print("starter area ready")
    for room_id in room_data["rooms"]:
        room = rooms[room_id]
        print(room.id, room.key)


if __name__ == "__main__":
    main()
