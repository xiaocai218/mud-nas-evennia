"""Developer/admin maintenance commands."""

import evennia
from evennia.utils import evtable

from .command import Command
from systems.character_model import ROOT_CHOICES, get_root_label, normalize_root_choice, reset_spiritual_root
from systems.content_loader import (
    find_content_record,
    get_content_summary,
    list_content_names,
    reload_content,
    validate_content,
)
from systems.object_index import get_object_by_content_id
from systems.player_stats import add_currency
from systems.quests import ROOT_CHOICE_READY, prepare_root_choice_state
from systems.world_objects import trigger_object

TEST_DESTINATIONS = {
    "坊市": "room_qingyun_outer_market",
    "外门坊市": "room_qingyun_outer_market",
    "外门": "room_qingyun_outer_court",
    "青云外门": "room_qingyun_outer_court",
    "升仙台": "room_shengxian_platform",
    "测灵石": "room_shengxian_platform",
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
