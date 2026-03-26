"""客户端协议信封与最小动作校验层。

负责内容：
- 定义 action message / response message 的最小外形。
- 维护 action 所需字段的白名单式校验。
- 在进入 action_router 之前尽早拦下明显坏请求。

不负责内容：
- 不实现业务动作本身。
- 不做权限、登录态和房间合法性校验；这些由更上层入口和系统模块负责。

主要输入 / 输出：
- 输入：原始 message dict、action 名、payload。
- 输出：规范化 action/response 包，或 `(ok, error_code)` 校验结果。

上游调用者：
- `web/api/views.py`
- 未来 WebSocket action 入口

排错优先入口：
- `ACTION_SPECS`
- `build_action`
- `build_response`
- `validate_action_message`
"""


ACTION_SPECS = {
    "move": {"required": ["direction"]},
    "talk": {"required": ["target"]},
    "attack": {"required": ["target"]},
    "battle_status": {"required": []},
    "battle_play_card": {"required": ["card_id"]},
    "battle_available_cards": {"required": []},
    "battle_targets": {"required": []},
    "chat_world": {"required": ["text"]},
    "chat_team": {"required": ["text"]},
    "chat_private": {"required": ["target", "text"]},
    "chat_status": {"required": []},
    "gather": {"required": ["target"]},
    "read": {"required": ["target"]},
    "trigger_object": {"required": ["target"]},
    "breakthrough": {"required": []},
    "use_item": {"required": ["target"]},
    "buy_item": {"required": ["target"]},
    "market_listings": {"required": []},
    "market_status": {"required": []},
    "market_create_listing": {"required": ["target", "price"]},
    "market_buy_listing": {"required": ["listing_id"]},
    "market_cancel_listing": {"required": ["listing_id"]},
    "market_claim_earnings": {"required": []},
    "trade_status": {"required": []},
    "trade_create_offer": {"required": ["target", "item_name"]},
    "trade_accept_offer": {"required": []},
    "trade_reject_offer": {"required": []},
    "trade_cancel_offer": {"required": []},
    "bootstrap": {"required": []},
    "look": {"required": []},
}


def build_action(action, payload=None):
    return {
        "type": "action",
        "action": action,
        "payload": payload or {},
    }


def build_response(ok, payload=None, error=None):
    # response 永远保留 payload 字段，即使失败也给前端稳定外形。
    # 这样客户端不需要在 success / failure 间切换两套解包逻辑。
    response = {
        "type": "response",
        "ok": bool(ok),
        "payload": payload or {},
    }
    if error:
        response["error"] = error
    return response


def validate_action_message(message):
    if not isinstance(message, dict):
        return False, "message_must_be_object"
    if message.get("type") != "action":
        return False, "type_must_be_action"

    action = message.get("action")
    if action not in ACTION_SPECS:
        return False, "unknown_action"

    payload = message.get("payload") or {}
    if not isinstance(payload, dict):
        return False, "payload_must_be_object"

    # 这里只校验“字段是否存在”，不校验语义。
    # 例如 price 是否 >= 0、listing_id 是否存在，仍由业务层给出更准确的错误码。
    missing = [field for field in ACTION_SPECS[action]["required"] if field not in payload]
    if missing:
        return False, f"missing_fields:{','.join(missing)}"
    return True, None
