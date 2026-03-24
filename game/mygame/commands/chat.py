"""Realtime chat commands."""

from .command import Command
from systems.chat import (
    list_channel_status,
    mute_channel,
    send_private_message,
    send_team_message,
    send_world_message,
    unmute_channel,
)


def _render_chat_result(caller, result, fallback):
    if not result.get("ok"):
        reason = result.get("reason")
        if reason == "team_not_joined":
            caller.msg("你当前没有加入队伍，暂时不能使用队伍频道。")
            return
        if reason == "target_not_found":
            caller.msg("没有找到你要私聊的玩家。")
            return
        caller.msg(fallback)
        return


class CmdWorldChat(Command):
    key = "世界"
    aliases = ["world"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        text = self.args.strip()
        if not text:
            self.caller.msg("你想在世界频道说什么？用法：|w世界 大家好|n")
            return
        _render_chat_result(self.caller, send_world_message(self.caller, text), "世界频道发送失败。")


class CmdTeamChat(Command):
    key = "队伍"
    aliases = ["team"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        text = self.args.strip()
        if not text:
            self.caller.msg("你想在队伍频道说什么？用法：|w队伍 集合到村口|n")
            return
        _render_chat_result(self.caller, send_team_message(self.caller, text), "队伍频道发送失败。")


class CmdPrivateChat(Command):
    key = "私聊"
    aliases = ["tell", "msg", "whisperto"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        parts = self.args.strip().split(None, 1)
        if len(parts) < 2:
            self.caller.msg("用法：|w私聊 玩家名 你好|n")
            return
        target_name, text = parts
        _render_chat_result(
            self.caller,
            send_private_message(self.caller, target_name, text.strip()),
            "私聊发送失败。",
        )


class CmdChannels(Command):
    key = "频道"
    aliases = ["channels", "channel"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        rows = []
        for entry in list_channel_status(self.caller):
            status = "可用" if entry["available"] else "不可用"
            if entry["muted"]:
                status += " / 已静音"
            if entry["reason"] == "team_not_joined":
                status += "（未加入队伍）"
            rows.append(f"- {entry['key']}: {entry['desc']} [{status}]")
        self.caller.msg("当前频道：\n" + "\n".join(rows))


class CmdMuteChannel(Command):
    key = "静音"
    aliases = ["mute"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        channel_name = self.args.strip()
        if not channel_name:
            self.caller.msg("用法：|w静音 世界|n")
            return
        result = mute_channel(self.caller, channel_name)
        if not result["ok"]:
            self.caller.msg("没有这个可静音的频道。可用频道：世界、队伍、系统。")
            return
        self.caller.msg(f"你已静音频道：|w{result['channel']}|n。")


class CmdUnmuteChannel(Command):
    key = "取消静音"
    aliases = ["unmute"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 1

    def func(self):
        channel_name = self.args.strip()
        if not channel_name:
            self.caller.msg("用法：|w取消静音 世界|n")
            return
        result = unmute_channel(self.caller, channel_name)
        if not result["ok"]:
            self.caller.msg("没有这个可取消静音的频道。可用频道：世界、队伍、系统。")
            return
        self.caller.msg(f"你已恢复接收频道：|w{result['channel']}|n。")


class CmdSystemChannel(Command):
    key = "系统"
    aliases = ["system"]
    locks = "cmd:all()"
    help_category = "社交"
    priority = 2

    def func(self):
        self.caller.msg("系统频道为只读。可输入 |w频道|n 查看当前可用频道，系统消息会自动推送。")
