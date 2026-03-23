"""Client protocol envelopes and action validation helpers."""


ACTION_SPECS = {
    "move": {"required": ["direction"]},
    "talk": {"required": ["target"]},
    "attack": {"required": ["target"]},
    "gather": {"required": ["target"]},
    "read": {"required": ["target"]},
    "trigger_object": {"required": ["target"]},
    "use_item": {"required": ["target"]},
    "buy_item": {"required": ["target"]},
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

    missing = [field for field in ACTION_SPECS[action]["required"] if field not in payload]
    if missing:
        return False, f"missing_fields:{','.join(missing)}"
    return True, None
