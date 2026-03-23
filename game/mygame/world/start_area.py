"""
Starter area builder for the localized prototype.

This script is safe to run multiple times. It updates existing rooms/exits
in place and creates any missing ones.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
OBJECT_TYPECLASS = "typeclasses.objects.Object"


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
        pine,
        "木人桩",
        "一具被反复击打得有些发亮的木人桩安静立在林间，桩身上留着新旧不一的拳印。"
        "看起来很适合新人练手。",
        {"training_target": True},
    )

    ensure_object(
        pine,
        "青木傀儡",
        "一尊以青木和旧铁片拼接成的傀儡半蹲在林间，关节处仍能听见细碎摩擦声。"
        "它像是专门留给新人试手的陪练目标。",
        {
            "combat_target": True,
            "hp": 30,
            "max_hp": 30,
            "reward_exp": 12,
            "counter_damage": 6,
            "drop_key": "青木碎片",
            "drop_desc": "一块从青木傀儡身上掉下来的木质碎片，边缘仍留着浅浅灵纹。",
            "quest_flag": "dummy_kill",
        },
    )

    ensure_object(
        stair,
        "山石傀儡",
        "一尊由山石碎块与旧铜环拼起来的傀儡守在石阶转角，动作沉稳得近乎迟缓。"
        "可一旦它真正扑上来，那股力道又像落石般结实。",
        {
            "combat_target": True,
            "hp": 42,
            "max_hp": 42,
            "reward_exp": 18,
            "counter_damage": 9,
            "drop_key": "山纹石屑",
            "drop_desc": "几片带着浅灰纹路的石屑，摸上去仍残留着微弱的土行灵意。",
            "quest_flag": "stone_kill",
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
        "雾行山魈",
        "一只灰黑长臂的山魈伏在栏影与雾气之间，獠牙半露，动作却异常灵巧。"
        "它不像傀儡那样呆板，更像是在试探你什么时候会露出破绽。",
        {
            "combat_target": True,
            "hp": 36,
            "max_hp": 36,
            "reward_exp": 24,
            "counter_damage": 10,
            "drop_key": "雾露果",
            "drop_desc": "一枚沾着薄雾水气的青白果子，闻起来带着淡淡甘凉气息。",
            "quest_flag": "mist_kill",
        },
    )

    print("starter area ready")
    for room in (qingyundu, stair, pine, valley):
        print(room.id, room.key)


if __name__ == "__main__":
    main()
