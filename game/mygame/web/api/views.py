"""JSON endpoints for the future H5 client."""

import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from systems.action_router import dispatch_action
from systems.client_protocol import ACTION_SPECS, build_response, validate_action_message
from systems.serializers import build_bootstrap_payload, serialize_quest_log, serialize_shop_by_id


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


@require_GET
def protocol_overview_view(request):
    payload = {
        "version": "v1",
        "http_base": "/api/h5/",
        "actions": sorted(ACTION_SPECS.keys()),
        "routes": {
            "bootstrap": "/api/h5/bootstrap/",
            "quests": "/api/h5/quests/",
            "action": "/api/h5/action/",
            "shop_detail": "/api/h5/shops/<shop_id>/",
            "ws_meta": "/api/h5/ws-meta/",
        },
    }
    return _json_response(build_response(True, payload))


@require_GET
def ws_meta_view(request):
    scheme = "wss" if request.is_secure() else "ws"
    host = request.get_host()
    payload = {
        "implemented": False,
        "version": "v1",
        "endpoint": f"{scheme}://{host}/api/h5/ws/",
        "note": "WebSocket transport is not implemented yet. Use HTTP endpoints for now.",
        "actions": sorted(ACTION_SPECS.keys()),
        "webclient_ws_port": int(
            getattr(settings, "WEBSOCKET_CLIENT_PROXY_PORT", settings.WEBSOCKET_CLIENT_PORT)
        ),
    }
    return _json_response(build_response(True, payload))


@require_GET
def bootstrap_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response
    return _json_response(build_response(True, build_bootstrap_payload(caller)))


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


@require_POST
def action_view(request):
    caller, error_response = _get_active_character(request)
    if error_response:
        return error_response

    try:
        message = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _json_response(
            build_response(False, error={"code": "invalid_json", "message": "请求体不是合法 JSON"}),
            status=400,
        )

    ok, error_code = validate_action_message(message)
    if not ok:
        return _json_response(
            build_response(False, error={"code": error_code, "message": "动作消息格式不正确"}),
            status=400,
        )

    response = dispatch_action(caller, message["action"], message.get("payload") or {})
    return _json_response(response)
