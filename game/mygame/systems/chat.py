"""Realtime chat helpers built on top of Evennia channels."""

import time

import evennia
from evennia.comms.comms import DefaultChannel
from evennia.accounts.models import AccountDB

from systems.chat_payloads import serialize_chat_message
from systems.event_bus import chat_message_event, enqueue_account_event


CHANNEL_WORLD = "world"
CHANNEL_TEAM = "team"
CHANNEL_SYSTEM = "system"

CHANNEL_CONFIG = {
    CHANNEL_WORLD: {
        "db_key": "chat_world",
        "legacy_names": ["世界", "world"],
        "key": "世界",
        "desc": "九州群修世界频道",
        "mutable": True,
        "user_sendable": True,
    },
    CHANNEL_TEAM: {
        "db_key": "chat_team",
        "legacy_names": ["队伍", "team"],
        "key": "队伍",
        "desc": "九州群修队伍频道",
        "mutable": True,
        "user_sendable": True,
    },
    CHANNEL_SYSTEM: {
        "db_key": "chat_system",
        "legacy_names": ["系统", "system"],
        "key": "系统",
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

MANAGED_CHANNEL_ALIASES = {
    "世界",
    "world",
    "队伍",
    "team",
    "系统",
    "system",
    "chat_world",
    "chat_team",
    "chat_system",
}


def get_channel_lockstring(channel_name):
    if channel_name == CHANNEL_SYSTEM:
        return "send:false();listen:all();control:perm(Admin)"
    return "send:all();listen:all();control:perm(Admin)"


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
    channel.mute(account)
    return {"ok": True, "channel": config["key"]}


def unmute_channel(caller, raw_name):
    account = _get_account(caller)
    channel_name = resolve_channel_name(raw_name)
    if not channel_name:
        return {"ok": False, "reason": "channel_not_found"}
    config = CHANNEL_CONFIG[channel_name]
    channel = _ensure_channel(channel_name)
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

    delivered = _deliver_chat_event(_unique_accounts([sender_account, target_account]), formatted, event)

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
        recipients = _get_online_accounts()

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

    delivered = _deliver_chat_event(recipients, formatted, event, muted_accounts=channel.mutelist)

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


def ensure_all_channels():
    for channel_name in CHANNEL_CONFIG:
        _ensure_channel(channel_name)


def cleanup_managed_channel_nicks(accounts=None):
    if accounts is None:
        accounts = AccountDB.objects.all()
    for account in accounts:
        for alias in MANAGED_CHANNEL_ALIASES:
            DefaultChannel.remove_user_channel_alias(account, alias)


def _send_channel_message(channel_name, caller, text):
    available, reason = _channel_available(caller, channel_name)
    if not available:
        return {"ok": False, "reason": reason}

    channel = _ensure_channel(channel_name)
    if channel_name == CHANNEL_TEAM:
        recipients = _get_team_accounts(caller)
    else:
        recipients = _get_online_accounts()

    ts = int(time.time())
    dto = serialize_chat_message(channel=channel_name, text=text, sender=caller, target=None, ts=ts)
    event = chat_message_event(dto)
    label = CHANNEL_CONFIG[channel_name]["key"]
    formatted = f"[{label}] {caller.key}: {text}"

    delivered = _deliver_chat_event(recipients, formatted, event, muted_accounts=channel.mutelist)

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
    matches = evennia.search_channel(config["db_key"])
    if matches:
        channel = matches[0]
        _apply_channel_configuration(channel, channel_name)
        return channel
    for legacy_name in config.get("legacy_names", []):
        matches = evennia.search_channel(legacy_name)
        if matches:
            channel = matches[0]
            _normalize_channel_identity(channel, channel_name)
            _apply_channel_configuration(channel, channel_name)
            return channel
    channel = evennia.create_channel(
        key=config["db_key"],
        aliases=[],
        desc=config.get("desc", ""),
        locks=get_channel_lockstring(channel_name),
    )
    _apply_channel_configuration(channel, channel_name)
    return channel


def _apply_channel_configuration(channel, channel_name):
    locks = getattr(channel, "locks", None)
    if locks and hasattr(locks, "add"):
        locks.add(get_channel_lockstring(channel_name))


def _normalize_channel_identity(channel, channel_name):
    config = CHANNEL_CONFIG[channel_name]
    desired_key = config["db_key"]
    if getattr(channel, "db_key", None) != desired_key:
        channel.db_key = desired_key
        channel.save(update_fields=["db_key"])
    aliases = getattr(channel, "aliases", None)
    if aliases and hasattr(aliases, "clear"):
        aliases.clear()


def _deliver_chat_event(accounts, formatted, event, muted_accounts=None):
    delivered = 0
    muted = set(muted_accounts or [])
    for account in accounts:
        if account in muted:
            continue
        account.msg(formatted)
        enqueue_account_event(account, event)
        delivered += 1
    return delivered


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
