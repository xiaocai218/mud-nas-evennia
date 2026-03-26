"""H5/API 动作分发入口。

负责内容：
- 作为结构化客户端的统一 action -> handler 入口。
- 约束 payload 的最小读取方式，并把各子系统结果包装成统一 response。
- 在战斗中执行动作门禁，避免客户端绕过回合制限制直接改世界状态。

不负责内容：
- 不实现任务、战斗、聊天、物品等具体规则。
- 不承担 HTTP 鉴权、请求解包与路由注册；这些在 web/api 层处理。

主要输入 / 输出：
- 输入：角色对象 `caller`、动作名 `action`、可选 `payload` 字典。
- 输出：`build_response(...)` 生成的结构化响应，失败时统一返回 error code。

上游调用者：
- 主要由 `web/api/views.py` 的 H5 接口调用。
- 也可被未来 WebSocket / 其他客户端协议层复用。

排错优先入口：
- `dispatch_action`
- `_handle_move`
- `_handle_trigger_object`
- `_handle_attack`
- `_handle_battle_*`
"""

from systems.battle import (
    get_battle_snapshot,
    is_character_in_battle,
    list_available_cards,
    list_available_targets,
    start_battle,
    submit_action,
)
from systems.client_protocol import build_response
from systems.chat import send_private_message, send_team_message, send_world_message
from systems.combat import attack_enemy
from systems.items import find_item, use_item
from systems.interaction_errors import build_interaction_error
from systems.market import (
    buy_market_listing,
    cancel_market_listing,
    claim_market_earnings,
    create_market_listing,
)
from systems.npc_routes import run_npc_route
from systems.player_stats import get_stats, try_breakthrough
from systems.quests import get_quest_status_text
from systems.serializers import (
    build_bootstrap_payload,
    serialize_inventory,
    serialize_chat_status,
    serialize_npc_relationship_detail,
    serialize_person_detail,
    serialize_ui_preferences,
    serialize_market_in_room,
    serialize_my_market_status,
    serialize_room,
    serialize_trade_status,
)
from systems.shops import buy_item
from systems.trade import (
    accept_trade_offer,
    cancel_trade_offer,
    create_trade_offer,
    reject_trade_offer,
)
from systems.targeting import find_target_in_room
from systems.world_objects import (
    gather_from_object,
    get_readable_text,
    is_gatherable,
    is_readable,
    trigger_object,
)

attack_training_target = attack_enemy


def dispatch_action(caller, action, payload=None):
    payload = payload or {}
    handlers = {
        "bootstrap": _handle_bootstrap,
        "look": _handle_look,
        "move": _handle_move,
        "read": _handle_read,
        "gather": _handle_gather,
        "trigger_object": _handle_trigger_object,
        "breakthrough": _handle_breakthrough,
        "use_item": _handle_use_item,
        "buy_item": _handle_buy_item,
        "market_listings": _handle_market_listings,
        "market_status": _handle_market_status,
        "market_create_listing": _handle_market_create_listing,
        "market_buy_listing": _handle_market_buy_listing,
        "market_cancel_listing": _handle_market_cancel_listing,
        "market_claim_earnings": _handle_market_claim_earnings,
        "trade_status": _handle_trade_status,
        "trade_create_offer": _handle_trade_create_offer,
        "trade_accept_offer": _handle_trade_accept_offer,
        "trade_reject_offer": _handle_trade_reject_offer,
        "trade_cancel_offer": _handle_trade_cancel_offer,
        "chat_world": _handle_chat_world,
        "chat_team": _handle_chat_team,
        "chat_private": _handle_chat_private,
        "chat_status": _handle_chat_status,
        "talk": _handle_talk,
        "inspect_person": _handle_inspect_person,
        "inspect_npc_relationship": _handle_inspect_npc_relationship,
        "attack": _handle_attack,
        "battle_status": _handle_battle_status,
        "battle_play_card": _handle_battle_play_card,
        "battle_available_cards": _handle_battle_available_cards,
        "battle_targets": _handle_battle_targets,
    }
    handler = handlers.get(action)
    if not handler:
        return build_response(False, error={"code": "unknown_action"})
    # 战斗中的 world state 必须只通过战斗动作推进。
    # 如果这里放开，H5 客户端可以在回合外执行移动/交互/购买，导致战斗快照和真实世界状态脱节。
    if is_character_in_battle(caller) and action not in {
        "attack",
        "battle_status",
        "battle_play_card",
        "battle_available_cards",
        "battle_targets",
        "chat_status",
        "chat_team",
        "bootstrap",
    }:
        return build_response(False, error={"code": "battle_action_only"})
    return handler(caller, payload)


def _handle_bootstrap(caller, payload):
    return build_response(True, build_bootstrap_payload(caller))


def _handle_look(caller, payload):
    return build_response(True, {"room": serialize_room(caller.location)})


def _handle_move(caller, payload):
    direction = payload.get("direction")
    exit_obj = caller.search(direction, candidates=caller.location.exits, quiet=True)
    if not exit_obj:
        # action_router 统一返回结构化 error code，方便 H5 直接映射文案和埋点，
        # 不要求前端再去解析 MUD 终端文本。
        return build_response(False, error={"code": "exit_not_found", "message": f"没有 '{direction}' 这个出口"})

    target = exit_obj[0] if isinstance(exit_obj, list) else exit_obj
    destination = getattr(target, "destination", None)
    if not destination:
        return build_response(False, error={"code": "destination_missing"})

    caller.move_to(destination, quiet=True)
    return build_response(True, {"room": serialize_room(destination)})


def _handle_read(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target or not is_readable(target):
        return build_response(False, error={"code": "target_not_readable"})
    text = get_readable_text(caller, target)
    return build_response(True, {"text": text, "target": target.key})


def _handle_gather(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target or not is_gatherable(target):
        return build_response(False, error={"code": "target_not_gatherable"})
    result = gather_from_object(caller, target)
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason"), "message": result.get("text")})
    return build_response(
        True,
        {
            "text": result.get("text"),
            "inventory": serialize_inventory(caller),
            "stamina": result.get("stamina_now"),
            "max_stamina": result.get("max_stamina"),
        },
    )


def _handle_trigger_object(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target:
        return build_response(False, error={"code": "target_not_found"})
    result = trigger_object(caller, target, option=payload.get("option"))
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason"), "message": result.get("text")})
    response = {"text": result.get("text"), "room": serialize_room(caller.location)}
    if result.get("destination"):
        response["room"] = serialize_room(result["destination"])
    if "choices" in result:
        response["choices"] = result["choices"]
    if "root" in result:
        response["root"] = result["root"]
        response["root_label"] = result.get("root_label")
    return build_response(True, response)


def _handle_breakthrough(caller, payload):
    result = try_breakthrough(caller)
    if not result.get("ok"):
        requirements = (result.get("requirements") or {}) if result.get("reason") == "requirements_not_met" else None
        return build_response(
            False,
            error={
                "code": result.get("reason") or "breakthrough_failed",
                "message": "当前尚未满足突破条件" if result.get("reason") != "requirements_not_met" else "突破条件尚未齐备",
                "requirements": requirements,
            },
        )
    return build_response(
        True,
        {
            "result": result,
            "character": build_bootstrap_payload(caller)["character"],
        },
    )


def _handle_use_item(caller, payload):
    item = find_item(caller, item_name=payload.get("target"), item_id=payload.get("item_id"))
    if not item:
        return build_response(False, error={"code": "item_not_found"})
    result = use_item(caller, item)
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason")})
    return build_response(True, {"result": result, "inventory": serialize_inventory(caller)})


def _handle_buy_item(caller, payload):
    result = buy_item(caller, payload.get("target"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(True, {"result": result, "inventory": serialize_inventory(caller)})


def _handle_market_listings(caller, payload):
    market = serialize_market_in_room(
        caller.location,
        page=payload.get("page", 1),
        keyword=(payload.get("keyword") or "").strip() or None,
    )
    if not market:
        return build_response(False, error={"code": "market_not_available"})
    return build_response(True, {"market": market})


def _handle_market_status(caller, payload):
    status = serialize_my_market_status(caller)
    if not status:
        return build_response(False, error={"code": "market_not_available"})
    return build_response(True, {"status": status, "inventory": serialize_inventory(caller)})


def _handle_market_create_listing(caller, payload):
    result = create_market_listing(caller, payload.get("target"), payload.get("price"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "inventory": serialize_inventory(caller),
            "market": serialize_market_in_room(caller.location),
            "status": serialize_my_market_status(caller),
        },
    )


def _handle_market_buy_listing(caller, payload):
    result = buy_market_listing(caller, payload.get("listing_id"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "inventory": serialize_inventory(caller),
            "market": serialize_market_in_room(caller.location),
        },
    )


def _handle_market_cancel_listing(caller, payload):
    result = cancel_market_listing(caller, payload.get("listing_id"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "inventory": serialize_inventory(caller),
            "market": serialize_market_in_room(caller.location),
            "status": serialize_my_market_status(caller),
        },
    )


def _handle_market_claim_earnings(caller, payload):
    result = claim_market_earnings(caller)
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "character": build_bootstrap_payload(caller)["character"],
            "status": serialize_my_market_status(caller),
        },
    )


def _handle_trade_status(caller, payload):
    status = serialize_trade_status(caller)
    if not status:
        return build_response(False, error={"code": "trade_status_unavailable"})
    return build_response(True, {"status": status, "inventory": serialize_inventory(caller)})


def _handle_trade_create_offer(caller, payload):
    result = create_trade_offer(caller, payload.get("target"), payload.get("item_name"), payload.get("price"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "inventory": serialize_inventory(caller),
            "status": serialize_trade_status(caller),
        },
    )


def _handle_trade_accept_offer(caller, payload):
    result = accept_trade_offer(caller, payload.get("target"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "inventory": serialize_inventory(caller),
            "status": serialize_trade_status(caller),
        },
    )


def _handle_trade_reject_offer(caller, payload):
    result = reject_trade_offer(caller, payload.get("target"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "status": serialize_trade_status(caller),
        },
    )


def _handle_trade_cancel_offer(caller, payload):
    result = cancel_trade_offer(caller, payload.get("target"))
    if not result.get("ok"):
        return build_response(False, error=result.get("error") or {"code": result.get("reason")})
    return build_response(
        True,
        {
            "result": result,
            "status": serialize_trade_status(caller),
        },
    )


def _build_chat_response(result):
    if not result.get("ok"):
        return build_response(
            False,
            error={"code": result.get("reason"), "message": result.get("text")},
        )
    return build_response(
        True,
        {
            "message": result.get("message"),
            "event": result.get("event"),
            "delivered": result.get("delivered", 0),
            "text": result.get("text", ""),
        },
    )


def _handle_chat_world(caller, payload):
    return _build_chat_response(send_world_message(caller, payload.get("text", "").strip()))


def _handle_chat_team(caller, payload):
    return _build_chat_response(send_team_message(caller, payload.get("text", "").strip()))


def _handle_chat_private(caller, payload):
    return _build_chat_response(
        send_private_message(caller, payload.get("target", "").strip(), payload.get("text", "").strip())
    )


def _handle_chat_status(caller, payload):
    chat_status = serialize_chat_status(caller)
    return build_response(
        True,
        {
            "channels": chat_status["channels"],
            "recent_messages": chat_status["recent_messages"],
            "ui_preferences": serialize_ui_preferences(caller),
        },
    )


def _handle_talk(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target:
        return build_response(False, error=build_interaction_error("target_not_found"))
    if not getattr(target.db, "npc_role", None):
        return build_response(False, error=build_interaction_error("target_not_talkable", target=target.key))

    messages = _capture_messages(caller, lambda: _run_talk_route(caller, target))
    return build_response(
        True,
        {
            "target": target.key,
            "messages": messages,
            "quests_text": get_quest_status_text(caller),
        },
    )


def _handle_inspect_person(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target:
        return build_response(False, error=build_interaction_error("target_not_found"))
    detail = serialize_person_detail(target, viewer=caller)
    if not detail:
        return build_response(False, error=build_interaction_error("target_not_person", target=target.key))
    return build_response(True, {"target": target.key, "person": detail})


def _handle_inspect_npc_relationship(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target:
        return build_response(False, error=build_interaction_error("target_not_found"))
    detail = serialize_npc_relationship_detail(caller, target)
    if not detail:
        return build_response(False, error=build_interaction_error("npc_relationship_unavailable", target=target.key))
    return build_response(True, {"target": target.key, "relationship": detail})


def _handle_attack(caller, payload):
    target = find_target_in_room(caller, payload.get("target"))
    if not target:
        return build_response(False, error=build_interaction_error("target_not_found"))
    if not getattr(target.db, "combat_target", False):
        return build_response(False, error=build_interaction_error("target_not_attackable", target=target.key))

    result = attack_training_target(caller, target)
    if not result.get("ok"):
        return build_response(
            False,
            error={"code": result.get("reason"), "cost": result.get("cost")},
        )

    payload = {
        "result": result,
        "character_stats": get_stats(caller),
        "inventory": serialize_inventory(caller),
    }
    return build_response(True, payload)


def _handle_battle_status(caller, payload):
    battle = get_battle_snapshot(caller)
    if not battle:
        return build_response(False, error={"code": "battle_not_found"})
    return build_response(True, {"battle": battle})


def _handle_battle_play_card(caller, payload):
    result = submit_action(
        caller,
        payload.get("card_id"),
        target_id=payload.get("target_id"),
        item_id=payload.get("item_id"),
    )
    if not result.get("ok"):
        return build_response(False, error={"code": result.get("reason")})
    return build_response(True, {"result": result.get("result"), "battle": result.get("battle")})


def _handle_battle_available_cards(caller, payload):
    if not is_character_in_battle(caller):
        return build_response(False, error={"code": "battle_not_found"})
    return build_response(True, {"cards": list_available_cards(caller)})


def _handle_battle_targets(caller, payload):
    if not is_character_in_battle(caller):
        return build_response(False, error={"code": "battle_not_found"})
    return build_response(True, {"targets": list_available_targets(caller)})


def _handle_not_implemented(caller, payload):
    return build_response(False, error={"code": "not_implemented"})


def _run_talk_route(caller, target):
    if run_npc_route(caller, getattr(target.db, "talk_route", None)):
        return
    caller.msg(f"{target.key} 暂时没有更多可说的。")


def _capture_messages(caller, func):
    messages = []
    original_msg = caller.msg

    def _capture(text=None, *args, **kwargs):
        messages.append("" if text is None else str(text))

    caller.msg = _capture
    try:
        func()
    finally:
        caller.msg = original_msg
    return messages
