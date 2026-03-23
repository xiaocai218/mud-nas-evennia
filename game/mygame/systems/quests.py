"""Quest metadata and state helpers for the starter quest chain."""


STAGE_ONE = "stage_one_started"
STAGE_ONE_DONE = "stage_one_done"
STAGE_TWO = "stage_two_started"
STAGE_THREE_READY = "stage_three_ready"
STAGE_THREE = "stage_three_started"
COMPLETED = "completed"

NOT_STARTED = "not_started"

QUEST_STAGE_DATA = {
    STAGE_ONE: {
        "title": "渡口试手",
        "objective": "击败一次青木傀儡",
        "giver": "守渡老人",
        "progress_attr": "guide_quest_dummy_kill",
    },
    STAGE_TWO: {
        "title": "石阶试锋",
        "objective": "击败一次山石傀儡",
        "giver": "守渡老人",
        "progress_attr": "guide_quest_stone_kill",
    },
    STAGE_THREE: {
        "title": "溪谷巡查",
        "objective": "击败一次雾行山魈",
        "giver": "巡山弟子",
        "progress_attr": "guide_quest_mist_kill",
    },
}

QUEST_STATUS_TEXT = {
    NOT_STARTED: "你暂时还没有接到任务。可以试试 |w交谈 守渡老人|n。",
    STAGE_ONE_DONE: "|g当前任务|n\n任务名: 渡口试手\n状态: 已完成，等待后续指引\n交付人: 守渡老人",
    STAGE_THREE_READY: "|g当前任务|n\n任务名: 溪谷巡查\n状态: 待接取\n提示: 前往溪谷栈道，交谈 巡山弟子",
    COMPLETED: "|g当前任务|n\n任务名: 入门试炼\n状态: 已全部完成\n守渡老人已经认可你完成了三段基础试炼。",
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


def get_quest_status_text(caller):
    state = get_quest_state(caller)
    if state in QUEST_STATUS_TEXT:
        return QUEST_STATUS_TEXT[state]

    stage = get_stage_data(state)
    if not stage:
        return QUEST_STATUS_TEXT[COMPLETED]

    done = "已完成" if bool(getattr(caller.db, stage["progress_attr"], False)) else "未完成"
    return (
        "|g当前任务|n\n"
        f"任务名: {stage['title']}\n"
        f"目标: {stage['objective']} [{done}]\n"
        f"交付人: {stage['giver']}"
    )


def start_guide_quest(caller):
    caller.db.guide_quest = STAGE_ONE
    caller.db.guide_quest_dummy_kill = False


def unlock_second_stage(caller):
    caller.db.guide_quest = STAGE_TWO
    caller.db.guide_quest_stone_kill = False


def start_third_stage(caller):
    caller.db.guide_quest = STAGE_THREE
    caller.db.guide_quest_mist_kill = False


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
