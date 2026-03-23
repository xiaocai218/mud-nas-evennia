"""Quest metadata and state helpers for the starter quest chain."""

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

QUEST_STAGE_DATA = {
    STAGE_ONE: {
        "title": "渡口试手",
        "objective": "击败一次青木傀儡",
        "giver": "守渡老人",
        "progress_attr": "guide_quest_dummy_kill",
        "reward_exp": 20,
        "reward_item": ("渡口药包", "守渡老人交给你的简陋药包，带着些草木辛气，也许日后会派上用场。"),
    },
    STAGE_TWO: {
        "title": "石阶试锋",
        "objective": "击败一次山石傀儡",
        "giver": "守渡老人",
        "progress_attr": "guide_quest_stone_kill",
        "reward_exp": 30,
        "reward_item": ("石阶护符", "一枚刻着浅淡山纹的护符，触手微凉，像是能让人稍稍安定心神。"),
    },
    STAGE_THREE: {
        "title": "溪谷巡查",
        "objective": "击败一次雾行山魈",
        "giver": "巡山弟子",
        "progress_attr": "guide_quest_mist_kill",
        "reward_exp": 36,
        "reward_item": ("巡山木牌", "一块刻着巡山纹记的木牌，边角被磨得光滑，象征你已通过这段入门试炼。"),
    },
}

SIDE_QUEST_DATA = {
    "herb_delivery": {
        "title": "雾露代药",
        "giver": "药庐学徒",
        "objective": "交付一个雾露果",
        "required_item": "雾露果",
        "reward_exp": 18,
        "reward_item": ("回春散", "药庐学徒分装给你的细纸药包，药香清苦，适合在重伤时应急。"),
    }
}

QUEST_STATUS_TEXT = {
    NOT_STARTED: "你暂时还没有接到任务。可以试试 |w交谈 守渡老人|n。",
    STAGE_ONE_DONE: "|g当前主线|n\n任务名: 渡口试手\n状态: 已完成，等待后续指引\n交付人: 守渡老人",
    STAGE_THREE_READY: "|g当前主线|n\n任务名: 溪谷巡查\n状态: 待接取\n提示: 前往溪谷栈道，交谈 巡山弟子",
    COMPLETED: "|g当前主线|n\n任务名: 入门试炼\n状态: 已全部完成\n守渡老人已经认可你完成了三段基础试炼。",
}

COMBAT_PROGRESS_FLAGS = {
    "dummy_kill": (STAGE_ONE, "guide_quest_dummy_kill"),
    "stone_kill": (STAGE_TWO, "guide_quest_stone_kill"),
    "mist_kill": (STAGE_THREE, "guide_quest_mist_kill"),
}


def get_quest_state(caller):
    state = caller.db.guide_quest or NOT_STARTED
    if state == COMPLETED and not bool(caller.db.guide_quest_stage_two_rewarded):
        return STAGE_ONE_DONE
    if state == COMPLETED and bool(caller.db.guide_quest_stage_two_rewarded) and not bool(caller.db.guide_quest_stage_three_rewarded):
        return STAGE_THREE_READY
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
        return "|g当前支线|n\n任务名: 雾露代药\n状态: 已完成\n药庐学徒已经收下你带回的雾露果。"

    quest = SIDE_QUEST_DATA["herb_delivery"]
    has_item = "已获得" if bool(find_item(caller, quest["required_item"])) else "未获得"
    return (
        "|g当前支线|n\n"
        f"任务名: {quest['title']}\n"
        f"目标: {quest['objective']} [{has_item}]\n"
        f"交付人: {quest['giver']}"
    )


def grant_stage_rewards(caller, stage):
    data = get_stage_data(stage)
    if not data:
        return None

    old_realm, new_realm, exp = apply_exp(caller, data["reward_exp"])
    reward = None
    if data.get("reward_item"):
        reward_key, reward_desc = data["reward_item"]
        reward = create_reward_item(caller, reward_key, reward_desc)
    return {
        "reward_exp": data["reward_exp"],
        "reward": reward,
        "old_realm": old_realm,
        "new_realm": new_realm,
        "exp": exp,
    }


def grant_side_quest_rewards(caller, quest_key):
    data = SIDE_QUEST_DATA.get(quest_key)
    if not data:
        return None

    old_realm, new_realm, exp = apply_exp(caller, data["reward_exp"])
    reward = None
    if data.get("reward_item"):
        reward_key, reward_desc = data["reward_item"]
        reward = create_reward_item(caller, reward_key, reward_desc)
    return {
        "reward_exp": data["reward_exp"],
        "reward": reward,
        "old_realm": old_realm,
        "new_realm": new_realm,
        "exp": exp,
    }


def start_guide_quest(caller):
    caller.db.guide_quest = STAGE_ONE
    caller.db.guide_quest_dummy_kill = False


def unlock_second_stage(caller):
    caller.db.guide_quest = STAGE_TWO
    caller.db.guide_quest_stone_kill = False


def start_third_stage(caller):
    caller.db.guide_quest = STAGE_THREE
    caller.db.guide_quest_mist_kill = False


def start_side_herb_quest(caller):
    caller.db.side_herb_quest = SIDE_HERB


def can_complete_side_herb_quest(caller):
    return get_side_quest_state(caller) == SIDE_HERB and bool(find_item(caller, SIDE_QUEST_DATA["herb_delivery"]["required_item"]))


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

    state, progress_attr = expected
    if get_quest_state(caller) == state:
        setattr(caller.db, progress_attr, True)


def can_complete_stage_one(caller):
    return get_quest_state(caller) == STAGE_ONE and bool(caller.db.guide_quest_dummy_kill)


def can_complete_stage_two(caller):
    return get_quest_state(caller) == STAGE_TWO and bool(caller.db.guide_quest_stone_kill)


def can_complete_stage_three(caller):
    return get_quest_state(caller) == STAGE_THREE and bool(caller.db.guide_quest_mist_kill)


def complete_stage_one(caller):
    caller.db.guide_quest = STAGE_ONE_DONE


def complete_stage_two(caller):
    caller.db.guide_quest = STAGE_THREE_READY
    caller.db.guide_quest_stage_two_rewarded = True


def complete_stage_three(caller):
    caller.db.guide_quest = COMPLETED
    caller.db.guide_quest_stage_three_rewarded = True
