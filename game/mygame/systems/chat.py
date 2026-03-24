"""Realtime chat helpers built on top of Evennia channels."""

import time

import evennia

from systems.chat_payloads import serialize_chat_message
from systems.event_bus import chat_message_event, enqueue_account_event


CHANNEL_WORLD = "world"
CHANNEL_TEAM = "team"
CHANNEL_SYSTEM = "system"

CHANNEL_CONFIG = {
    CHANNEL_WORLD: {
        "key": "世界",
        "aliases": ["world"],
        "desc": "九州群修世界频道",
        "mutable": True,
        "user_sendable": True,
    },
    CHANNEL_TEAM: {
        "key": "队伍",
        "aliases": ["team"],
        "desc": "九州群修队伍频道",
        "mutable": True,
        "user_sendable": True,
    },
    CHANNEL_SYSTEM: {
        "key": "系统",
        "aliases": ["system"],
        "desc": "九州群修系统频道",
        "mutable": True,
        "user_sendable": False,
    },
}

CHANNEL_INPUTS = {
    "世界": CHANNEL_WORLD,
    "world": CHANNEL_WORLD,
    "队伍": CHANNEL_TEAM,
    "team": CHANNEL_TEAM,
    "系统": CHANNEL_SYSTEM,
    "system": CHANNEL_SYSTEM,
}


def get_channel_definition(channel_name):
    return CHANNEL_CONFIG.get(channel_name)


def resolve_channel_name(raw_name):
    if not raw_name:
        return None
    value = str(raw_name).strip()
    return CHANNEL_INPUTS.get(value.lower()) or CHANNEL_INPUTS.get(value)


def list_channel_status(caller):
    account = _get_account(caller)
    statuses = []
    for channel_name, config in CHANNEL_CONFIG.items():
        channel = _ensure_channel(channel_name)
        if channel_name in {CHANNEL_WORLD, CHANNEL_SYSTEM}:
            _sync_online_subscribers(channel_name)
        available, reason = _channel_available(caller, channel_name)
        statuses.append(
            {
                "channel": channel_name,
                "key": config["key"],
                "desc": config["desc"],
                "muted": bool(account and account in channel.mutelist),
                "available": available,
                "reason": reason,
            }
        )
    statuses.append(
        {
            "channel": "private",
            "key": "私聊",
            "desc": "玩家间定向实时私聊",
            "muted": False,
            "available": True,
            "reason": None,
        }
    )
    return statuses


def mute_channel(caller, raw_name):
    account = _get_account(caller)
    channel_name = resolve_channel_name(raw_name)
    if not channel_name:
        return {"ok": False, "reason": "channel_not_found"}
    config = CHANNEL_CONFIG[channel_name]
    if not config.get("mutable", True):
        return {"ok": False, "reason": "channel_not_mutable"}
    channel = _ensure_channel(channel_name)
    _sync_channel_subscriber(channel, account)
    channel.mute(account)
    return {"ok": True, "channel": config["key"]}


def unmute_channel(caller, raw_name):
    account = _get_account(caller)
    channel_name = resolve_channel_name(raw_name)
    if not channel_name:
        return {"ok": False, "reason": "channel_not_found"}
    config = CHANNEL_CONFIG[channel_name]
    channel = _ensure_channel(channel_name)
    _sync_channel_subscriber(channel, account)
    channel.unmute(account)
    return {"ok": True, "channel": config["key"]}


def send_world_message(caller, text):
    if not (text or "").strip():
        return {"ok": False, "reason": "empty_message"}
    return _send_channel_message(CHANNEL_WORLD, caller, text)


def send_team_message(caller, text):
    if not (text or "").strip():
        return {"ok": False, "reason": "empty_message"}
    return _send_channel_message(CHANNEL_TEAM, caller, text)


def send_private_message(caller, target_name, text):
    if not (text or "").strip():
        return {"ok": False, "reason": "empty_message"}
    target_character = _find_target_character(target_name)
    if not target_character:
        return {"ok": False, "reason": "target_not_found"}

    sender_account = _get_account(caller)
    target_account = _get_account(target_character)
    if not sender_account or not target_account:
        return {"ok": False, "reason": "target_not_found"}

    ts = int(time.time())
    dto = serialize_chat_message(
        channel="private",
        text=text,
        sender=caller,
        target=target_character,
        ts=ts,
    )
    event = chat_message_event(dto)
    formatted = f"[私聊] {caller.key} -> {target_character.key}: {text}"

    delivered = 0
    for account in _unique_accounts([sender_account, target_account]):
        account.msg(formatted)
        enqueue_account_event(account, event)
        delivered += 1

    return {
        "ok": True,
        "channel": "私聊",
        "message": dto,
        "event": event,
        "delivered": delivered,
        "text": formatted,
    }


def send_system_message(message, recipients=None, code=None, level="info"):
    channel = _ensure_channel(CHANNEL_SYSTEM)
    recipients = _resolve_system_recipients(recipients)
    if not recipients:
        recipients = _sync_online_subscribers(CHANNEL_SYSTEM)

    ts = int(time.time())
    dto = serialize_chat_message(
        channel=CHANNEL_SYSTEM,
        text=message,
        sender=None,
        target=None,
        ts=ts,
        extra={"level": level, "code": code},
    )
    event = chat_message_event(dto)
    formatted = f"[系统] {message}"

    delivered = 0
    for account in recipients:
        _sync_channel_subscriber(channel, account)
        if account in channel.mutelist:
            continue
        account.msg(formatted)
        enqueue_account_event(account, event)
        delivered += 1

    return {
        "ok": True,
        "channel": "系统",
        "message": dto,
        "event": event,
        "delivered": delivered,
        "text": formatted,
    }


def notify_player(recipient, message, code=None, level="info"):
    return send_system_message(message, recipients=[recipient], code=code, level=level)


def _send_channel_message(channel_name, caller, text):
    available, reason = _channel_available(caller, channel_name)
    if not available:
        return {"ok": False, "reason": reason}

    channel = _ensure_channel(channel_name)
    if channel_name in {CHANNEL_WORLD, CHANNEL_SYSTEM}:
        recipients = _sync_online_subscribers(channel_name)
    elif channel_name == CHANNEL_TEAM:
        recipients = _get_team_accounts(caller)
    else:
        recipients = []

    ts = int(time.time())
    dto = serialize_chat_message(channel=channel_name, text=text, sender=caller, target=None, ts=ts)
    event = chat_message_event(dto)
    label = CHANNEL_CONFIG[channel_name]["key"]
    formatted = f"[{label}] {caller.key}: {text}"

    delivered = 0
    for account in recipients:
        _sync_channel_subscriber(channel, account)
        if account in channel.mutelist:
            continue
        account.msg(formatted)
        enqueue_account_event(account, event)
        delivered += 1

    return {
        "ok": True,
        "channel": label,
        "message": dto,
        "event": event,
        "delivered": delivered,
        "text": formatted,
    }


def _channel_available(caller, channel_name):
    if channel_name == CHANNEL_TEAM:
        if not getattr(getattr(caller, "db", None), "team_id", None):
            return False, "team_not_joined"
    return True, None


def _ensure_channel(channel_name):
    config = CHANNEL_CONFIG[channel_name]
    matches = evennia.search_channel(config["key"])
    if matches:
        return matches[0]
    for alias in config.get("aliases", []):
        matches = evennia.search_channel(alias)
        if matches:
            return matches[0]
    return evennia.create_channel(
        key=config["key"],
        aliases=config.get("aliases", []),
        desc=config.get("desc", ""),
        locks="send:all();listen:all();control:perm(Admin)",
    )


def _sync_online_subscribers(channel_name):
    channel = _ensure_channel(channel_name)
    accounts = _get_online_accounts()
    for account in accounts:
        _sync_channel_subscriber(channel, account)
    return accounts


def _sync_channel_subscriber(channel, account):
    if account and not channel.has_connection(account):
        channel.connect(account)


def _get_online_accounts():
    accounts = []
    for session in evennia.SESSION_HANDLER.get_sessions():
        account = getattr(session, "account", None)
        if account:
            accounts.append(account)
    return _unique_accounts(accounts)


def _get_team_accounts(caller):
    team_id = getattr(getattr(caller, "db", None), "team_id", None)
    if not team_id:
        return []

    accounts = []
    for session in evennia.SESSION_HANDLER.get_sessions():
        account = getattr(session, "account", None)
        puppet = getattr(session, "puppet", None)
        if puppet and getattr(getattr(puppet, "db", None), "team_id", None) == team_id and account:
            accounts.append(account)
    return _unique_accounts(accounts)


def _resolve_system_recipients(recipients):
    if not recipients:
        return []
    resolved = []
    for entry in recipients:
        account = _get_account(entry)
        if account:
            resolved.append(account)
    return _unique_accounts(resolved)


def _find_target_character(target_name):
    matches = evennia.search_object(target_name)
    if matches:
        return matches[0]
    matches = evennia.search_account(target_name)
    if matches:
        account = matches[0]
        last_puppet = getattr(getattr(account, "db", None), "_last_puppet", None)
        if last_puppet:
            return last_puppet
    return None


def _get_account(entity):
    if not entity:
        return None
    if hasattr(entity, "username") and getattr(entity, "is_authenticated", True):
        return entity
    return getattr(entity, "account", None)


def _unique_accounts(accounts):
    unique = []
    seen = set()
    for account in accounts:
        identifier = getattr(account, "pk", None) or id(account)
        if identifier in seen:
            continue
        seen.add(identifier)
        unique.append(account)
    return unique
