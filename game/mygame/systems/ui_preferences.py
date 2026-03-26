"""Terminal/webclient UI preference helpers."""

from django.conf import settings


DEFAULT_CHAT_LAYOUT = {
    "dock": "right-sidebar",
    "size": "normal",
    "visible": True,
    "active_channel": "aggregate",
}

_VALID_DOCKS = {"right-sidebar", "top-strip", "bottom-strip"}
_VALID_SIZES = {"compact", "normal", "large"}
_VALID_CHANNELS = {"aggregate", "world", "team", "private", "system"}

_OPTION_FIELD_MAP = {
    "dock": "chatDockPreset",
    "size": "chatPaneSize",
    "visible": "chatPaneVisible",
    "active_channel": "chatActiveChannel",
}


def get_ui_preferences(caller_or_account):
    account = _resolve_account(caller_or_account)
    options = _get_saved_options(account)
    chat_layout = {
        "dock": _sanitize_dock(options.get(_OPTION_FIELD_MAP["dock"])),
        "size": _sanitize_size(options.get(_OPTION_FIELD_MAP["size"])),
        "visible": _sanitize_visible(options.get(_OPTION_FIELD_MAP["visible"])),
        "active_channel": _sanitize_channel(options.get(_OPTION_FIELD_MAP["active_channel"])),
    }
    return {"chat_layout": chat_layout}


def update_ui_preferences(caller_or_account, payload=None):
    account = _resolve_account(caller_or_account)
    if not account:
        return get_ui_preferences(None)

    payload = payload or {}
    options = _get_saved_options(account)
    chat_layout = payload.get("chat_layout") if isinstance(payload, dict) else None
    if isinstance(chat_layout, dict):
        if "dock" in chat_layout:
            options[_OPTION_FIELD_MAP["dock"]] = _sanitize_dock(chat_layout.get("dock"))
        if "size" in chat_layout:
            options[_OPTION_FIELD_MAP["size"]] = _sanitize_size(chat_layout.get("size"))
        if "visible" in chat_layout:
            options[_OPTION_FIELD_MAP["visible"]] = _sanitize_visible(chat_layout.get("visible"))
        if "active_channel" in chat_layout:
            options[_OPTION_FIELD_MAP["active_channel"]] = _sanitize_channel(chat_layout.get("active_channel"))

    account.db._saved_webclient_options = options
    return get_ui_preferences(account)


def _get_saved_options(account):
    if not account:
        return {}
    db = getattr(account, "db", None)
    options = dict(getattr(db, "_saved_webclient_options", {}) or {})
    if not options:
        options = settings.WEBCLIENT_OPTIONS.copy()
    return options


def _resolve_account(caller_or_account):
    if not caller_or_account:
        return None
    if hasattr(caller_or_account, "username") and getattr(caller_or_account, "is_authenticated", True):
        return caller_or_account
    return getattr(caller_or_account, "account", None)


def _sanitize_dock(value):
    if value in _VALID_DOCKS:
        return value
    return DEFAULT_CHAT_LAYOUT["dock"]


def _sanitize_size(value):
    if value in _VALID_SIZES:
        return value
    return DEFAULT_CHAT_LAYOUT["size"]


def _sanitize_channel(value):
    if value in _VALID_CHANNELS:
        return value
    return DEFAULT_CHAT_LAYOUT["active_channel"]


def _sanitize_visible(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in {"false", "0", "off", "no"}
    if value is None:
        return DEFAULT_CHAT_LAYOUT["visible"]
    return bool(value)
