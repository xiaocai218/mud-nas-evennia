"""Simple quest state helpers."""


GUIDE_QUEST = "guide_dummy_trial"


def get_quest_state(caller):
    return caller.db.guide_quest or "not_started"


def start_guide_quest(caller):
    caller.db.guide_quest = "started"
    caller.db.guide_quest_dummy_kill = False


def mark_dummy_kill(caller):
    if get_quest_state(caller) == "started":
        caller.db.guide_quest_dummy_kill = True


def can_complete_guide_quest(caller):
    return get_quest_state(caller) == "started" and bool(caller.db.guide_quest_dummy_kill)


def complete_guide_quest(caller):
    caller.db.guide_quest = "completed"
