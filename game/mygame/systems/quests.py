"""Quest metadata and state helpers for the starter quest chain."""

import json
from pathlib import Path

from systems.items import create_reward_item, find_item
from systems.player_stats import apply_exp


STAGE_ONE = "stage_one_started"
STAGE_ONE_DONE = "stage_one_done"
STAGE_TWO = "stage_two_started"
STAGE_THREE_READY = "stage_three_ready"
STAGE_THREE = "stage_three_started"
COMPLETED = "completed"

NOT_STARTED = "not_started"
QUEST_DATA_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "quests.json"


def _load_quest_data():
    with QUEST_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


QUEST_DATA = _load_quest_data()
MAIN_FLOW = QUEST_DATA["main_flow"]
QUEST_STAGE_DATA = QUEST_DATA["main_stages"]
SIDE_QUEST_DATA = QUEST_DATA["side_quests"]
QUEST_STATUS_TEXT = QUEST_DATA["main_status_text"]
COMBAT_PROGRESS_FLAGS = QUEST_DATA["combat_progress_flags"]
COMPATIBILITY_RULES = QUEST_DATA.get("compatibility", {}).get("main_state_overrides", [])


def get_quest_state(caller):
    state = caller.db.guide_quest or NOT_STARTED
    for rule in COMPATIBILITY_RULES:
        if state != rule["when_state"]:
            continue
        if any(not bool(getattr(caller.db, flag, False)) for flag in rule.get("required_flags", [])):
            continue
        if any(bool(getattr(caller.db, flag, False)) for flag in rule.get("missing_flags", [])):
            continue
        return rule["mapped_state"]
    return state


def get_stage_data(state):
    return QUEST_STAGE_DATA.get(state)


def get_side_quest_state(caller):
    for quest in SIDE_QUEST_DATA.values():
        state_attr = quest.get("state_attr")
        if state_attr:
            state = getattr(caller.db, state_attr, None)
            if state and state != NOT_STARTED:
                return state
    return NOT_STARTED


def get_side_quest_data(quest_key):
    return SIDE_QUEST_DATA.get(quest_key)


def get_side_quest_state_attr(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("state_attr") if quest else None


def get_side_quest_start_state(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("start_state") if quest else None


def get_side_quest_completed_state(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("completed_state") if quest else None


def get_active_side_quest_key(caller):
    for quest_key, quest in SIDE_QUEST_DATA.items():
        state_attr = quest.get("state_attr")
        if not state_attr:
            continue
        state = getattr(caller.db, state_attr, None)
        if state and state != NOT_STARTED:
            return quest_key
    return None


def get_quest_status_text(caller):
    lines = [get_main_quest_status_text(caller)]
    side_text = get_side_quest_status_text(caller)
    if side_text:
        lines.append(side_text)
    return "\n\n".join(lines)


def get_main_quest_status_text(caller):
    state = get_quest_state(caller)
    if state in QUEST_STATUS_TEXT:
        return QUEST_STATUS_TEXT[state]

    stage = get_stage_data(state)
    if not stage:
        return QUEST_STATUS_TEXT[COMPLETED]

    done = "已完成" if bool(getattr(caller.db, stage["progress_attr"], False)) else "未完成"
    return (
        "|g当前主线|n\n"
        f"任务名: {stage['title']}\n"
        f"目标: {stage['objective']} [{done}]\n"
        f"交付人: {stage['giver']}"
    )


def get_side_quest_status_text(caller):
    quest_key = get_active_side_quest_key(caller)
    if not quest_key:
        return None
    quest = SIDE_QUEST_DATA[quest_key]
    state = getattr(caller.db, quest.get("state_attr"), NOT_STARTED)
    if state == quest.get("completed_state"):
        return quest["completed_text"]
    has_item = "已获得" if bool(find_item(caller, item_name=quest.get("required_item"), item_id=quest.get("required_item_id"))) else "未获得"
    return (
        "|g当前支线|n\n"
        f"任务名: {quest['title']}\n"
        f"目标: {quest['objective']} [{has_item}]\n"
        f"交付人: {quest['giver']}"
    )


def _grant_rewards(caller, data):
    old_realm, new_realm, exp = apply_exp(caller, data["reward_exp"])
    reward = None
    if data.get("reward_item"):
        reward_key = data["reward_item"].get("key")
        reward_item_id = data["reward_item"].get("item_id")
        reward_desc = data["reward_item"]["desc"]
        reward = create_reward_item(caller, key=reward_key, item_id=reward_item_id, desc=reward_desc)
    return {
        "reward_exp": data["reward_exp"],
        "reward": reward,
        "old_realm": old_realm,
        "new_realm": new_realm,
        "exp": exp,
    }


def grant_stage_rewards(caller, stage):
    data = get_stage_data(stage)
    if not data:
        return None
    return _grant_rewards(caller, data)


def grant_side_quest_rewards(caller, quest_key):
    data = SIDE_QUEST_DATA.get(quest_key)
    if not data:
        return None
    return _grant_rewards(caller, data)


def set_main_quest_state(caller, state):
    stage = get_stage_data(state)
    if stage:
        for attr in stage.get("start_resets", []):
            setattr(caller.db, attr, False)
    caller.db.guide_quest = state


def start_guide_quest(caller):
    set_main_quest_state(caller, MAIN_FLOW["start_state"])


def unlock_second_stage(caller):
    set_main_quest_state(caller, STAGE_TWO)


def start_third_stage(caller):
    set_main_quest_state(caller, STAGE_THREE)


def start_side_quest(caller, quest_key):
    quest = get_side_quest_data(quest_key)
    if not quest:
        return
    state_attr = quest.get("state_attr")
    start_state = quest.get("start_state")
    if state_attr and start_state:
        setattr(caller.db, state_attr, start_state)


def can_complete_side_quest(caller, quest_key):
    quest = get_side_quest_data(quest_key)
    if not quest:
        return False
    state_attr = quest.get("state_attr")
    start_state = quest.get("start_state")
    if state_attr and getattr(caller.db, state_attr, NOT_STARTED) != start_state:
        return False
    return bool(
        find_item(caller, item_name=quest.get("required_item"), item_id=quest.get("required_item_id"))
    )


def complete_side_quest(caller, quest_key):
    quest = get_side_quest_data(quest_key)
    if not quest:
        return
    item = find_item(caller, item_name=quest.get("required_item"), item_id=quest.get("required_item_id"))
    if item:
        item.delete()
    state_attr = quest.get("state_attr")
    completed_state = quest.get("completed_state")
    if state_attr and completed_state:
        setattr(caller.db, state_attr, completed_state)


def mark_combat_kill(caller, target):
    quest_flag = getattr(target.db, "quest_flag", None)
    expected = COMBAT_PROGRESS_FLAGS.get(quest_flag)
    if not expected:
        return

    state = expected["state"]
    progress_attr = expected["progress_attr"]
    if get_quest_state(caller) == state:
        setattr(caller.db, progress_attr, True)


def can_complete_main_stage(caller, state):
    stage = get_stage_data(state)
    if not stage or get_quest_state(caller) != state:
        return False
    return bool(getattr(caller.db, stage["progress_attr"], False))


def complete_main_stage(caller, state):
    stage = get_stage_data(state)
    if not stage:
        return None

    next_state = stage["complete_to"]
    reward_flag = stage.get("reward_flag")
    caller.db.guide_quest = next_state
    if reward_flag:
        setattr(caller.db, reward_flag, True)
    return next_state


def can_complete_stage_one(caller):
    return can_complete_main_stage(caller, STAGE_ONE)


def can_complete_stage_two(caller):
    return can_complete_main_stage(caller, STAGE_TWO)


def can_complete_stage_three(caller):
    return can_complete_main_stage(caller, STAGE_THREE)


def complete_stage_one(caller):
    return complete_main_stage(caller, STAGE_ONE)


def complete_stage_two(caller):
    return complete_main_stage(caller, STAGE_TWO)


def complete_stage_three(caller):
    return complete_main_stage(caller, STAGE_THREE)
