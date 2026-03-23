"""Shared JSON content loading helpers."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "world" / "data"
_CONTENT_CACHE = {}
CONTENT_SPECS = {
    "items": {"source": "items", "container": None, "kind": "dict", "key_field": "key", "id_field": "id"},
    "enemies": {"source": "enemies", "container": None, "kind": "dict", "key_field": "enemy_key", "id_field": "id"},
    "rooms": {"source": "rooms", "container": "rooms", "kind": "dict", "key_field": "room_key", "id_field": "content_id"},
    "npcs": {"source": "npcs", "container": "npcs", "kind": "list", "key_field": "key", "id_field": "id"},
    "objects": {"source": "objects", "container": "objects", "kind": "list", "key_field": "key", "id_field": "id"},
    "main_stages": {"source": "quests", "container": "main_stages", "kind": "dict", "key_field": "state", "id_field": "id"},
    "side_quests": {"source": "quests", "container": "side_quests", "kind": "dict", "key_field": "quest_key", "id_field": "id"},
}
VALID_NPC_ROUTE_ACTIONS = {
    "dialogue",
    "start_main_stage",
    "complete_main_stage",
    "start_side_quest",
    "complete_side_quest",
}
VALID_NPC_ROUTE_CONDITIONS = {
    "main_state_is",
    "main_stage_completable",
    "side_state_is",
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

    room_keys = set(load_content("rooms").get("rooms", {}).keys())
    room_content_ids = {
        room.get("content_id")
        for room in load_content("rooms").get("rooms", {}).values()
        if room.get("content_id")
    }
    item_ids = {
        item.get("id")
        for item in load_content("items").values()
        if item.get("id")
    }
    npc_ids = {
        npc.get("id")
        for npc in load_content("npcs").get("npcs", [])
        if npc.get("id")
    }
    main_stage_states = set(load_content("quests").get("main_stages", {}).keys())
    side_quest_keys = set(load_content("quests").get("side_quests", {}).keys())
    dialogue_sections = load_content("dialogues")

    for enemy_key, enemy in load_content("enemies").items():
        room_id = enemy.get("room_id")
        if room_id and room_id not in room_keys:
            issues.append(f"enemies.{enemy_key}: room_id '{room_id}' 不存在")
        drop_item_id = enemy.get("drop_item_id")
        if drop_item_id and drop_item_id not in item_ids:
            issues.append(f"enemies.{enemy_key}: drop_item_id '{drop_item_id}' 不存在")

    for npc in load_content("npcs").get("npcs", []):
        room_id = npc.get("room_id")
        if room_id and room_id not in room_keys:
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: room_id '{room_id}' 不存在")
        talk_route = ((npc.get("attrs") or {}).get("talk_route"))
        if talk_route and talk_route not in load_content("npc_routes"):
            issues.append(f"npcs.{npc.get('id') or npc.get('key')}: talk_route '{talk_route}' 不存在")

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
            effects = load_content("effects")
            if trigger_effect["buff_key"] not in effects:
                issues.append(f"objects.{obj_name}: buff_key '{trigger_effect['buff_key']}' 不存在")

    quests = load_content("quests")
    for state, stage in quests.get("main_stages", {}).items():
        if stage.get("giver_npc_id") and stage["giver_npc_id"] not in npc_ids:
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
            action = step.get("action", {})
            action_type = action.get("type")
            if action_type not in VALID_NPC_ROUTE_ACTIONS:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: 未知 action.type '{action_type}'")
                continue
            dialogue = action.get("dialogue")
            if dialogue and not _dialogue_exists(dialogue_sections, dialogue):
                issues.append(f"npc_routes.{route_key}.steps[{index}]: dialogue '{dialogue}' 不存在")
            if action_type in {"start_main_stage", "complete_main_stage"} and action.get("stage") not in main_stage_states:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: stage '{action.get('stage')}' 不存在")
            if action_type in {"start_side_quest", "complete_side_quest"} and action.get("quest") not in side_quest_keys:
                issues.append(f"npc_routes.{route_key}.steps[{index}]: quest '{action.get('quest')}' 不存在")

    return issues


def _dialogue_exists(dialogue_sections, dotted_key):
    if "." not in dotted_key:
        return False
    section, key = dotted_key.split(".", 1)
    return bool(dialogue_sections.get(section, {}).get(key))
