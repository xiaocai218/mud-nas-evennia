"""
Simple beginner-facing commands for the localized prototype.
"""

from evennia.utils import evtable
from evennia.utils.create import create_object

from .command import Command


REALM_ORDER = [
    ("炼气一层", 0),
    ("炼气二层", 30),
    ("炼气三层", 80),
    ("炼气四层", 150),
]


def get_realm_from_exp(exp):
    realm = REALM_ORDER[0][0]
    for name, threshold in REALM_ORDER:
        if exp >= threshold:
            realm = name
    return realm


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if results else None


def get_quest_state(caller):
    return caller.db.guide_quest or "not_started"


class CmdNewbie(Command):
    """
    查看新手引导

    用法:
      新手
      begin

    显示当前服务器最基础的入门说明。
    """

    key = "新手"
    aliases = ["begin", "guide", "入门"]
    locks = "cmd:all()"
    help_category = "入门"

    def func(self):
        self.caller.msg(
            "|g新手指引|n\n"
            "\n"
            "欢迎来到这个中文 MUD 原型服，目前已经可以完成最基础的登录与探索。\n"
            "\n"
            "你现在最推荐先试这些命令：\n"
            "  |wlook|n        查看当前场景\n"
            "  |whelp 新手|n   查看新手帮助条目\n"
            "  |w新手|n        再次查看这份指引\n"
            "  |w状态|n        查看当前角色状态\n"
            "  |w修炼|n        消耗体力获取修为\n"
            "  |w休息|n        恢复体力\n"
            "  |w调息|n        恢复气血\n"
            "  |w练拳|n        在木人桩前练习拳脚\n"
            "  |w交谈 守渡老人|n  向新手 NPC 打听情况\n"
            "  |w攻击 青木傀儡|n  进行最基础战斗测试\n"
            "  |w炼化 青木碎片|n  将掉落物转成修为\n"
            "  |w背包|n        查看当前获得的物品\n"
            "  |w任务|n        查看当前新手任务进度\n"
            "  |w北|n / |w东|n      在新手区域中移动\n"
            "  |wchannels|n    查看可用频道\n"
            "\n"
            "当前世界仍在建设中，接下来会逐步加入地图、属性、战斗与修仙玩法。"
        )


class CmdStatus(Command):
    """
    查看角色状态

    用法:
      状态
      status

    查看当前角色的基础信息。
    """

    key = "状态"
    aliases = ["status", "stat", "属性"]
    locks = "cmd:all()"
    help_category = "角色"

    def func(self):
        caller = self.caller

        realm = caller.db.realm or "炼气一层"
        hp = caller.db.hp if caller.db.hp is not None else 100
        max_hp = caller.db.max_hp if caller.db.max_hp is not None else 100
        stamina = caller.db.stamina if caller.db.stamina is not None else 50
        max_stamina = caller.db.max_stamina if caller.db.max_stamina is not None else 50
        exp = caller.db.exp if caller.db.exp is not None else 0
        location = caller.location.key if caller.location else "未知"
        inventory = caller.contents_get(content_type="object")
        item_count = len([obj for obj in inventory if getattr(obj.db, "is_item", False)])

        table = evtable.EvTable(border="cells", pad_width=1)
        table.add_row("姓名", caller.key)
        table.add_row("境界", realm)
        table.add_row("气血", f"{hp}/{max_hp}")
        table.add_row("体力", f"{stamina}/{max_stamina}")
        table.add_row("修为", str(exp))
        table.add_row("位置", location)
        table.add_row("背包", f"{item_count} 件")

        self.caller.msg("|g角色状态|n\n%s" % table)


class CmdCultivate(Command):
    """
    进行修炼

    用法:
      修炼
      meditate

    消耗体力，获得修为，并在达到阈值时自动提升到更高境界。
    """

    key = "修炼"
    aliases = ["meditate", "xiulian"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        stamina = caller.db.stamina if caller.db.stamina is not None else 50
        max_stamina = caller.db.max_stamina if caller.db.max_stamina is not None else 50
        exp = caller.db.exp if caller.db.exp is not None else 0
        old_realm = caller.db.realm or get_realm_from_exp(exp)

        cost = 10
        gain = 15

        if stamina < cost:
            caller.msg(
                f"你尝试凝神运气，却觉得体力不济。当前体力仅有 |w{stamina}|n 点，至少需要 |w{cost}|n 点才能修炼。"
            )
            return

        stamina -= cost
        exp += gain
        new_realm = get_realm_from_exp(exp)

        caller.db.stamina = max(0, min(stamina, max_stamina))
        caller.db.exp = exp
        caller.db.realm = new_realm

        caller.msg(
            "你盘膝而坐，吐纳周天，缓缓引导四周稀薄灵气汇入经脉。\n"
            f"|g本次修炼收获|n: 修为 +{gain}，体力 -{cost}\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}，体力 {caller.db.stamina}/{max_stamina}"
        )

        if new_realm != old_realm:
            caller.msg(f"|y你心神一振，灵息贯通，境界提升至 {new_realm}。|n")


class CmdRest(Command):
    """
    进行休息

    用法:
      休息
      rest

    恢复一些体力，便于继续修炼或练习。
    """

    key = "休息"
    aliases = ["rest", "recover"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        stamina = caller.db.stamina if caller.db.stamina is not None else 50
        max_stamina = caller.db.max_stamina if caller.db.max_stamina is not None else 50
        gain = 15

        if stamina >= max_stamina:
            caller.msg("你调匀呼吸，发现自己气息平稳，暂时不需要额外休息。")
            return

        caller.db.stamina = min(max_stamina, stamina + gain)
        caller.msg(
            "你找了处安稳地方略作休整，呼吸渐渐平缓，筋骨中的疲意也散去了不少。\n"
            f"|g体力恢复|n: +{caller.db.stamina - stamina}，当前体力 {caller.db.stamina}/{max_stamina}"
        )


class CmdRecoverHp(Command):
    """
    调整气息

    用法:
      调息
      heal

    平复气血，恢复少量生命。
    """

    key = "调息"
    aliases = ["heal", "recoverhp"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        hp = caller.db.hp if caller.db.hp is not None else 100
        max_hp = caller.db.max_hp if caller.db.max_hp is not None else 100
        gain = 20

        if hp >= max_hp:
            caller.msg("你默运周天，只觉气血充盈，暂时无需额外调息。")
            return

        caller.db.hp = min(max_hp, hp + gain)
        caller.msg(
            "你收摄心神，缓缓调匀体内紊乱气机，胸腹间的闷痛也散去了不少。\n"
            f"|g气血恢复|n: +{caller.db.hp - hp}，当前气血 {caller.db.hp}/{max_hp}"
        )


class CmdTrain(Command):
    """
    练习拳脚

    用法:
      练拳
      train

    在木人桩前练习基础招式，少量消耗体力并获得修为。
    """

    key = "练拳"
    aliases = ["train", "practice"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        target = get_target(caller, "木人桩")
        if not target:
            caller.msg("你环顾四周，没有找到适合练拳的木人桩。")
            return

        stamina = caller.db.stamina if caller.db.stamina is not None else 50
        max_stamina = caller.db.max_stamina if caller.db.max_stamina is not None else 50
        exp = caller.db.exp if caller.db.exp is not None else 0
        old_realm = caller.db.realm or get_realm_from_exp(exp)

        cost = 5
        gain = 8

        if stamina < cost:
            caller.msg(f"你刚摆开架势就觉得双臂发沉，至少需要 |w{cost}|n 点体力才能继续练拳。")
            return

        stamina -= cost
        exp += gain
        new_realm = get_realm_from_exp(exp)

        caller.db.stamina = max(0, min(stamina, max_stamina))
        caller.db.exp = exp
        caller.db.realm = new_realm

        caller.msg(
            "你对着木人桩反复演练基础拳架，出拳、收势、转身都比刚才稳了几分。\n"
            f"|g本次练拳收获|n: 修为 +{gain}，体力 -{cost}\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}，体力 {caller.db.stamina}/{max_stamina}"
        )

        if new_realm != old_realm:
            caller.msg(f"|y你的气息在练拳中愈发凝练，境界提升至 {new_realm}。|n")


class CmdTalk(Command):
    """
    与目标交谈

    用法:
      交谈 <目标>
      talk <目标>

    用于向当前场景中的 NPC 询问提示。
    """

    key = "交谈"
    aliases = ["talk", "对话", "问询"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想和谁交谈？用法：|w交谈 守渡老人|n")
            return

        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return

        if not getattr(target.db, "npc_role", None):
            caller.msg(f"{target.key} 看起来并不打算和你搭话。")
            return

        if target.key == "守渡老人":
            quest_state = get_quest_state(caller)
            if quest_state == "not_started":
                caller.db.guide_quest = "started"
                caller.msg(
                    "守渡老人抬眼看了你一会儿，慢声说道：\n"
                    "“初来乍到，不必心急。先去古松林击倒一次|w青木傀儡|n，再回来见我。”\n"
                    "“记住，体力不足就|w休息|n，气血受损就|w调息|n。打完回来，我自会给你些入门资粮。”\n"
                    "|g任务已接取|n: 击败一次青木傀儡。"
                )
                return
            if quest_state == "started" and caller.db.guide_quest_dummy_kill:
                caller.db.guide_quest = "completed"
                reward_exp = 20
                exp = caller.db.exp if caller.db.exp is not None else 0
                old_realm = caller.db.realm or get_realm_from_exp(exp)
                exp += reward_exp
                new_realm = get_realm_from_exp(exp)
                caller.db.exp = exp
                caller.db.realm = new_realm
                reward = create_object(
                    "typeclasses.items.Item",
                    key="渡口药包",
                    location=caller,
                )
                reward.db.desc = "守渡老人交给你的简陋药包，带着些草木辛气，也许日后会派上用场。"
                caller.msg(
                    "守渡老人看你气息沉稳了几分，微微点头：\n"
                    "“不错，至少不是站都站不稳的新雏了。这点东西你先拿着。”\n"
                    f"|g任务完成|n: 修为 +{reward_exp}，获得 |w{reward.key}|n。"
                )
                if new_realm != old_realm:
                    caller.msg(f"|y在这一番历练之后，你的境界提升至 {new_realm}。|n")
                return
            if quest_state == "started":
                caller.msg(
                    "守渡老人拄着旧杖，朝东边古松林扬了扬下巴：\n"
                    "“先去把青木傀儡打倒一次，再回来见我。”"
                )
                return
            if quest_state == "completed":
                caller.msg(
                    "守渡老人淡淡一笑：\n"
                    "“该教你的入门路数，你已经走过一遍了。接下来，就看你自己能走多远。”"
                )
                return
            caller.msg(
                "守渡老人抬眼看了你一会儿，却没有多说什么。"
            )
            return

        caller.msg(f"{target.key} 朝你点了点头，却没有多说什么。")


class CmdAttack(Command):
    """
    攻击目标

    用法:
      攻击 <目标>
      attack <目标>

    对当前场景中的训练目标发动一次简单攻击。
    """

    key = "攻击"
    aliases = ["attack", "fight", "打"]
    locks = "cmd:all()"
    help_category = "战斗"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要攻击谁？用法：|w攻击 青木傀儡|n")
            return

        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近找到这个目标。")
            return

        if not getattr(target.db, "combat_target", False):
            caller.msg(f"{target.key} 并不是适合出手的目标。")
            return

        stamina = caller.db.stamina if caller.db.stamina is not None else 50
        max_stamina = caller.db.max_stamina if caller.db.max_stamina is not None else 50
        hp = caller.db.hp if caller.db.hp is not None else 100
        max_hp = caller.db.max_hp if caller.db.max_hp is not None else 100
        exp = caller.db.exp if caller.db.exp is not None else 0
        old_realm = caller.db.realm or get_realm_from_exp(exp)
        target_hp = target.db.hp if target.db.hp is not None else 30
        target_max_hp = target.db.max_hp if target.db.max_hp is not None else 30

        cost = 8
        damage = 12
        gain = 12
        counter = 6

        if stamina < cost:
            caller.msg(f"你提气欲上，却发现体力不足。至少需要 |w{cost}|n 点体力才能出手。")
            return

        stamina -= cost
        target_hp -= damage

        caller.db.stamina = max(0, min(stamina, max_stamina))

        if target_hp <= 0:
            exp += gain
            new_realm = get_realm_from_exp(exp)
            caller.db.exp = exp
            caller.db.realm = new_realm
            target.db.hp = target_max_hp
            if target.key == "青木傀儡" and get_quest_state(caller) == "started":
                caller.db.guide_quest_dummy_kill = True
            drop = create_object(
                "typeclasses.items.Item",
                key="青木碎片",
                location=caller,
            )
            drop.db.desc = "一块从青木傀儡身上掉下来的木质碎片，边缘仍留着浅浅灵纹。"
            caller.msg(
                f"你一掌击中 {target.key} 的胸口，木屑四散，傀儡轰然倒退。\n"
                f"|g战斗收获|n: 修为 +{gain}，体力 -{cost}\n"
                f"你拾起了 |w{drop.key}|n。\n"
                f"{target.key} 很快被重新扶正，似乎又能继续陪练了。"
            )
            if new_realm != old_realm:
                caller.msg(f"|y在实战磨砺之下，你的境界提升至 {new_realm}。|n")
            return

        target.db.hp = target_hp
        hp = max(0, hp - counter)
        caller.db.hp = hp
        caller.msg(
            f"你朝 {target.key} 猛然出手，打得桩身一震。\n"
            f"{target.key} 随即回震而来，撞得你胸口微微发闷。\n"
            f"|g当前效果|n: {target.key} 气血 {target_hp}/{target_max_hp}，你的体力 {caller.db.stamina}/{max_stamina}，你的气血 {hp}/{max_hp}"
        )

        if hp <= 0:
            caller.db.hp = max_hp
            caller.db.stamina = max_stamina
            if caller.location and caller.location.key != "青云渡":
                home = caller.search("青云渡", global_search=True, quiet=True)
                if home:
                    caller.move_to(home[0], quiet=True)
            caller.msg("|r你被反震得眼前发黑，只得狼狈退回青云渡重新调息。|n")


class CmdInventory(Command):
    """
    查看背包

    用法:
      背包
      inventory

    查看当前持有的基础物品。
    """

    key = "背包"
    aliases = ["inventory", "inv", "bag"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        items = [obj for obj in caller.contents_get(content_type="object") if getattr(obj.db, "is_item", False)]
        if not items:
            caller.msg("你的背包里空空如也。")
            return

        table = evtable.EvTable("名称", "说明", border="cells", pad_width=1)
        for item in items:
            table.add_row(item.key, item.db.desc or "暂无说明")

        caller.msg("|g背包|n\n%s" % table)


class CmdRefine(Command):
    """
    炼化物品

    用法:
      炼化 <物品名>
      refine <物品名>

    将特定材料炼化为修为。
    """

    key = "炼化"
    aliases = ["refine", "absorb"]
    locks = "cmd:all()"
    help_category = "物品"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你要炼化什么？用法：|w炼化 青木碎片|n")
            return

        item_name = self.args.strip()
        items = [obj for obj in caller.contents_get(content_type="object") if getattr(obj.db, "is_item", False)]
        item = next((obj for obj in items if obj.key == item_name), None)
        if not item:
            caller.msg("你的背包里没有这个物品。")
            return

        exp = caller.db.exp if caller.db.exp is not None else 0
        old_realm = caller.db.realm or get_realm_from_exp(exp)

        if item.key == "青木碎片":
            gain = 10
            exp += gain
            new_realm = get_realm_from_exp(exp)
            caller.db.exp = exp
            caller.db.realm = new_realm
            item.delete()
            caller.msg(
                f"你将 {item_name} 捧在掌心，缓缓炼化其中残存的灵息。\n"
                f"|g炼化收获|n: 修为 +{gain}\n"
                f"|g当前状态|n: {new_realm}，修为 {exp}"
            )
            if new_realm != old_realm:
                caller.msg(f"|y借这一缕灵息之助，你的境界提升至 {new_realm}。|n")
            return

        caller.msg(f"{item_name} 现在还无法炼化。")


class CmdQuest(Command):
    """
    查看任务

    用法:
      任务
      quest

    查看当前新手任务进度。
    """

    key = "任务"
    aliases = ["quest", "missions"]
    locks = "cmd:all()"
    help_category = "任务"

    def func(self):
        caller = self.caller
        state = get_quest_state(caller)
        if state == "not_started":
            caller.msg("你暂时还没有接到任务。可以试试 |w交谈 守渡老人|n。")
            return
        if state == "started":
            done = "已完成" if caller.db.guide_quest_dummy_kill else "未完成"
            caller.msg(
                "|g当前任务|n\n"
                "任务名: 渡口试手\n"
                f"目标: 击败一次青木傀儡 [{done}]\n"
                "交付人: 守渡老人"
            )
            return
        caller.msg(
            "|g当前任务|n\n"
            "任务名: 渡口试手\n"
            "状态: 已完成\n"
            "守渡老人已经认可你完成了最基础的入门试炼。"
        )
