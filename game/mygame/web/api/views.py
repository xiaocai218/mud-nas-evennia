"""JSON endpoints for the future H5 client."""

import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from systems.action_router import dispatch_action
from systems.client_protocol import ACTION_SPECS, build_response, validate_action_message
from systems.event_bus import build_event_batch, pop_account_events
from systems.battle_summary import render_battle_summary
from systems.battle import get_battle_snapshot
from systems.serializers import (
    build_bootstrap_payload,
    serialize_market_by_id,
    serialize_account,
    serialize_chat_status,
    serialize_character_summary,
    serialize_quest_log,
    serialize_shop_by_id,
    serialize_ui_preferences,
)
from systems.ui_preferences import update_ui_preferences


def _json_response(payload, status=200):
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def _get_account(request):
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user
    return None


def _iter_characters(account):
    characters = getattr(account, "characters", [])
    try:
        return list(characters.all())
    except AttributeError:
        return list(characters)


def _load_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, _json_response(
            build_response(False, error={"code": "invalid_json", "message": "请求体不是合法 JSON"}),
            status=400,
        )


def _get_active_character(request):
    account = _get_account(request)
    if not account:
        return None, _json_response(
            build_response(False, error={"code": "not_authenticated", "message": "需要先登录账号"}),
            status=401,
        )

    characters = _iter_characters(account)

    puppet_id = getattr(request, "session", {}).get("puppet")
    if puppet_id is not None:
        try:
            puppet_id = int(puppet_id)
        except (TypeError, ValueError):
            puppet_id = None
        if puppet_id is not None:
            for character in characters:
                if getattr(character, "pk", None) == puppet_id:
                    return character, None

    last_puppet = getattr(getattr(account, "db", None), "_last_puppet", None)
    if last_puppet:
        return last_puppet, None

    if len(characters) == 1:
        return characters[0], None

    return None, _json_response(
        build_response(False, error={"code": "no_active_character", "message": "当前没有激活角色"}),
        status=409,
    )


# H5 uses session cookies for these JSON endpoints; exempt them from Django's
# form-oriented CSRF middleware so same-origin fetch requests can log in and act.
@csrf_exempt
@require_POST
def login_view(request):
    payload, error_response = _load_json_body(request)
    if error_response:
        return error_response

    username = (payload or {}).get("username", "")
    password = (payload or {}).get("password", "")
    if not username or not password:
        return _json_response(
            build_response(False, error={"code": "missing_credentials", "message": "缺少账号或密码"}),
            status=400,
        )

    account = authenticate(request, username=username, password=password)
    if not account:
        return _json_response(
            build_response(False, error={"code": "invalid_credentials", "message": "账号或密码错误"}),
            status=401,
        )

    login(request, account)
    request.session["website_authenticated_uid"] = account.id
    request.session["webclient_authenticated_uid"] = account.id

    characters = _iter_characters(account)
    if len(characters) == 1:
        request.session["puppet"] = int(characters[0].pk)
        account.db._last_puppet = characters[0]

    active_character, _ = _get_active_character(request)
    return _json_response(
        build_response(
            True,
            {
                "account": serialize_account(account),
                "characters": [serialize_character_summary(character) for character in characters],
                "active_character_id": getattr(active_character, "pk", None),
            },
        )
    )


@csrf_exempt
@require_POST
def logout_view(request):
    if getattr(request, "session", None):
        request.session["puppet"] = None
        request.session["website_authenticated_uid"] = None
        request.session["webclient_authenticated_uid"] = None
    logout(request)
    return _json_response(build_response(True, {"logged_out": True}))


@require_GET
def character_list_view(request):
    account = _get_account(request)
    if not account:
        return _json_response(
            build_response(False, error={"code": "not_authenticated", "message": "需要先登录账号"}),
            status=401,
        )

    active_character, _ = _get_active_character(request)
    return _json_response(
        build_response(
            True,
            {
                "account": serialize_account(account),
                "characters": [serialize_character_summary(character) for character in _iter_characters(account)],
                "active_character_id": getattr(active_character, "pk", None),
            },
        )
    )


@csrf_exempt
@require_POST
def character_select_view(request):
    account = _get_account(request)
    if not account:
        return _json_response(
            build_response(False, error={"code": "not_authenticated", "message": "需要先登录账号"}),
            status=401,
        )

    payload, error_response = _load_json_body(request)
    if error_response:
        return error_response

    character_id = (payload or {}).get("character_id")
    if character_id is None:
        return _json_response(
            build_response(False, error={"code": "missing_character_id", "message": "缺少角色 ID"}),
            status=400,
        )

    try:
        character_id = int(character_id)
    except (TypeError, ValueError):
        return _json_response(
            build_response(False, error={"code": "invalid_character_id", "message": "角色 ID 格式错误"}),
            status=400,
        )

    target = next((character for character in _iter_characters(account) if getattr(character, "pk", None) == character_id), None)
    if not target:
        return _json_response(
            build_response(False, error={"code": "character_not_found", "message": "角色不存在或不属于当前账号"}),
            status=404,
        )

    request.session["puppet"] = int(target.pk)
    account.db._last_puppet = target

    return _json_response(
        build_response(
            True,
            {
                "active_character_id": target.pk,
                "bootstrap": build_bootstrap_payload(target),
            },
        )
    )


@require_GET
def protocol_overview_view(request):
    payload = {
        "version": "v1",
        "http_base": "/api/h5/",
        "actions": sorted(ACTION_SPECS.keys()),
        "routes": {
            "login": "/api/h5/auth/login/",
            "logout": "/api/h5/auth/logout/",
            "character_list": "/api/h5/account/characters/",
            "character_select": "/api/h5/account/characters/select/",
            "bootstrap": "/api/h5/bootstrap/",
            "chat_status": "/api/h5/chat-status/",
            "ui_preferences": "/api/h5/ui/preferences/",
            "quests": "/api/h5/quests/",
            "action": "/api/h5/action/",
            "shop_detail": "/api/h5/shops/<shop_id>/",
            "market_detail": "/api/h5/markets/<market_id>/",
            "ws_meta": "/api/h5/ws-meta/",
            "event_poll": "/api/h5/events/poll/",
        },
    }
    return _json_response(build_response(True, payload))


@require_GET
def ws_meta_view(request):
    scheme = "wss" if request.is_secure() else "ws"
    host = request.get_host()
    caller, _ = _get_active_character(request)
    payload = {
        "implemented": False,
        "version": "v1",
        "endpoint": f"{scheme}://{host}/api/h5/ws/",
        "poll_endpoint": "/api/h5/events/poll/",
        "transports": {
            "websocket": {
                "available": False,
                "implemented": False,
                "note": "WebSocket bridge is not implemented yet.",
            },
            "poll": {
                "available": True,
                "interval_ms": 3000,
                "cursor_type": "opaque_string",
            },
        },
        "session": {
            "authenticated": bool(_get_account(request)),
            "active_character_id": getattr(caller, "pk", None) if caller else None,
        },
        "events": {
            "supported": [
                "chat.message",
                "room.updated",
                "stats.updated",
                "inventory.updated",
                "quest.updated",
                "system.notice",
            ],
        },
        "note": "WebSocket is reserved for a future bridge. Polling is the current fallback transport.",
        "actions": sorted(ACTION_SPECS.keys()),
        "webclient_ws_port": int(
            getattr(settings, "WEBSOCKET_CLIENT_PROXY_PORT", settings.WEBSOCKET_CLIENT_PORT)
        ),
    }
    return _json_response(build_response(True, payload))


@require_GET
def event_poll_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response

    cursor = request.GET.get("cursor")
    payload = build_event_batch(events=pop_account_events(_get_account(request)), cursor=cursor, transport="poll")
    payload["active_character_id"] = getattr(caller, "pk", None)
    return _json_response(build_response(True, payload))


@require_GET
def bootstrap_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    return _json_response(build_response(True, build_bootstrap_payload(caller)))


@require_GET
def battle_status_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    battle = get_battle_snapshot(caller)
    if not battle:
        return _json_response(build_response(True, {"battle": None, "summary": "", "signature": None}))
    signature = ":".join(
        [
            str(battle.get("battle_id") or ""),
            str(battle.get("status") or ""),
            str(battle.get("turn_count") or 0),
            str(battle.get("current_actor_id") or ""),
            str((battle.get("log") or [{}])[-1].get("turn_count") if battle.get("log") else ""),
        ]
    )
    return _json_response(
        build_response(
            True,
            {
                "battle": battle,
                "summary": render_battle_summary(battle, viewer_name=caller.key),
                "signature": signature,
            },
        )
    )


@require_GET
def chat_status_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    chat_status = serialize_chat_status(caller)
    return _json_response(
        build_response(
            True,
            {
                "channels": chat_status["channels"],
                "recent_messages": chat_status["recent_messages"],
                "recent_combat_logs": chat_status.get("recent_combat_logs", []),
                "ui_preferences": serialize_ui_preferences(caller),
            },
        )
    )


@csrf_exempt
def ui_preferences_view(request):
    account = _get_account(request)
    if not account:
        return _json_response(
            build_response(False, error={"code": "not_authenticated", "message": "需要先登录账号"}),
            status=401,
        )

    if request.method == "GET":
        return _json_response(build_response(True, {"ui_preferences": serialize_ui_preferences(account)}))
    if request.method != "POST":
        return _json_response(
            build_response(False, error={"code": "method_not_allowed", "message": "请求方法不支持"}),
            status=405,
        )

    payload, error_response = _load_json_body(request)
    if error_response:
        return error_response
    updated = update_ui_preferences(account, payload or {})
    return _json_response(build_response(True, {"ui_preferences": updated}))


@require_GET
def quest_log_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    return _json_response(build_response(True, {"quests": serialize_quest_log(caller)}))


@require_GET
def shop_detail_view(request, shop_id):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    shop = serialize_shop_by_id(shop_id)
    if not shop:
        return _json_response(
            build_response(False, error={"code": "shop_not_found", "message": "商店不存在"}),
            status=404,
        )
    return _json_response(
        build_response(
            True,
            {
                "shop": shop,
                "character": build_bootstrap_payload(caller)["character"],
            },
        )
    )


@require_GET
def market_detail_view(request, market_id):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    page = request.GET.get("page", 1)
    keyword = request.GET.get("keyword")
    market = serialize_market_by_id(market_id, page=page, keyword=keyword)
    if not market:
        return _json_response(
            build_response(False, error={"code": "market_not_found", "message": "坊市不存在"}),
            status=404,
        )
    return _json_response(
        build_response(
            True,
            {
                "market": market,
                "character": build_bootstrap_payload(caller)["character"],
            },
        )
    )


@csrf_exempt
@require_POST
def action_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response

    message, error_response = _load_json_body(request)
    if error_response:
        return error_response

    ok, error_code = validate_action_message(message)
    if not ok:
        return _json_response(
            build_response(False, error={"code": error_code, "message": "动作消息格式不正确"}),
            status=400,
        )

    response = dispatch_action(caller, message["action"], message.get("payload") or {})
    return _json_response(response)
