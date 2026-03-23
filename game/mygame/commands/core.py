"""Core player-facing commands."""

import time

from evennia.utils import evtable

from .command import Command
from systems.areas import get_area_for_room
from systems.effect_executor import format_effect_result
from systems.help_content import get_newbie_content
from systems.items import get_inventory_items
from systems.player_stats import get_active_effect_text, get_stats
from systems.world_objects import (
    gather_from_object,
    get_readable_text,
    is_gatherable,
    is_readable,
    is_triggerable,
    trigger_object,
)


def get_target(caller, target_name):
    results = caller.search(target_name, location=caller.location, quiet=True)
    return results[0] if results else None


class CmdNewbie(Command):
    key = "新手"
    aliases = ["begin", "guide", "入门"]
    locks = "cmd:all()"
    help_category = "入门"

    def func(self):
        content = get_newbie_content()
        command_lines = [
            f"  |w{entry['command']}|n  {entry['description']}"
            for entry in content.get("recommended_commands", [])
        ]
        feature_lines = [f"- {entry}" for entry in content.get("completed_features", [])]
        self.caller.msg(
            f"{content['title']}\n\n"
            f"{content['intro']}\n\n"
            "你现在最推荐先试这些命令：\n"
            f"{chr(10).join(command_lines)}\n\n"
            "当前服务器已经完成：\n\n"
            f"{chr(10).join(feature_lines)}"
        )


class CmdStatus(Command):
    key = "状态"
    aliases = ["status", "stat", "属性"]
    locks = "cmd:all()"
    help_category = "角色"

    def func(self):
        caller = self.caller
        stats = get_stats(caller)
        location = caller.location.key if caller.location else "未知"
        area = get_area_for_room(caller.location)
        item_count = len(get_inventory_items(caller))

        table = evtable.EvTable(border="cells", pad_width=1)
        table.add_row("姓名", caller.key)
        table.add_row("境界", stats["realm"])
        table.add_row("气血", f"{stats['hp']}/{stats['max_hp']}")
        table.add_row("体力", f"{stats['stamina']}/{stats['max_stamina']}")
        table.add_row("修为", str(stats["exp"]))
        table.add_row("铜钱", str(stats["copper"]))
        table.add_row("区域", area["key"] if area else "未划分")
        table.add_row("位置", location)
        table.add_row("效果", get_active_effect_text(caller))
        table.add_row("背包", f"{item_count} 件")
        self.caller.msg("|g角色状态|n\n%s" % table)


class CmdRead(Command):
    key = "阅读"
    aliases = ["read", "查看告示", "读"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想阅读什么？用法：|w阅读 渡口告示牌|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_readable(target):
            caller.msg(f"{target.key} 上并没有什么可读的内容。")
            return
        caller.msg(get_readable_text(caller, target))


class CmdGather(Command):
    key = "采集"
    aliases = ["gather", "采药", "收集"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想采集什么？用法：|w采集 松纹草丛|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_gatherable(target):
            caller.msg(f"{target.key} 看起来并不适合采集。")
            return
        result = gather_from_object(caller, target)
        if not result["ok"]:
            caller.msg(result["text"])
            return
        caller.msg(
            f"{result['text']}\n"
            f"|g采集收获|n: 获得 |w{result['item'].key}|n，体力 -{result['cost']}\n"
            f"|g当前体力|n: {result['stamina_now']}/{result['max_stamina']}"
        )


class CmdTrigger(Command):
    key = "触发"
    aliases = ["trigger", "激活", "touch"]
    locks = "cmd:all()"
    help_category = "交互"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("你想触发什么？用法：|w触发 回渡石|n")
            return
        target = get_target(caller, self.args.strip())
        if not target:
            caller.msg("你没有在附近看到这个目标。")
            return
        if not is_triggerable(target):
            caller.msg(f"{target.key} 看起来并不会回应你的触碰。")
            return
        result = trigger_object(caller, target)
        if not result["ok"]:
            caller.msg(result["text"])
            return
        if result.get("effect"):
            remaining = max(0, int(result["effect"]["expires_at"] - time.time()))
            caller.msg(
                f"{result['text']}\n"
                f"|g当前效果|n: {result['effect']['label']}，持续约 {remaining} 秒"
            )
            return
        if "hp_gain" in result or "stamina_gain" in result:
            caller.msg(format_effect_result(result, "恢复结果"))
            return
        caller.msg(result["text"])
