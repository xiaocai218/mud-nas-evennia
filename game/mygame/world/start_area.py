"""
Starter area builder for the localized prototype.

This script is safe to run multiple times. It updates existing rooms/exits
in place and creates any missing ones.
"""

import os
import sys
import json
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
ENEMY_DATA_PATH = Path(__file__).resolve().parent / "data" / "enemies.json"


def load_enemy_data():
    with ENEMY_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def get_room(room_id, key, desc):
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
        obj = create_object(
            OBJECT_TYPECLASS,
            key=key,
            location=location,
        )
    obj.db.desc = desc
    for attr_key, attr_value in (attrs or {}).items():
        setattr(obj.db, attr_key, attr_value)
    obj.save()
    return obj


def main():
    enemies = load_enemy_data()
    qingyundu = get_room(
        2,
        "青云渡",
        "晨雾沿着石阶缓缓流下，古渡口边立着一块半旧的青碑，上书'青云渡'三字。\n"
        "这里是初入九州的修行者暂歇之地，向前可问道，向后可回望凡尘。\n"
        "你隐约听见远处钟声回荡，像是在提醒你，一段新的旅程已经开始。",
    )

    stair = get_or_create_room(
        "问道石阶",
        "青石长阶沿山势缓缓向上，石缝间生着些许青苔。两侧风声清冷，"
        "远处偶尔传来诵经与钟鸣，令人不由自主收敛心神。",
    )

    pine = get_or_create_room(
        "古松林",
        "几株古松盘根错节，枝叶高高探向天幕。林间有碎石小径通行，"
        "空气里带着松脂与湿土的清气，适合新人暂作停留。",
    )

    valley = get_or_create_room(
        "溪谷栈道",
        "栈道贴着山壁向前探出，脚下隐约能听见溪流撞击乱石的空响。"
        "山雾时聚时散，将前方的木栏和藤蔓都笼上一层湿润的冷意。",
    )

    ensure_exit(qingyundu, stair, "北", ["north", "n"])
    ensure_exit(stair, qingyundu, "南", ["south", "s"])
    ensure_exit(qingyundu, pine, "东", ["east", "e"])
    ensure_exit(pine, qingyundu, "西", ["west", "w"])
    ensure_exit(stair, valley, "北", ["north", "n"])
    ensure_exit(valley, stair, "南", ["south", "s"])

    ensure_object(
        qingyundu,
        "守渡老人",
        "一位须发半白的老人倚着渡口旧碑静静站着，衣袍洗得发旧，目光却十分沉稳。"
        "看起来像是见惯了来来往往的新人修士。",
        {"npc_role": "guide"},
    )

    ensure_object(
        qingyundu,
        "药庐学徒",
        "一名穿着青灰短褂的年轻学徒守在一只竹匾旁，袖口上还沾着细碎药粉。"
        "他像是刚从药庐跑出来帮忙分拣药材，神情里带着些忙乱。",
        {"npc_role": "herbalist"},
    )

    ensure_object(
        pine,
        "木人桩",
        "一具被反复击打得有些发亮的木人桩安静立在林间，桩身上留着新旧不一的拳印。"
        "看起来很适合新人练手。",
        {"training_target": True},
    )

    ensure_object(
        pine,
        enemies["qingmu_dummy"]["key"],
        enemies["qingmu_dummy"]["desc"],
        {
            "combat_target": True,
            "enemy_id": "qingmu_dummy",
            "hp": enemies["qingmu_dummy"]["hp"],
            "max_hp": enemies["qingmu_dummy"]["max_hp"],
            "reward_exp": enemies["qingmu_dummy"]["reward_exp"],
            "counter_damage": enemies["qingmu_dummy"]["counter_damage"],
            "damage_taken": enemies["qingmu_dummy"]["damage_taken"],
            "drop_key": enemies["qingmu_dummy"]["drop_key"],
            "quest_flag": enemies["qingmu_dummy"]["quest_flag"],
        },
    )

    ensure_object(
        stair,
        enemies["stone_dummy"]["key"],
        enemies["stone_dummy"]["desc"],
        {
            "combat_target": True,
            "enemy_id": "stone_dummy",
            "hp": enemies["stone_dummy"]["hp"],
            "max_hp": enemies["stone_dummy"]["max_hp"],
            "reward_exp": enemies["stone_dummy"]["reward_exp"],
            "counter_damage": enemies["stone_dummy"]["counter_damage"],
            "damage_taken": enemies["stone_dummy"]["damage_taken"],
            "drop_key": enemies["stone_dummy"]["drop_key"],
            "quest_flag": enemies["stone_dummy"]["quest_flag"],
        },
    )

    ensure_object(
        valley,
        "巡山弟子",
        "一名束发利落的青年弟子立在栈道旁，腰间挂着木牌与短哨，目光总不时扫向雾气深处。"
        "看起来是负责这一带巡查的外门弟子。",
        {"npc_role": "scout"},
    )

    ensure_object(
        valley,
        enemies["mist_ape"]["key"],
        enemies["mist_ape"]["desc"],
        {
            "combat_target": True,
            "enemy_id": "mist_ape",
            "hp": enemies["mist_ape"]["hp"],
            "max_hp": enemies["mist_ape"]["max_hp"],
            "reward_exp": enemies["mist_ape"]["reward_exp"],
            "counter_damage": enemies["mist_ape"]["counter_damage"],
            "damage_taken": enemies["mist_ape"]["damage_taken"],
            "drop_key": enemies["mist_ape"]["drop_key"],
            "quest_flag": enemies["mist_ape"]["quest_flag"],
        },
    )

    print("starter area ready")
    for room in (qingyundu, stair, pine, valley):
        print(room.id, room.key)


if __name__ == "__main__":
    main()
