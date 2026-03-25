"""Developer/admin maintenance commands."""

import evennia
from evennia.utils import evtable

from .command import Command
from systems.battle import clear_battle, get_battle_log, start_battle
from systems.character_model import ROOT_CHOICES, get_root_label, normalize_root_choice, reset_spiritual_root
from systems.content_loader import (
    find_content_record,
    get_content_summary,
    list_content_names,
    reload_content,
    validate_content,
)
from systems.enemy_model import ensure_enemy_model, get_enemy_definition, is_enemy, spawn_enemy_instance
from systems.object_index import get_object_by_content_id
from systems.player_stats import add_currency, get_stats
from systems.quests import ROOT_CHOICE_READY, prepare_root_choice_state
from systems.world_objects import trigger_object

TEST_DESTINATIONS = {
    "坊市": "room_qingyun_outer_market",
    "外门坊市": "room_qingyun_outer_market",
    "外门": "room_qingyun_outer_court",
    "青云外门": "room_qingyun_outer_court",
    "升仙台": "room_shengxian_platform",
    "测灵石": "room_shengxian_platform",
    "试战木场": "room_ferry_battle_yard",
    "战斗房": "room_ferry_battle_yard",
    "测试战斗房": "room_ferry_battle_yard",
}

class CmdContent(Command):
    key = "内容"
    aliases = ["content"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        if not args:
            table = evtable.EvTable("内容集", "条目数", border="cells", pad_width=1)
            for entry in get_content_summary():
                table.add_row(entry["name"], str(entry["count"]))
            caller.msg(
                "|g内容索引|n\n%s\n\n"
                "用法:\n"
                "  |w内容 重载|n\n"
                "  |w内容 重载 <内容集>|n\n"
                "  |w内容 查看 <内容集> <id或key>|n\n"
                "  |w内容 校验|n\n"
                "可用内容集: %s"
                % (table, "、".join(list_content_names()))
            )
            return

        parts = args.split()
        action = parts[0]

        if action == "重载":
            target = parts[1] if len(parts) > 1 else None
            if target and target not in list_content_names() and target not in {
                "items",
                "enemies",
                "rooms",
                "npcs",
                "objects",
                "quests",
                "dialogues",
                "npc_routes",
                "realms",
                "effects",
                "character_defaults",
                "help_content",
            }:
                caller.msg("没有这个内容集。")
                return
            reload_content(target)
            caller.msg(f"|g内容重载|n: 已重载 {target or '全部缓存内容'}。")
            return

        if action == "查看":
            if len(parts) < 3:
                caller.msg("用法：|w内容 查看 <内容集> <id或key>|n")
                return
            content_name = parts[1]
            lookup = " ".join(parts[2:])
            record = find_content_record(content_name, lookup)
            if not record:
                caller.msg("没有找到对应内容。")
                return
            lines = [f"{key}: {value}" for key, value in record.items()]
            caller.msg("|g内容详情|n\n" + "\n".join(lines))
            return

        if action == "校验":
            issues = validate_content()
            if not issues:
                caller.msg("|g内容校验|n: 未发现配置引用错误。")
                return
            caller.msg("|r内容校验发现以下问题|n\n" + "\n".join(f"- {issue}" for issue in issues))
            return

        caller.msg("可用子命令：|w重载|n、|w查看|n、|w校验|n")


class CmdTestGoto(Command):
    key = "测试传送"
    aliases = ["testgoto", "devgoto"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        target_name = self.args.strip()
        if not target_name:
            caller.msg("用法：|w测试传送 坊市|n 或 |w测试传送 玩家名 坊市|n。当前可用：坊市、外门。")
            return

        parts = target_name.split()
        target = caller
        destination_name = target_name
        if len(parts) >= 2:
            possible_destination = parts[-1]
            possible_target = " ".join(parts[:-1]).strip()
            if possible_destination in TEST_DESTINATIONS and possible_target:
                destination_name = possible_destination
                target = _find_test_target(possible_target)
                if not target:
                    caller.msg("没有找到要传送的目标玩家。")
                    return

        room_content_id = TEST_DESTINATIONS.get(destination_name)
        if not room_content_id:
            caller.msg("没有这个测试传送目标。当前可用：坊市、外门。")
            return

        destination = get_object_by_content_id(room_content_id)
        if not destination:
            caller.msg("目标房间当前不存在。请先同步最新世界并重跑 start_area。")
            return

        target.move_to(destination, quiet=True)
        if target == caller:
            caller.msg(f"你已通过测试传送抵达：{destination.key}。")
            return
        caller.msg(f"你已将 {target.key} 测试传送到：{destination.key}。")
        target.msg(f"[系统] 管理员已将你测试传送到：{destination.key}。")


class CmdTestAddMoney(Command):
    key = "测试加钱"
    aliases = ["testmoney", "加钱测试"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        if not raw:
            caller.msg("用法：|w测试加钱 数量|n 或 |w测试加钱 玩家名 数量|n。")
            return

        parts = raw.split()
        target = caller
        amount_raw = raw
        if len(parts) >= 2:
            try:
                int(parts[-1])
            except ValueError:
                caller.msg("测试加钱的数量必须是整数。")
                return
            if len(parts) > 1:
                amount_raw = parts[-1]
                if len(parts) > 1 and len(parts[:-1]) >= 1:
                    target_name = " ".join(parts[:-1]).strip()
                    if target_name:
                        target = _find_test_target(target_name)
                        if not target:
                            caller.msg("没有找到要加钱的目标玩家。")
                            return
        try:
            amount = int(amount_raw)
        except ValueError:
            caller.msg("测试加钱的数量必须是整数。")
            return
        if amount <= 0:
            caller.msg("测试加钱的数量必须大于 0。")
            return

        current = add_currency(target, amount)
        if target == caller:
            caller.msg(f"测试加钱完成：已增加 {amount} 铜钱。当前铜钱 {current}。")
            return
        caller.msg(f"测试加钱完成：已为 {target.key} 增加 {amount} 铜钱。对方当前铜钱 {current}。")
        target.msg(f"[系统] 管理员为你补发了 {amount} 铜钱。当前铜钱 {current}。")


class CmdTestChooseRoot(Command):
    key = "测试灵根"
    aliases = ["testroot", "devroot"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        if not raw:
            caller.msg("用法：|w测试灵根 <金|木|水|火|土>|n 或 |w测试灵根 玩家名 <金|木|水|火|土>|n。")
            return

        parts = raw.split()
        root_raw = parts[-1]
        root_key = normalize_root_choice(root_raw)
        if root_key not in ROOT_CHOICES:
            caller.msg("测试灵根只支持：金、木、水、火、土。")
            return

        target = caller
        if len(parts) > 1:
            target_name = " ".join(parts[:-1]).strip()
            if target_name:
                target = _find_test_target(target_name)
                if not target:
                    caller.msg("没有找到要测试灵根的目标玩家。")
                    return

        spirit_stone_room = _find_room_by_content_id("room_shengxian_platform")
        spirit_stone = _find_object_by_content_id("obj_spirit_stone_01")
        if not spirit_stone_room or not spirit_stone:
            caller.msg("测灵石或升仙台当前不存在。请先同步最新世界并重跑 start_area。")
            return

        target.move_to(spirit_stone_room, quiet=True)
        prepare_root_choice_state(target)
        reset_spiritual_root(target)
        result = trigger_object(target, spirit_stone, option=root_raw)
        if not result.get("ok"):
            caller.msg(result.get("text") or "测试灵根失败。")
            return

        root_label = result.get("root_label") or get_root_label(root_key, root_key)
        if target == caller:
            caller.msg(f"测试灵根完成：你已被传送至升仙台，并确认 {root_label}。")
            return
        caller.msg(f"测试灵根完成：已将 {target.key} 传送至升仙台，并确认 {root_label}。")
        target.msg(f"[系统] 管理员已将你传送至升仙台，并直接确认 {root_label}。")


class CmdTestResetRoot(Command):
    key = "测试重置灵根"
    aliases = ["resetroot", "testresetroot", "重置灵根"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        target = caller
        if raw:
            target = _find_test_target(raw)
            if not target:
                caller.msg("没有找到要重置灵根的目标玩家。")
                return

        spirit_stone_room = _find_room_by_content_id("room_shengxian_platform")
        if not spirit_stone_room:
            caller.msg("升仙台当前不存在。请先同步最新世界并重跑 start_area。")
            return

        target.move_to(spirit_stone_room, quiet=True)
        prepare_root_choice_state(target)
        reset_spiritual_root(target)
        if target == caller:
            caller.msg("测试重置灵根完成：你已恢复到升仙台测灵前的待选择状态。")
            return
        caller.msg(f"测试重置灵根完成：已将 {target.key} 恢复到升仙台测灵前的待选择状态。")
        target.msg("[系统] 管理员已将你恢复到升仙台测灵前的待选择状态。")


class CmdTestBattleRoom(Command):
    key = "测试战斗房"
    aliases = ["testbattle", "devbattle"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        target = caller
        if raw:
            target = _find_test_target(raw)
            if not target:
                caller.msg("没有找到要传送到测试战斗房的目标玩家。")
                return

        room = _find_room_by_content_id("room_ferry_battle_yard")
        if not room:
            caller.msg("试战木场当前不存在。请先同步世界并重跑 start_area。")
            return

        target.move_to(room, quiet=True)
        if target == caller:
            caller.msg("你已被传送至试战木场。")
            return
        caller.msg(f"你已将 {target.key} 传送至试战木场。")
        target.msg("[系统] 管理员已将你传送至试战木场。")


class CmdTestRefreshEnemy(Command):
    key = "测试刷新敌人"
    aliases = ["testenemy", "refreshenemy", "devenemy"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        if raw:
            enemy = _find_enemy_target(raw, caller.location)
            if not enemy:
                caller.msg("没有找到要刷新的测试敌人。可传入内容 id、enemy_id 或当前房间中的敌人名字。")
                return
            refreshed = [_refresh_enemy(enemy)]
        else:
            refreshed = []
            for obj in _get_room_objects(caller.location):
                if not is_enemy(obj):
                    continue
                refreshed.append(_refresh_enemy(obj))
            if not refreshed:
                caller.msg("当前房间没有可刷新的敌人。")
                return

        rows = [entry for entry in refreshed if entry]
        caller.msg("测试刷新敌人完成：\n" + "\n".join(f"- {entry}" for entry in rows))


class CmdTestResetBattle(Command):
    key = "测试重置战斗"
    aliases = ["resetbattle", "devresetbattle"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        target = caller
        if raw:
            target = _find_test_target(raw)
            if not target:
                caller.msg("没有找到要重置战斗状态的目标玩家。")
                return

        stats = get_stats(target)
        target.db.battle_id = None
        target.db.hp = stats["max_hp"]
        target.db.mp = stats["max_mp"]
        target.db.stamina = stats["max_stamina"]
        if target == caller:
            caller.msg("测试重置战斗完成：你的战斗状态、气血、灵力与体力已重置。")
            return
        caller.msg(f"测试重置战斗完成：已重置 {target.key} 的战斗状态。")
        target.msg("[系统] 管理员已重置你的战斗状态、气血、灵力与体力。")


class CmdTestSpawnBeast(Command):
    key = "测试生成妖兽"
    aliases = ["testbeast", "spawnbeast"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("你当前不在任何房间，无法生成测试敌人。")
            return

        enemy_id = self.args.strip() or "mist_ape"
        enemy = spawn_enemy_instance(enemy_id, location)
        if not enemy:
            caller.msg("没有找到对应的妖兽模板。")
            return
        caller.msg(f"测试生成妖兽完成：已在 {location.key} 生成 {enemy.key}。")


class CmdTestSpawnCultivatorEnemy(Command):
    key = "测试生成修士敌人"
    aliases = ["testcultivator", "spawncultivator"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("你当前不在任何房间，无法生成测试敌人。")
            return

        enemy_id = self.args.strip() or "battle_yard_renegade_disciple"
        enemy = spawn_enemy_instance(enemy_id, location)
        if not enemy:
            caller.msg("没有找到对应的修士敌人模板。")
            return
        caller.msg(f"测试生成修士敌人完成：已在 {location.key} 生成 {enemy.key}。")


class CmdTestForceBattle(Command):
    key = "测试强制开始战斗"
    aliases = ["forcebattle", "testforcebattle"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        room = caller.location
        if not room:
            caller.msg("你当前不在任何房间，无法开始测试战斗。")
            return

        raw = self.args.strip()
        if raw:
            enemy = _find_enemy_target(raw, room)
            if not enemy:
                caller.msg("没有找到要强制开战的目标敌人。")
                return
            targets = [enemy]
        else:
            targets = [obj for obj in _get_room_objects(room) if is_enemy(obj)]
            if not targets:
                caller.msg("当前房间没有可用于测试的敌人。")
                return

        result = start_battle(caller, targets, team_mode=True)
        if not result.get("ok"):
            caller.msg("测试强制开始战斗失败。")
            return
        battle = result.get("battle") or {}
        caller.msg(
            f"测试强制开始战斗完成：battle_id={battle.get('battle_id')}，"
            f"参战人数 {len(battle.get('participants') or [])}。"
        )


class CmdTestClearBattle(Command):
    key = "测试清空当前战斗"
    aliases = ["clearbattle", "testclearbattle"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        target = caller
        if raw:
            target = _find_test_target(raw)
            if not target:
                caller.msg("没有找到要清空战斗的目标玩家。")
                return

        snapshot = clear_battle(target, reset_players=True, reset_enemies=True)
        if not snapshot:
            target.db.battle_id = None
            stats = get_stats(target)
            target.db.hp = stats["max_hp"]
            target.db.mp = stats["max_mp"]
            target.db.stamina = stats["max_stamina"]
            if target == caller:
                caller.msg("当前没有 active battle，已直接重置你的战斗状态。")
                return
            caller.msg(f"{target.key} 当前没有 active battle，已直接重置其战斗状态。")
            target.msg("[系统] 管理员已直接重置你的战斗状态。")
            return

        if target == caller:
            caller.msg(f"测试清空当前战斗完成：已结束 {snapshot.get('battle_id')}。")
            return
        caller.msg(f"测试清空当前战斗完成：已结束 {target.key} 所在的战斗 {snapshot.get('battle_id')}。")
        target.msg("[系统] 管理员已清空你当前所在的战斗。")


class CmdTestBattleLog(Command):
    key = "测试战斗日志"
    aliases = ["battlelog", "testbattlelog"]
    locks = "cmd:perm(Admin)"
    help_category = "维护"

    def func(self):
        caller = self.caller
        raw = self.args.strip()
        target = caller
        if raw:
            target = _find_test_target(raw)
            if not target:
                caller.msg("没有找到要查看战斗日志的目标玩家。")
                return

        battle_id = getattr(getattr(target, "db", None), "battle_id", None)
        if not battle_id:
            caller.msg("目标当前没有处于战斗中。")
            return

        logs = get_battle_log(target, limit=10)
        if not logs:
            caller.msg(f"战斗 {battle_id} 当前还没有日志。")
            return

        lines = [f"战斗日志 {battle_id}:"]
        for index, entry in enumerate(logs, start=1):
            lines.append(_format_battle_log_entry(index, entry))
        caller.msg("\n".join(lines))


def _find_test_target(target_name):
    matches = evennia.search_object(target_name)
    if matches:
        return matches[0]
    matches = evennia.search_account(target_name)
    if matches:
        return getattr(matches[0].db, "_last_puppet", None)
    return None


def _find_room_by_content_id(content_id):
    return get_object_by_content_id(content_id)


def _find_object_by_content_id(content_id):
    return _find_room_by_content_id(content_id)


def _get_room_objects(room):
    if not room:
        return []
    contents = getattr(room, "contents", None)
    if contents is not None:
        return list(contents)
    contents_get = getattr(room, "contents_get", None)
    if callable(contents_get):
        return list(contents_get())
    return []


def _find_enemy_target(raw, room=None):
    direct = get_object_by_content_id(raw)
    if direct and is_enemy(direct):
        return direct
    room_objects = _get_room_objects(room)
    for obj in room_objects:
        if not is_enemy(obj):
            continue
        if getattr(obj.db, "enemy_id", None) == raw or obj.key == raw:
            return obj
    return None


def _refresh_enemy(enemy):
    enemy_id = getattr(enemy.db, "enemy_id", None) or getattr(enemy.db, "template_id", None)
    definition = get_enemy_definition(enemy_id)
    if not definition:
        return None
    enemy.db.battle_id = None
    sheet = ensure_enemy_model(enemy)
    enemy.db.max_hp = sheet["combat_stats"]["max_hp"]
    enemy.db.hp = sheet["combat_stats"]["max_hp"]
    enemy.db.combat_stats = {**sheet["combat_stats"], "hp": sheet["combat_stats"]["max_hp"]}
    return f"{enemy.key} -> HP {enemy.db.hp}/{enemy.db.max_hp}"


def _format_battle_log_entry(index, entry):
    actor_name = entry.get("actor_name", "未知")
    target_name = entry.get("target_name")
    value = entry.get("value", 0)
    card_id = entry.get("card_id")
    entry_type = entry.get("type")

    if entry_type == "basic_attack":
        return f"{index}. {actor_name} 对 {target_name} 造成 {value} 点伤害。"
    if entry_type == "use_combat_item":
        item_text = entry.get("text") or "使用了战斗物品"
        return f"{index}. {actor_name}{item_text}，效果值 {value}。"
    if entry_type == "skill_card":
        if target_name:
            return f"{index}. {actor_name} 使用 {card_id} 命中 {target_name}，效果值 {value}。"
        return f"{index}. {actor_name} 使用 {card_id}，效果值 {value}。"
    if entry_type == "guard":
        return f"{index}. {actor_name} 使用 {card_id or 'guard'}，获得 {value} 点护盾。"
    return f"{index}. {actor_name} 执行了 {entry_type or 'unknown'}。"
