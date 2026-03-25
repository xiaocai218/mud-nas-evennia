"""JSON 内容加载与校验入口。

负责内容：
- 从 `world/data/*.json` 读取静态内容。
- 提供按内容类型列举、按 key/id 查找、缓存重载与一致性校验。
- 为 commands / systems / devtools 提供统一内容入口，减少各模块自己拼路径。

不负责内容：
- 不承担业务语义解释；任务、敌人、对象等规则仍在各自系统模块中。
- 不做运行态对象刷新；重载缓存之后，live object 是否同步由上层决定。

主要输入 / 输出：
- 输入：内容名、可选 lookup。
- 输出：原始 JSON 数据、平铺记录列表、摘要信息、校验问题列表。

上游调用者：
- `quests.py`、`help_content.py`、`npc_routes.py` 等系统模块。
- `devtools.py` 的内容查看 / 重载 / 校验命令。

排错优先入口：
- `load_content`
- `reload_content`
- `get_content_records`
- `find_content_record`
- `validate_content`
"""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "world" / "data"
_CONTENT_CACHE = {}
CONTENT_SPECS = {
    "items": {"source": "items", "container": None, "kind": "dict", "key_field": "key", "id_field": "id"},
    "enemies": {"source": "enemies", "container": None, "kind": "dict", "key_field": "enemy_key", "id_field": "id"},
    "battle_cards": {"source": "battle_cards", "container": None, "kind": "dict", "key_field": "card_key", "id_field": "id"},
    "areas": {"source": "areas", "container": None, "kind": "dict", "key_field": "area_key", "id_field": "id"},
    "area_exits": {"source": "area_exits", "container": None, "kind": "dict", "key_field": "area_exit_key", "id_field": "id"},
    "rooms": {"source": "rooms", "container": "rooms", "kind": "dict", "key_field": "room_key", "id_field": "content_id"},
    "npcs": {"source": "npcs", "container": "npcs", "kind": "list", "key_field": "key", "id_field": "id"},
    "objects": {"source": "objects", "container": "objects", "kind": "list", "key_field": "key", "id_field": "id"},
    "shops": {"source": "shops", "container": None, "kind": "dict", "key_field": "shop_key", "id_field": "id"},
    "markets": {"source": "markets", "container": None, "kind": "dict", "key_field": "market_key", "id_field": "id"},
    "main_stages": {"source": "quests", "container": "main_stages", "kind": "dict", "key_field": "state", "id_field": "id"},
    "side_quests": {"source": "quests", "container": "side_quests", "kind": "dict", "key_field": "quest_key", "id_field": "id"},
}
VALID_NPC_ROUTE_ACTIONS = {
    "dialogue",
    "start_main_stage",
    "complete_main_stage",
    "complete_main_stage_realm_step",
    "start_side_quest",
    "complete_side_quest",
}
VALID_NPC_ROUTE_CONDITIONS = {
    "main_state_is",
    "main_stage_completable",
    "side_state_is",
    "side_quest_state_is",
    "side_quest_completable",
}


def load_content(name):
    if name not in _CONTENT_CACHE:
        path = DATA_DIR / f"{name}.json"
        with path.open("r", encoding="utf-8") as file_obj:
            _CONTENT_CACHE[name] = json.load(file_obj)
    return _CONTENT_CACHE[name]


def reload_content(name=None):
    if name is None:
        _CONTENT_CACHE.clear()
        return
    # 某些逻辑层暴露的是“逻辑视图名”，例如 main_stages/side_quests 实际都来自 quests.json。
    # 这里先折回 source，避免调用方误以为自己只重载了视图片段。
    if name in CONTENT_SPECS:
        name = CONTENT_SPECS[name]["source"]
    _CONTENT_CACHE.pop(name, None)


def list_content_names():
    return sorted(CONTENT_SPECS.keys())


def get_content_records(name):
    spec = CONTENT_SPECS.get(name)
    if not spec:
        return []

    data = load_content(spec["source"])
    container = data.get(spec["container"]) if spec["container"] else data
    if spec["kind"] == "dict":
        return [{spec["key_field"]: record_key, **record_data} for record_key, record_data in container.items()]
    return [{**record} for record in container]


def find_content_record(name, lookup):
    spec = CONTENT_SPECS.get(name)
    if not spec:
        return None

    for record in get_content_records(name):
        if record.get(spec["id_field"]) == lookup:
            return record
        if record.get(spec["key_field"]) == lookup:
            return record
    return None


def get_content_summary():
    summary = []
    for name in list_content_names():
        summary.append({"name": name, "count": len(get_content_records(name))})
    return summary


def validate_content():
    issues = []
    # 校验保持“跨文件引用完整性”优先，不尝试复刻全部业务规则。
    # 目标是快速发现坏引用、坏 key、坏 schema，而不是替代运行时测试。

    rooms_data = load_content("rooms").get("rooms", {})
    areas_data = load_content("areas")
    area_exit_data = load_content("area_exits")
    room_keys = set(rooms_data.keys())
    area_keys = set(areas_data.keys())
    object_ids = {
        obj.get("id")
        for obj in load_content("objects").get("objects", [])
        if obj.get("id")
    }
    room_content_ids = {
        room.get("content_id")
        for room in rooms_data.values()
        if room.get("content_id")
    }
    item_ids = {
        item.get("id")
        for item in load_content("items").values()
        if item.get("id")
    }
    effect_keys = set(load_content("effects").keys())
    npc_ids = {
        npc.get("id")
        for npc in load_content("npcs").get("npcs", [])
        if npc.get("id")
    }
    main_stage_states = set(load_content("quests").get("main_stages", {}).keys())
    side_quest_keys = set(load_content("quests").get("side_quests", {}).keys())
    dialogue_sections = load_content("dialogues")
    shop_ids = {
        shop.get("id")
        for shop in load_content("shops").values()
        if shop.get("id")
    }

    for room_key, room in rooms_data.items():
        area_id = room.get("area_id")
        if area_id and area_id not in area_keys:
            issues.append(f"rooms.{room_key}: area_id '{area_id}' 不存在")
        if area_id and room_key in room_keys and room_key not in areas_data.get(area_id, {}).get("rooms", []):
            issues.append(f"rooms.{room_key}: area_id '{area_id}' 未在 areas.{area_id}.rooms 中声明")

    for area_key, area in areas_data.items():
        for room_key in area.get("rooms", []):
            if room_key not in room_keys:
                issues.append(f"areas.{area_key}: room '{room_key}' 不存在")

    for exit_key, exit_data in area_exit_data.items():
        if exit_data.get("from_area") not in area_keys:
            issues.append(f"area_exits.{exit_key}: from_area '{exit_data.get('from_area')}' 不存在")
        if exit_data.get("to_area") not in area_keys:
            issues.append(f"area_exits.{exit_key}: to_area '{exit_data.get('to_area')}' 不存在")
        if exit_data.get("trigger_room") and exit_data["trigger_room"] not in room_keys:
            issues.append(f"area_exits.{exit_key}: trigger_room '{exit_data['trigger_room']}' 不存在")
        if exit_data.get("trigger_object_id") and exit_data["trigger_object_id"] not in object_ids:
            issues.append(f"area_exits.{exit_key}: trigger_object_id '{exit_data['trigger_object_id']}' 不存在")

    for enemy_key, enemy in load_content("enemies").items():
        room_id = enemy.get("room_id")
        if not room_id:
            room_id = ((enemy.get("progression") or {}).get("spawn_profile") or {}).get("room_id")
        if room_id and room_id not in room_keys:
            issues.append(f"enemies.{enemy_key}: room_id '{room_id}' 不存在")
        drop_item_id = enemy.get("drop_item_id")
        if not drop_item_id:
            drop_item_id = (enemy.get("enemy_meta") or {}).get("drop_item_id")
        if drop_item_id and drop_item_id not in item_ids:
            issues.append(f"enemies.{enemy_key}: drop_item_id '{drop_item_id}' 不存在")

    for npc in load_content("npcs").get("npcs", []):
        room_id = npc.get("room_id")
        if room_id and room_id not in room_keys and room_id not in room_content_ids:
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: room_id '{room_id}' 不存在")
        attrs = npc.get("attrs") or {}
        npc_meta = npc.get("npc_meta") or {}
        identity = npc.get("identity") or {}
        progression = npc.get("progression") or {}
        talk_route = attrs.get("talk_route") or npc_meta.get("talk_route")
        if talk_route and talk_route not in load_content("npc_routes"):
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: talk_route '{talk_route}' 不存在")
        shop_id = attrs.get("shop_id") or npc_meta.get("shop_id")
        if shop_id and shop_id not in shop_ids:
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: shop_id '{shop_id}' 不存在")
        if identity and identity.get("kind") not in {None, "npc"}:
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: identity.kind 必须为 'npc'")
        if progression and (progression.get("spawn_profile") or {}).get("room_id") not in {None, room_id}:
            issues.append(
                f"npcs.{npc.get('id') or npc.get('key')}: progression.spawn_profile.room_id 与 room_id 不一致"
            )

    for obj in load_content("objects").get("objects", []):
        obj_name = obj.get("id") or obj.get("key")
        room_id = obj.get("room_id")
        if room_id and room_id not in room_keys:
            issues.append(f"objects.{obj_name}: room_id '{room_id}' 不存在")
        attrs = obj.get("attrs", {})
        gather_config = attrs.get("gather_config", {})
        if gather_config.get("gather_item_id") and gather_config["gather_item_id"] not in item_ids:
            issues.append(f"objects.{obj_name}: gather_item_id '{gather_config['gather_item_id']}' 不存在")
        trigger_effect = attrs.get("trigger_effect", {})
        if trigger_effect.get("room_id") and trigger_effect["room_id"] not in room_content_ids:
            issues.append(f"objects.{obj_name}: trigger_effect.room_id '{trigger_effect['room_id']}' 不存在")
        if trigger_effect.get("buff_key"):
            if trigger_effect["buff_key"] not in effect_keys:
                issues.append(f"objects.{obj_name}: buff_key '{trigger_effect['buff_key']}' 不存在")

    for item_key, item in load_content("items").items():
        use_effect = item.get("use_effect", {})
        if use_effect.get("buff_key") and use_effect["buff_key"] not in effect_keys:
            issues.append(f"items.{item_key}: use_effect.buff_key '{use_effect['buff_key']}' 不存在")

    for shop_key, shop in load_content("shops").items():
        if shop.get("room_id") and shop["room_id"] not in room_keys:
            issues.append(f"shops.{shop_key}: room_id '{shop['room_id']}' 不存在")
        if shop.get("npc_id") and shop["npc_id"] not in npc_ids:
            issues.append(f"shops.{shop_key}: npc_id '{shop['npc_id']}' 不存在")
        for index, entry in enumerate(shop.get("inventory", []), start=1):
            item_id = entry.get("item_id")
            if item_id and item_id not in item_ids:
                issues.append(f"shops.{shop_key}.inventory[{index}]: item_id '{item_id}' 不存在")

    for market_key, market in load_content("markets").items():
        if market.get("room_id") and market["room_id"] not in room_keys and market["room_id"] not in room_content_ids:
            issues.append(f"markets.{market_key}: room_id '{market['room_id']}' 不存在")
        if not market.get("key"):
            issues.append(f"markets.{market_key}: 缺少 key")
        if int(market.get("visible_listings", 0) or 0) <= 0:
            issues.append(f"markets.{market_key}: visible_listings 必须大于 0")
        if int(market.get("listing_ttl_seconds", 0) or 0) <= 0:
            issues.append(f"markets.{market_key}: listing_ttl_seconds 必须大于 0")

    quests = load_content("quests")
    for state, stage in quests.get("main_stages", {}).items():
        if stage.get("giver_npc_id") and stage["giver_npc_id"] not in npc_ids and stage["giver_npc_id"] not in object_ids:
            issues.append(f"quests.main_stages.{state}: giver_npc_id '{stage['giver_npc_id']}' 不存在")
        reward_item = stage.get("reward_item", {})
        if reward_item.get("item_id") and reward_item["item_id"] not in item_ids:
            issues.append(f"quests.main_stages.{state}: reward_item.item_id '{reward_item['item_id']}' 不存在")
        complete_to = stage.get("complete_to")
        if complete_to and complete_to not in main_stage_states and complete_to not in {"completed", "stage_one_done", "stage_three_ready"}:
            issues.append(f"quests.main_stages.{state}: complete_to '{complete_to}' 未声明")

    for quest_key, quest in quests.get("side_quests", {}).items():
        if quest.get("giver_npc_id") and quest["giver_npc_id"] not in npc_ids:
            issues.append(f"quests.side_quests.{quest_key}: giver_npc_id '{quest['giver_npc_id']}' 不存在")
        if quest.get("required_item_id") and quest["required_item_id"] not in item_ids:
            issues.append(f"quests.side_quests.{quest_key}: required_item_id '{quest['required_item_id']}' 不存在")
        reward_item = quest.get("reward_item", {})
        if reward_item.get("item_id") and reward_item["item_id"] not in item_ids:
            issues.append(f"quests.side_quests.{quest_key}: reward_item.item_id '{reward_item['item_id']}' 不存在")
        if not quest.get("state_attr") or not quest.get("start_state") or not quest.get("completed_state"):
            issues.append(f"quests.side_quests.{quest_key}: 缺少 state_attr/start_state/completed_state")

    for route_key, route in load_content("npc_routes").items():
        fallback = route.get("fallback_dialogue")
        if fallback and not _dialogue_exists(dialogue_sections, fallback):
            issues.append(f"npc_routes.{route_key}: fallback_dialogue '{fallback}' 不存在")
        for index, step in enumerate(route.get("steps", []), start=1):
            condition = step.get("condition", {})
            unknown_conditions = [key for key in condition if key not in VALID_NPC_ROUTE_CONDITIONS]
            if unknown_conditions:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: 未知 condition {unknown_conditions}")
            if "side_quest_state_is" in condition:
                side_condition = condition["side_quest_state_is"]
                quest_key = side_condition.get("quest")
                state = side_condition.get("state")
                if not quest_key or quest_key not in side_quest_keys:
                    issues.append(f"npc_routes.{route_key}.steps[{index}]: side_quest_state_is.quest '{quest_key}' 不存在")
                if not state:
                    issues.append(f"npc_routes.{route_key}.steps[{index}]: side_quest_state_is.state 缺失")
            action = step.get("action", {})
            action_type = action.get("type")
            if action_type not in VALID_NPC_ROUTE_ACTIONS:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: 未知 action.type '{action_type}'")
                continue
            dialogue = action.get("dialogue")
            if dialogue and not _dialogue_exists(dialogue_sections, dialogue):
                issues.append(f"npc_routes.{route_key}.steps[{index}]: dialogue '{dialogue}' 不存在")
            if action_type in {"start_main_stage", "complete_main_stage", "complete_main_stage_realm_step"} and action.get("stage") not in main_stage_states:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: stage '{action.get('stage')}' 不存在")
            if action_type in {"start_side_quest", "complete_side_quest"} and action.get("quest") not in side_quest_keys:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: quest '{action.get('quest')}' 不存在")

    return issues


def _dialogue_exists(dialogue_sections, dotted_key):
    if "." not in dotted_key:
        return False
    section, key = dotted_key.split(".", 1)
    return bool(dialogue_sections.get(section, {}).get(key))
