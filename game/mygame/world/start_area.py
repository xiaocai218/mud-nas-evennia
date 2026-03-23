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

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


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


def get_room_by_id(room_id, key, desc):
    room = ObjectDB.objects.get(id=room_id)
    room.key = key
    room.db.desc = desc
    room.save()
    return room


def get_or_create_room(key, desc):
    room = ObjectDB.objects.filter(db_key=key).first()
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key)
    room.db.desc = desc
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
    obj = ObjectDB.objects.filter(db_location=location, db_key=key).first()
    if not obj:
        obj = create_object(OBJECT_TYPECLASS, key=key, location=location)
    obj.db.desc = desc
    for attr_key, attr_value in (attrs or {}).items():
        setattr(obj.db, attr_key, attr_value)
    obj.save()
    return obj


def build_rooms(room_defs):
    rooms = {}
    for room_id, room_data in room_defs.items():
        if room_data.get("id"):
            room = get_room_by_id(room_data["id"], room_data["key"], room_data["desc"])
        else:
            room = get_or_create_room(room_data["key"], room_data["desc"])
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
        ensure_object(rooms[obj["room"]], obj["key"], obj["desc"], obj.get("attrs"))


def build_enemies(rooms, enemy_defs):
    for enemy_id, enemy in enemy_defs.items():
        room_id = enemy["room"]
        ensure_object(
            rooms[room_id],
            enemy["key"],
            enemy["desc"],
            {
                "combat_target": True,
                "enemy_id": enemy_id,
                "hp": enemy["hp"],
                "max_hp": enemy["max_hp"],
                "reward_exp": enemy["reward_exp"],
                "counter_damage": enemy["counter_damage"],
                "damage_taken": enemy["damage_taken"],
                "drop_key": enemy["drop_key"],
                "quest_flag": enemy["quest_flag"],
            },
        )


def main():
    room_data = load_json(ROOM_DATA_PATH)
    npc_data = load_json(NPC_DATA_PATH)
    object_data = load_json(OBJECT_DATA_PATH)
    enemy_data = load_json(ENEMY_DATA_PATH)

    rooms = build_rooms(room_data["rooms"])
    build_exits(rooms, room_data["exits"])
    build_objects(rooms, npc_data["npcs"])
    build_objects(rooms, object_data["objects"])
    build_enemies(rooms, enemy_data)

    print("starter area ready")
    for room_id in room_data["rooms"]:
        room = rooms[room_id]
        print(room.id, room.key)


if __name__ == "__main__":
    main()
