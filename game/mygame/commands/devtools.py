"""Developer/admin maintenance commands."""

from evennia.utils import evtable

from .command import Command
from systems.content_loader import (
    find_content_record,
    get_content_summary,
    list_content_names,
    reload_content,
)


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

        caller.msg("可用子命令：|w重载|n、|w查看|n")
