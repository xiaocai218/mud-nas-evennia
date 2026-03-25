"""配置驱动的场景对象交互层。

负责内容：
- 根据对象上的 `read_config` / `gather_config` / `trigger_effect` 解释交互行为。
- 为 `阅读`、`采集`、`触发` 三类入口提供统一 helper。
- 兼容旧对象散字段，并逐步收口到配置驱动模型。

不负责内容：
- 不负责对象的创建与铺设；那部分在 world/start_area 与内容数据层。
- 不负责具体 buff / restore 数值结算；这些交给 effect_executor。

主要输入 / 输出：
- 输入：玩家对象 `caller`、live object `target`、可选触发参数 `option`。
- 输出：统一的 `{"ok": bool, ...}` 结果字典，供命令层和 action router 复用。

上游调用者：
- `commands/core.py`
- `action_router.py`
- 需要按 `content_id` 驱动对象行为的其他系统模块

排错优先入口：
- `get_readable_text`
- `gather_from_object`
- `trigger_object`
- `teleport_via_object`
- `awaken_root_via_object`
"""

from systems.character_model import ROOT_CHOICES, awaken_spiritual_root, get_root_label, normalize_root_choice
from systems.effect_executor import execute_effect
from systems.items import create_loot
from systems.object_index import get_object_by_content_id, iter_world_objects
from systems.player_stats import get_stats
from systems.quests import (
    can_access_ascension_platform,
    can_use_spirit_stone,
    get_quest_state,
    get_quest_status_text,
    has_awakened_spiritual_root,
    mark_root_awakened,
)


TRIGGER_CONFIG_FALLBACK_KEYS = [
    "teleport_room_id",
    "teleport_room_key",
    "teleport_text",
    "locked_text",
    "required_main_state",
    "buff_key",
    "buff_bonus",
    "buff_duration",
    "buff_label",
    "buff_text",
    "type",
]

TELEPORT_CONFIG_FALLBACK_KEYS = [
    "teleport_room_id",
    "teleport_room_key",
    "teleport_text",
    "locked_text",
    "required_main_state",
]

BUFF_CONFIG_FALLBACK_KEYS = ["buff_key", "buff_bonus", "buff_duration", "buff_label", "buff_text"]
SPIRITUAL_ROOT_CONFIG_FALLBACK_KEYS = ["text", "confirm_text", "already_awakened_text"]


def _get_config(target, attr_name, fallback_keys=None):
    config = getattr(target.db, attr_name, None)
    if config:
        return config
    if not fallback_keys:
        return None
    # 旧对象还可能把配置散落在单独 db 字段上。
    # 这里保留 fallback，是为了让内容逐步迁移到统一 config 结构时不必一次性重建所有 live object。
    data = {}
    for key in fallback_keys:
        value = getattr(target.db, key, None)
        if value is not None:
            data[key] = value
    return data or None


def _check_requirements(caller, requirements):
    if not requirements:
        return {"ok": True}
    current_state = get_quest_state(caller)
    main_state = requirements.get("main_state_is")
    if main_state and current_state != main_state:
        return {
            "ok": False,
            "reason": "locked",
            "text": requirements.get("fail_text") or "这处入口暂时还不会向你开启。",
        }
    main_states = requirements.get("main_state_in")
    if main_states and current_state not in set(main_states):
        return {
            "ok": False,
            "reason": "locked",
            "text": requirements.get("fail_text") or "这处入口暂时还不会向你开启。",
        }
    return {"ok": True}


def _check_object_specific_requirements(caller, target):
    content_id = getattr(target.db, "content_id", None)
    if content_id == "obj_qingyun_gate_01" and not can_access_ascension_platform(caller):
        return {
            "ok": False,
            "reason": "locked",
            "text": "你刚靠近山门，门上云纹便生出一层微凉阻力，像是在提醒你：先完成眼前这段试炼，拿到前往升仙台测灵的资格，再谈更高处的去路。",
        }
    if content_id == "obj_spirit_stone_01" and not can_use_spirit_stone(caller):
        return {
            "ok": False,
            "reason": "locked",
            "text": "你将手伸向测灵石，却只触到一层温凉却毫无回应的光幕。眼下还不到定下灵根的时候。",
        }
    return {"ok": True}


def is_readable(target):
    read_config = _get_config(target, "read_config")
    return bool(read_config or getattr(target.db, "readable_text", None) or getattr(target.db, "quest_hint_title", None))


def get_readable_text(caller, target):
    read_config = _get_config(target, "read_config")
    if read_config:
        read_type = read_config.get("type", "static")
        if read_type == "static":
            return read_config.get("text")
        if read_type == "quest_status":
            title = read_config.get("title") or "|g路碑灵光|n"
            intro = read_config.get("intro") or "碑面上的灵光缓缓聚拢，映出你当前最紧要的方向。"
            return f"{title}\n\n{intro}\n\n{get_quest_status_text(caller)}"

    static_text = getattr(target.db, "readable_text", None)
    if static_text:
        return static_text

    quest_hint_title = getattr(target.db, "quest_hint_title", None)
    if quest_hint_title:
        intro = getattr(target.db, "quest_hint_intro", None) or "碑面上的灵光缓缓聚拢，映出你当前最紧要的方向。"
        return f"{quest_hint_title}\n\n{intro}\n\n{get_quest_status_text(caller)}"

    return None


def is_gatherable(target):
    gather_config = _get_config(target, "gather_config", ["gather_item_id", "gather_item", "gather_cost", "gather_text", "gather_fail_text"])
    return bool(gather_config and (gather_config.get("gather_item_id") or gather_config.get("gather_item")))


def gather_from_object(caller, target):
    gather_config = _get_config(target, "gather_config", ["gather_item_id", "gather_item", "gather_cost", "gather_text", "gather_fail_text"])
    gather_item_id = gather_config.get("gather_item_id") if gather_config else None
    gather_item = gather_config.get("gather_item") if gather_config else None
    cost = int((gather_config or {}).get("gather_cost", 0) or 0)
    if not gather_item and not gather_item_id:
        return {"ok": False, "reason": "not_gatherable"}

    stats = get_stats(caller)
    if stats["stamina"] < cost:
        fail_text = (gather_config or {}).get("gather_fail_text") or "你现在体力不足，没法好好采集。"
        return {"ok": False, "reason": "stamina_low", "cost": cost, "text": fail_text.format(cost=cost)}

    caller.db.stamina = max(0, stats["stamina"] - cost)
    item = create_loot(caller, key=gather_item, item_id=gather_item_id)
    item_name = item.key if item else (gather_item or gather_item_id)
    text = (gather_config or {}).get("gather_text") or f"你从 {target.key} 上采下了 {item_name}。"
    return {
        "ok": True,
        "item": item,
        "cost": cost,
        "text": text,
        "stamina_now": caller.db.stamina,
        "max_stamina": stats["max_stamina"],
    }


def is_teleportable(target):
    trigger_config = _get_trigger_config(target)
    if not trigger_config:
        return False
    effect_type = trigger_config.get("type", "teleport")
    if effect_type != "teleport":
        return False
    return bool(trigger_config.get("room_id") or trigger_config.get("teleport_room_id") or trigger_config.get("teleport_room_key"))


def teleport_via_object(caller, target):
    trigger_config = _get_config(target, "trigger_effect", TELEPORT_CONFIG_FALLBACK_KEYS)
    requirements = _get_config(target, "trigger_requirements")
    room_id = (trigger_config or {}).get("room_id") or (trigger_config or {}).get("teleport_room_id")
    room_key = (trigger_config or {}).get("room_key") or (trigger_config or {}).get("teleport_room_key")
    if not room_key and not room_id:
        return {"ok": False, "reason": "not_teleportable"}

    legacy_required_main_state = (trigger_config or {}).get("required_main_state")
    if legacy_required_main_state and not requirements:
        # 兼容早期仅用 trigger_effect.required_main_state 描述门禁的对象配置。
        # 新配置优先使用 trigger_requirements，避免 teleport/buff/spiritual_root 重复发明条件字段。
        requirements = {"main_state_is": legacy_required_main_state, "fail_text": (trigger_config or {}).get("locked_text")}
    requirement_result = _check_requirements(caller, requirements)
    if not requirement_result["ok"]:
        return requirement_result
    object_requirement_result = _check_object_specific_requirements(caller, target)
    if not object_requirement_result["ok"]:
        return object_requirement_result

    destination = None
    if room_id:
        destination = get_object_by_content_id(room_id)
    if not destination and room_key:
        destination = next((obj for obj in iter_world_objects() if obj.db_key == room_key), None)
    if not destination:
        return {"ok": False, "reason": "destination_missing", "text": "这处灵纹如今黯淡无光，似乎暂时无法回应。"}

    caller.move_to(destination, quiet=True)
    text = (trigger_config or {}).get("text") or (trigger_config or {}).get("teleport_text") or f"你借 {target.key} 的灵力回到了 {destination.key}。"
    return {"ok": True, "text": text, "destination": destination}


def is_blessable(target):
    trigger_config = _get_config(target, "trigger_effect", BUFF_CONFIG_FALLBACK_KEYS)
    if not trigger_config:
        return False
    effect_type = trigger_config.get("type", "buff")
    if effect_type != "buff":
        return False
    return bool(trigger_config.get("buff_key"))


def is_triggerable(target):
    return bool(_get_trigger_config(target))


def receive_object_blessing(caller, target):
    trigger_config = _get_config(target, "trigger_effect", BUFF_CONFIG_FALLBACK_KEYS)
    buff_key = (trigger_config or {}).get("buff_key")
    if not buff_key:
        return {"ok": False, "reason": "not_blessable"}
    return execute_effect(caller, trigger_config)


def awaken_root_via_object(caller, target, root_choice=None):
    trigger_config = _get_config(target, "trigger_effect", SPIRITUAL_ROOT_CONFIG_FALLBACK_KEYS)
    requirements = _get_config(target, "trigger_requirements")
    requirement_result = _check_requirements(caller, requirements)
    if not requirement_result["ok"]:
        return requirement_result
    object_requirement_result = _check_object_specific_requirements(caller, target)
    if not object_requirement_result["ok"]:
        return object_requirement_result

    stats = get_stats(caller)
    if stats["stage"] == "cultivator" and stats["root"] and has_awakened_spiritual_root(caller):
        return {
            "ok": True,
            "text": (trigger_config or {}).get("already_awakened_text") or "你的灵根已定。",
            "root": stats["root"],
            "already_awakened": True,
        }

    normalized_root = normalize_root_choice(root_choice)
    if not normalized_root:
        return {
            "ok": True,
            "text": (trigger_config or {}).get("text") or f"{target.key} 映出五行灵光，等待你的选择。",
            "choices": list(ROOT_CHOICES),
            "awaiting_choice": True,
        }

    sheet = awaken_spiritual_root(caller, normalized_root)
    mark_root_awakened(caller)
    confirm_text = (trigger_config or {}).get("confirm_text") or "灵根已定：{root_label}"
    return {
        "ok": True,
        "text": confirm_text.format(root_label=get_root_label(normalized_root, normalized_root)),
        "root": normalized_root,
        "root_label": get_root_label(normalized_root, normalized_root),
        "character": sheet,
    }


def trigger_object(caller, target, option=None):
    trigger_config = _get_trigger_config(target)
    if not trigger_config:
        return {"ok": False, "reason": "not_triggerable", "text": f"{target.key} 看起来并不会回应你的触碰。"}

    effect_type = _resolve_trigger_type(target, trigger_config)
    # 触发类型统一走 handler 映射，避免后续新增对象效果时把条件分支继续堆回单个函数。
    handler = TRIGGER_HANDLERS.get(effect_type)
    if handler:
        return handler(caller, target, trigger_config=trigger_config, option=option)
    return {"ok": False, "reason": "unsupported_trigger", "text": f"{target.key} 暂时还没有可触发的反应。"}


def _get_trigger_config(target):
    return _get_config(target, "trigger_effect", TRIGGER_CONFIG_FALLBACK_KEYS)


def _resolve_trigger_type(target, trigger_config):
    effect_type = trigger_config.get("type")
    if effect_type:
        return effect_type
    if is_blessable(target):
        return "buff"
    return "teleport"


def _handle_trigger_teleport(caller, target, trigger_config=None, option=None):
    return teleport_via_object(caller, target)


def _handle_trigger_buff(caller, target, trigger_config=None, option=None):
    return receive_object_blessing(caller, target)


def _handle_trigger_restore(caller, target, trigger_config=None, option=None):
    return execute_effect(caller, trigger_config or {})


def _handle_trigger_spiritual_root(caller, target, trigger_config=None, option=None):
    return awaken_root_via_object(caller, target, root_choice=option)


TRIGGER_HANDLERS = {
    "teleport": _handle_trigger_teleport,
    "buff": _handle_trigger_buff,
    "restore": _handle_trigger_restore,
    "spiritual_root": _handle_trigger_spiritual_root,
}
