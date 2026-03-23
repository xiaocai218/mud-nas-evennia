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

SIDE_HERB = "side_herb_started"
SIDE_HERB_DONE = "side_herb_completed"

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
    return caller.db.side_herb_quest or NOT_STARTED


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
    state = get_side_quest_state(caller)
    if state == NOT_STARTED:
        return None
    if state == SIDE_HERB_DONE:
        return SIDE_QUEST_DATA["herb_delivery"]["completed_text"]

    quest = SIDE_QUEST_DATA["herb_delivery"]
    has_item = "已获得" if bool(find_item(caller, quest["required_item"])) else "未获得"
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
        reward_key = data["reward_item"]["key"]
        reward_desc = data["reward_item"]["desc"]
        reward = create_reward_item(caller, reward_key, reward_desc)
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


def start_side_herb_quest(caller):
    caller.db.side_herb_quest = SIDE_HERB


def can_complete_side_herb_quest(caller):
    quest = SIDE_QUEST_DATA["herb_delivery"]
    return get_side_quest_state(caller) == SIDE_HERB and bool(find_item(caller, quest["required_item"]))


def complete_side_herb_quest(caller):
    item = find_item(caller, SIDE_QUEST_DATA["herb_delivery"]["required_item"])
    if item:
        item.delete()
    caller.db.side_herb_quest = SIDE_HERB_DONE


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
