"""物品定义与背包辅助层。

负责内容：
- 从 `items.json` 读取物品定义，并在 live item 与静态定义之间做映射。
- 提供背包查找、掉落物创建、奖励物创建、炼化与使用入口。
- 让任务、战斗、对象交互、商店和坊市都复用同一套物品识别方式。

不负责内容：
- 不处理交易、寄售和商店结算规则。
- 不定义具体效果执行；使用类物品的数值效果由 `effect_executor.py` 处理。

主要输入 / 输出：
- 输入：玩家对象、item key / item id、live item 对象。
- 输出：物品定义、背包物品列表、新建物品对象或统一结果字典。

上游调用者：
- `quests.py`
- `battle.py`
- `world_objects.py`
- `shops.py` / `market.py` / `trade.py`

排错优先入口：
- `get_item_definition_for_object`
- `find_item`
- `create_item`
- `create_loot`
- `refine_item`
- `use_item`
"""

from evennia.utils.create import create_object

from .content_loader import load_content
from .effect_executor import execute_effect
from .player_stats import apply_exp


ITEM_DEFINITIONS = load_content("items")
ITEM_DEFINITIONS_BY_ID = {
    item_data["id"]: {"key": item_key, **item_data}
    for item_key, item_data in ITEM_DEFINITIONS.items()
    if item_data.get("id")
}


def get_item_definition(item_key):
    return ITEM_DEFINITIONS.get(item_key)


def get_item_definition_by_id(item_id):
    return ITEM_DEFINITIONS_BY_ID.get(item_id)


def get_item_definition_for_object(item):
    item_id = getattr(item.db, "item_id", None)
    if item_id:
        item_def = get_item_definition_by_id(item_id)
        if item_def:
            return item_def
    # 优先用 item_id 反查定义，避免玩家改名、奖励改 desc 后丢失配置绑定。
    # 只有老物品或缺少 item_id 的对象才退回 key 匹配。
    return get_item_definition(item.key)


def resolve_item_key(item_key=None, item_id=None):
    if item_key:
        return item_key
    item_def = get_item_definition_by_id(item_id)
    return item_def["key"] if item_def else None


def get_inventory_items(caller):
    return [
        obj
        for obj in caller.contents_get(content_type="object")
        if getattr(obj.db, "is_item", False) and getattr(obj, "location", None) == caller
    ]


def find_item(caller, item_name=None, item_id=None):
    for obj in get_inventory_items(caller):
        if item_id and getattr(obj.db, "item_id", None) == item_id:
            return obj
        if item_name and obj.key == item_name:
            return obj
    return None


def create_item(caller, key, desc=None):
    item = create_object("typeclasses.items.Item", key=key, location=caller)
    item_def = get_item_definition(key)
    item.db.desc = desc or (item_def["desc"] if item_def else None)
    item.db.item_id = item_def.get("id") if item_def else None
    return item


def create_loot(caller, key=None, item_id=None, desc=None):
    # 掉落与奖励当前共用同一套创建逻辑，但保留两个入口名称，
    # 这样调用方表达意图更清晰，后续若要分开埋点或特殊标记也不用回改所有调用点。
    resolved_key = resolve_item_key(item_key=key, item_id=item_id)
    return create_item(caller, resolved_key, desc=desc) if resolved_key else None


def create_reward_item(caller, key=None, item_id=None, desc=None):
    resolved_key = resolve_item_key(item_key=key, item_id=item_id)
    return create_item(caller, resolved_key, desc=desc) if resolved_key else None


def refine_item(caller, item):
    item_def = get_item_definition_for_object(item)
    refine_exp = item_def.get("refine_exp") if item_def else None
    if not refine_exp:
        return {"ok": False, "reason": "not_refinable"}

    old_realm, new_realm, exp = apply_exp(caller, refine_exp)
    item_key = item.key
    item.delete()
    return {
        "ok": True,
        "item_key": item_key,
        "gain": refine_exp,
        "old_realm": old_realm,
        "new_realm": new_realm,
        "exp": exp,
    }


def use_item(caller, item):
    item_def = get_item_definition_for_object(item)
    use_effect = item_def.get("use_effect") if item_def else None
    if not use_effect:
        return {"ok": False, "reason": "not_usable"}

    result = execute_effect(caller, use_effect)
    # 只有效果执行成功才销毁物品，避免因为门禁或参数错误把道具直接吞掉。
    if result["ok"]:
        item.delete()
    return result
