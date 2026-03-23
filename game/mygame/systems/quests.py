"""Simple quest state helpers."""


STAGE_ONE = "stage_one_started"
STAGE_ONE_DONE = "stage_one_done"
STAGE_TWO = "stage_two_started"
COMPLETED = "completed"


def get_quest_state(caller):
    state = caller.db.guide_quest or "not_started"
    if state == COMPLETED and not bool(caller.db.guide_quest_stage_two_rewarded):
        return STAGE_ONE_DONE
    return state


def start_guide_quest(caller):
    caller.db.guide_quest = STAGE_ONE
    caller.db.guide_quest_dummy_kill = False


def unlock_second_stage(caller):
    caller.db.guide_quest = STAGE_TWO
    caller.db.guide_quest_stone_kill = False


def mark_combat_kill(caller, target):
    quest_flag = getattr(target.db, "quest_flag", None)
    state = get_quest_state(caller)

    if quest_flag == "dummy_kill" and state == STAGE_ONE:
        caller.db.guide_quest_dummy_kill = True
    if quest_flag == "stone_kill" and state == STAGE_TWO:
        caller.db.guide_quest_stone_kill = True


def can_complete_stage_one(caller):
    return get_quest_state(caller) == STAGE_ONE and bool(caller.db.guide_quest_dummy_kill)


def can_complete_stage_two(caller):
    return get_quest_state(caller) == STAGE_TWO and bool(caller.db.guide_quest_stone_kill)


def complete_stage_one(caller):
    caller.db.guide_quest = STAGE_ONE_DONE


def complete_stage_two(caller):
    caller.db.guide_quest = COMPLETED
    caller.db.guide_quest_stage_two_rewarded = True
