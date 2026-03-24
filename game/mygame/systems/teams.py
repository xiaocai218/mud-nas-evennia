"""Minimal persistent team system for text gameplay."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import evennia
from evennia.server.models import ServerConfig

from .chat import notify_player, send_system_message


TEAM_REGISTRY_KEY = "prototype_teams"
INVITE_TTL_SECONDS = 1800


def list_team_status(caller):
    team = get_team_snapshot(caller)
    if not team:
        invites = _active_invites(caller)
        return {"ok": False, "reason": "team_not_joined", "pending_invites": len(invites)}
    return {"ok": True, "team": team, "pending_invites": len(_active_invites(caller))}


def create_team(caller, name=None):
    if _get_team_id(caller):
        return {"ok": False, "reason": "already_in_team"}

    team_id = f"team_{int(time.time())}_{_get_character_id(caller)}"
    team_name = (name or "").strip() or f"{caller.key}的小队"
    registry = _load_registry()
    registry[team_id] = {
        "id": team_id,
        "name": team_name,
        "leader_id": _get_character_id(caller),
        "leader_name": caller.key,
        "members": [{"id": _get_character_id(caller), "name": caller.key}],
        "created_at": int(time.time()),
    }
    _save_registry(registry)
    _set_team_membership(caller, team_id, team_name, role="leader")
    _clear_invites(caller)
    notify_player(caller, f"已创建队伍：{team_name}。", code="team_created")
    return {"ok": True, "team": registry[team_id]}


def invite_to_team(caller, target_name):
    team = _require_leader_team(caller)
    if not team["ok"]:
        return team

    target = _find_target_character(target_name)
    if not target:
        return {"ok": False, "reason": "target_not_found"}
    if target == caller:
        return {"ok": False, "reason": "target_is_self"}
    if _get_team_id(target):
        return {"ok": False, "reason": "target_already_in_team"}

    invites = _active_invites(target)
    invite = {
        "team_id": team["team"]["id"],
        "team_name": team["team"]["name"],
        "leader_id": _get_character_id(caller),
        "leader_name": caller.key,
        "expires_at": int(time.time()) + INVITE_TTL_SECONDS,
    }
    invites = [entry for entry in invites if entry["team_id"] != invite["team_id"]]
    invites.append(invite)
    target.db.team_invites = invites
    notify_player(
        caller,
        f"已向 {target.key} 发出组队邀请。",
        code="team_invite_sent",
    )
    notify_player(
        target,
        f"{caller.key} 邀请你加入队伍“{team['team']['name']}”。可输入 接受邀请 {caller.key}。",
        code="team_invite_received",
    )
    return {"ok": True, "team": team["team"], "target": target.key}


def accept_team_invite(caller, leader_name=None):
    if _get_team_id(caller):
        return {"ok": False, "reason": "already_in_team"}

    invites, expired_count = _split_invites(caller)
    if not invites:
        reason = "invite_expired" if expired_count else "invite_not_found"
        return {"ok": False, "reason": reason}

    invite = _select_invite(invites, leader_name)
    if not invite:
        return {"ok": False, "reason": "invite_not_found"}

    registry = _load_registry()
    team = registry.get(invite["team_id"])
    if not team:
        caller.db.team_invites = [entry for entry in invites if entry["team_id"] != invite["team_id"]]
        return {"ok": False, "reason": "team_not_found"}

    member_id = _get_character_id(caller)
    if not any(entry["id"] == member_id for entry in team["members"]):
        team["members"].append({"id": member_id, "name": caller.key})
    registry[team["id"]] = team
    _save_registry(registry)

    _set_team_membership(caller, team["id"], team["name"], role="member")
    caller.db.team_invites = [entry for entry in invites if entry["team_id"] != invite["team_id"]]

    send_system_message(
        f"{caller.key} 已加入队伍“{team['name']}”。",
        recipients=_get_team_member_characters(team["id"]),
        code="team_joined",
    )
    return {"ok": True, "team": team}


def reject_team_invite(caller, leader_name=None):
    if _get_team_id(caller):
        return {"ok": False, "reason": "already_in_team"}

    invites, expired_count = _split_invites(caller)
    if not invites:
        reason = "invite_expired" if expired_count else "invite_not_found"
        return {"ok": False, "reason": reason}

    invite = _select_invite(invites, leader_name)
    if not invite:
        return {"ok": False, "reason": "invite_not_found"}

    caller.db.team_invites = [entry for entry in invites if entry["team_id"] != invite["team_id"]]
    leader = _get_character_by_id(invite["leader_id"])
    if leader:
        notify_player(
            leader,
            f"{caller.key} 拒绝了加入队伍“{invite['team_name']}”的邀请。",
            code="team_invite_declined",
        )
    notify_player(
        caller,
        f"你已拒绝来自 {invite['leader_name']} 的组队邀请。",
        code="team_invite_rejected",
    )
    return {"ok": True, "leader_name": invite["leader_name"], "team_name": invite["team_name"]}


def leave_team(caller):
    team_id = _get_team_id(caller)
    if not team_id:
        return {"ok": False, "reason": "team_not_joined"}

    registry = _load_registry()
    team = registry.get(team_id)
    if not team:
        _clear_team_membership(caller)
        return {"ok": True, "disbanded": False}

    member_id = _get_character_id(caller)
    is_leader = team.get("leader_id") == member_id
    team["members"] = [entry for entry in team["members"] if entry["id"] != member_id]
    _clear_team_membership(caller)

    remaining_members = _get_team_member_characters(team_id, member_entries=team["members"])
    if not team["members"]:
        registry.pop(team_id, None)
        _save_registry(registry)
        notify_player(caller, f"你离开了队伍“{team['name']}”，队伍已解散。", code="team_disbanded")
        return {"ok": True, "disbanded": True}

    if is_leader:
        new_leader = team["members"][0]
        team["leader_id"] = new_leader["id"]
        team["leader_name"] = new_leader["name"]
        new_leader_obj = _get_character_by_id(new_leader["id"])
        if new_leader_obj:
            new_leader_obj.db.team_role = "leader"
        leader_notice = f"{caller.key} 离队，{new_leader['name']} 成为新的队长。"
    else:
        leader_notice = f"{caller.key} 离开了队伍“{team['name']}”。"

    registry[team_id] = team
    _save_registry(registry)
    send_system_message(leader_notice, recipients=remaining_members, code="team_member_left")
    notify_player(caller, f"你已离开队伍“{team['name']}”。", code="team_left")
    return {"ok": True, "disbanded": False, "team": team}


def get_team_snapshot(caller):
    team_id = _get_team_id(caller)
    if not team_id:
        return None
    team = _load_registry().get(team_id)
    if not team:
        return None
    members = []
    online_member_ids = {_get_character_id(obj) for obj in _get_team_member_characters(team_id)}
    for entry in team["members"]:
        member = dict(entry)
        member["online"] = entry["id"] in online_member_ids
        member["leader"] = entry["id"] == team["leader_id"]
        members.append(member)
    return {
        "id": team["id"],
        "name": team["name"],
        "leader_id": team["leader_id"],
        "leader_name": team["leader_name"],
        "members": members,
    }


def _require_leader_team(caller):
    team = get_team_snapshot(caller)
    if not team:
        return {"ok": False, "reason": "team_not_joined"}
    if team["leader_id"] != _get_character_id(caller):
        return {"ok": False, "reason": "not_team_leader"}
    return {"ok": True, "team": team}


def _load_registry() -> Dict[str, dict]:
    return ServerConfig.objects.conf(TEAM_REGISTRY_KEY, default=dict) or {}


def _save_registry(registry):
    ServerConfig.objects.conf(TEAM_REGISTRY_KEY, value=registry)


def _active_invites(caller) -> List[dict]:
    invites = list(getattr(caller.db, "team_invites", []) or [])
    now = int(time.time())
    filtered = [entry for entry in invites if entry.get("expires_at", 0) > now]
    if filtered != invites:
        caller.db.team_invites = filtered
    return filtered


def _split_invites(caller):
    invites = list(getattr(caller.db, "team_invites", []) or [])
    now = int(time.time())
    active = [entry for entry in invites if entry.get("expires_at", 0) > now]
    expired_count = len(invites) - len(active)
    if active != invites:
        caller.db.team_invites = active
    return active, expired_count


def _select_invite(invites, leader_name):
    if not leader_name:
        return invites[0]
    normalized = leader_name.strip().lower()
    for invite in invites:
        if invite.get("leader_name", "").lower() == normalized:
            return invite
    return None


def _find_target_character(target_name):
    matches = evennia.search_object(target_name)
    if matches:
        return matches[0]
    matches = evennia.search_account(target_name)
    if matches:
        return getattr(matches[0].db, "_last_puppet", None)
    return None


def _get_team_id(caller):
    return getattr(getattr(caller, "db", None), "team_id", None)


def _set_team_membership(caller, team_id, team_name, role):
    caller.db.team_id = team_id
    caller.db.team_name = team_name
    caller.db.team_role = role


def _clear_team_membership(caller):
    caller.db.team_id = None
    caller.db.team_name = None
    caller.db.team_role = None


def _clear_invites(caller):
    caller.db.team_invites = []


def _get_character_id(caller):
    return getattr(caller, "id", None) or getattr(caller, "pk", None)


def _get_character_by_id(character_id):
    matches = evennia.search_object(f"#{character_id}")
    return matches[0] if matches else None


def _get_team_member_characters(team_id, member_entries=None):
    registry = _load_registry()
    team = registry.get(team_id)
    members = member_entries if member_entries is not None else (team or {}).get("members", [])
    characters = []
    for entry in members:
        character = _get_character_by_id(entry["id"])
        if character:
            characters.append(character)
    return characters
