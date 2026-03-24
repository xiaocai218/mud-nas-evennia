"""Minimal team commands."""

from .command import Command
from systems.teams import (
    accept_team_invite,
    create_team,
    invite_to_team,
    leave_team,
    list_team_status,
    reject_team_invite,
)


TEAM_ERROR_MESSAGES = {
    "team_not_joined": "你当前还没有加入队伍。",
    "already_in_team": "你已经在队伍中，不能重复执行这个操作。",
    "not_team_leader": "只有队长可以发起邀请。",
    "target_not_found": "没有找到你要邀请的玩家。",
    "target_is_self": "不能邀请自己加入队伍。",
    "target_already_in_team": "目标已经在其他队伍中。",
    "invite_not_found": "没有找到可接受的组队邀请。",
    "invite_expired": "当前没有有效的组队邀请，旧邀请可能已经过期。",
    "team_not_found": "这条邀请对应的队伍已经不存在了。",
}


def _render_team_error(caller, result):
    caller.msg(TEAM_ERROR_MESSAGES.get(result.get("reason"), "队伍操作失败。"))


def _format_pending_invites(result):
    invites = result.get("pending_invites") or []
    if not invites:
        return ""
    rows = ["待处理邀请："]
    for invite in invites:
        ttl_minutes = max(1, invite["expires_in"] // 60) if invite["expires_in"] else 0
        rows.append(
            f"- {invite['leader_name']} 邀请你加入“{invite['team_name']}”"
            f"（约剩 {ttl_minutes} 分钟）"
        )
    if result.get("expired_invites_count"):
        rows.append(f"- 已自动清理过期邀请 {result['expired_invites_count']} 条")
    return "\n" + "\n".join(rows)


def _send_team_action_or_error(caller, action, *args):
    result = action(caller, *args)
    if not result["ok"]:
        _render_team_error(caller, result)
    return result


class CmdTeamStatus(Command):
    key = "组队"
    aliases = ["teaminfo", "队伍信息"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        result = list_team_status(self.caller)
        if not result["ok"]:
            invite_count = len(result.get("pending_invites") or [])
            extra = ""
            if invite_count:
                extra = f" 当前有 {invite_count} 条待处理邀请，可用 接受邀请 或 拒绝邀请。"
            if result.get("expired_invites_count"):
                extra += f" 已自动清理过期邀请 {result['expired_invites_count']} 条。"
            self.caller.msg(
                "你当前还没有加入队伍。可用命令：建队、邀请、接受邀请、拒绝邀请、离队。"
                + extra
                + _format_pending_invites(result)
            )
            return
        team = result["team"]
        rows = []
        for member in team["members"]:
            parts = [member["name"]]
            if member["leader"]:
                parts.append("队长")
            parts.append("在线" if member["online"] else "离线")
            rows.append(f"- {' / '.join(parts)}")
        self.caller.msg(
            f"当前队伍：{team['name']}\n"
            f"队长：{team['leader_name']}\n"
            f"待处理邀请：{len(result.get('pending_invites') or [])}\n"
            f"成员：\n" + "\n".join(rows)
        )


class CmdListTeamInvites(Command):
    key = "邀请列表"
    aliases = ["队伍邀请", "teaminvites"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        result = list_team_status(self.caller)
        invites = result.get("pending_invites") or []
        if not invites:
            expired = result.get("expired_invites_count") or 0
            suffix = f" 已自动清理过期邀请 {expired} 条。" if expired else ""
            self.caller.msg("当前没有待处理的组队邀请。" + suffix)
            return
        self.caller.msg("当前可处理的组队邀请：" + _format_pending_invites(result))


class CmdCreateTeam(Command):
    key = "建队"
    aliases = ["创建队伍", "createteam"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_team_action_or_error(self.caller, create_team, self.args.strip())


class CmdInviteTeam(Command):
    key = "邀请"
    aliases = ["invite"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        target = self.args.strip()
        if not target:
            self.caller.msg("用法：邀请 玩家名")
            return
        _send_team_action_or_error(self.caller, invite_to_team, target)


class CmdAcceptTeamInvite(Command):
    key = "接受邀请"
    aliases = ["接受组队", "acceptinvite"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_team_action_or_error(self.caller, accept_team_invite, self.args.strip() or None)


class CmdRejectTeamInvite(Command):
    key = "拒绝邀请"
    aliases = ["拒绝组队", "rejectinvite"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_team_action_or_error(self.caller, reject_team_invite, self.args.strip() or None)


class CmdLeaveTeam(Command):
    key = "离队"
    aliases = ["退出队伍", "leaveteam"]
    locks = "cmd:all()"
    help_category = "社交"

    def func(self):
        _send_team_action_or_error(self.caller, leave_team)
