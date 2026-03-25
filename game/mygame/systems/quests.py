"""Quest metadata and state helpers for the starter quest chain."""

from systems.chat import send_system_message
from systems.content_loader import load_content
from systems.enemy_model import get_enemy_quest_flag
from systems.items import create_reward_item, find_item
from systems.player_stats import apply_exp
from systems.teams import get_same_area_team_members, get_team_member_characters


STAGE_ONE = "stage_one_started"
STAGE_ONE_DONE = "stage_one_done"
STAGE_TWO = "stage_two_started"
STAGE_THREE_READY = "stage_three_ready"
STAGE_THREE = "stage_three_started"
ROOT_CHOICE_READY = "root_choice_ready"
QI_GUIDANCE_READY = "qi_guidance_ready"
COMPLETED = "completed"

NOT_STARTED = "not_started"
ASCENSION_PLATFORM_STATES = frozenset({ROOT_CHOICE_READY, QI_GUIDANCE_READY})


QUEST_DATA = load_content("quests")
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


def has_completed_trial_rewards(caller):
    return bool(getattr(caller.db, "guide_quest_stage_two_rewarded", False)) and bool(
        getattr(caller.db, "guide_quest_stage_three_rewarded", False)
    )


def has_awakened_spiritual_root(caller):
    return bool(getattr(caller.db, "guide_quest_root_awakened", False))


def has_completed_qi_guidance(caller):
    return bool(getattr(caller.db, "guide_quest_qi_guided", False))


def is_waiting_for_root_choice(caller):
    return get_quest_state(caller) == ROOT_CHOICE_READY


def is_waiting_for_qi_guidance(caller):
    return get_quest_state(caller) == QI_GUIDANCE_READY


def can_use_spirit_stone(caller):
    return is_waiting_for_root_choice(caller) or has_awakened_spiritual_root(caller)


def has_completed_intro_trials(caller):
    state = get_quest_state(caller)
    if state == COMPLETED:
        return has_completed_trial_rewards(caller) and has_completed_qi_guidance(caller)
    return state in ASCENSION_PLATFORM_STATES


def can_access_ascension_platform(caller):
    return has_completed_intro_trials(caller)


def get_main_stage_summary(state, prefix="主线已更新"):
    stage = get_stage_data(state)
    if not stage:
        return f"{prefix}。"
    return f"{prefix}：{stage['title']} - {stage['objective']}"


def get_side_quest_state(caller, quest_key=None):
    if quest_key:
        quest = get_side_quest_data(quest_key)
        if not quest:
            return NOT_STARTED
        state_attr = quest.get("state_attr")
        if not state_attr:
            return NOT_STARTED
        return getattr(caller.db, state_attr, NOT_STARTED) or NOT_STARTED

    for quest_key in SIDE_QUEST_DATA:
        state = get_side_quest_state(caller, quest_key)
        if state != NOT_STARTED:
            return state
    return NOT_STARTED


def get_side_quest_data(quest_key):
    return SIDE_QUEST_DATA.get(quest_key)


def get_side_quest_summary(quest_key, prefix="支线已接取"):
    quest = get_side_quest_data(quest_key)
    if not quest:
        return f"{prefix}。"
    return f"{prefix}：{quest['title']} - {quest['objective']}"


def get_side_quest_state_attr(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("state_attr") if quest else None


def get_side_quest_start_state(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("start_state") if quest else None


def get_side_quest_completed_state(quest_key):
    quest = get_side_quest_data(quest_key)
    return quest.get("completed_state") if quest else None


def get_started_side_quest_keys(caller, include_completed=True):
    started = []
    for quest_key, quest in SIDE_QUEST_DATA.items():
        state = get_side_quest_state(caller, quest_key)
        if state == NOT_STARTED:
            continue
        if not include_completed and state == quest.get("completed_state"):
            continue
        started.append(quest_key)
    return started


def get_active_side_quest_key(caller):
    active = get_started_side_quest_keys(caller, include_completed=False)
    if active:
        return active[0]
    started = get_started_side_quest_keys(caller, include_completed=True)
    return started[0] if started else None


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
    quest_keys = get_started_side_quest_keys(caller, include_completed=True)
    if not quest_keys:
        return None
    lines = []
    for quest_key in quest_keys:
        quest = SIDE_QUEST_DATA[quest_key]
        state = get_side_quest_state(caller, quest_key)
        if state == quest.get("completed_state"):
            lines.append(quest["completed_text"])
            continue
        has_item = "已获得" if bool(find_item(caller, item_name=quest.get("required_item"), item_id=quest.get("required_item_id"))) else "未获得"
        lines.append(
            "|g当前支线|n\n"
            f"任务名: {quest['title']}\n"
            f"目标: {quest['objective']} [{has_item}]\n"
            f"交付人: {quest['giver']}"
        )
    return "\n\n".join(lines)


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


def reset_all_quest_progress(caller):
    caller.db.guide_quest = NOT_STARTED

    reset_attrs = set()
    for stage in QUEST_STAGE_DATA.values():
        progress_attr = stage.get("progress_attr")
        if progress_attr:
            reset_attrs.add(progress_attr)
        for attr in stage.get("start_resets", []):
            reset_attrs.add(attr)
        reward_flag = stage.get("reward_flag")
        if reward_flag:
            reset_attrs.add(reward_flag)

    for attr in reset_attrs:
        setattr(caller.db, attr, False)

    for quest in SIDE_QUEST_DATA.values():
        state_attr = quest.get("state_attr")
        if state_attr:
            setattr(caller.db, state_attr, NOT_STARTED)

    return {
        "main_state": NOT_STARTED,
        "reset_attrs": sorted(reset_attrs),
        "side_quests": sorted(
            quest_key for quest_key, quest in SIDE_QUEST_DATA.items() if quest.get("state_attr")
        ),
    }


def notify_team_main_stage_completed(caller, state):
    stage = get_stage_data(state)
    if not stage:
        return False
    teammates = get_team_member_characters(caller, include_self=False)
    if not teammates:
        return False
    send_system_message(
        f"{caller.key} 已完成主线交付“{stage['title']}”，可继续推进后续引导。",
        recipients=teammates,
        code="quest_team_completed",
    )
    return True


def set_main_quest_state(caller, state):
    stage = get_stage_data(state)
    if stage:
        for attr in stage.get("start_resets", []):
            setattr(caller.db, attr, False)
    caller.db.guide_quest = state


def prepare_root_choice_state(caller):
    caller.db.guide_quest_stage_two_rewarded = True
    caller.db.guide_quest_stage_three_rewarded = True
    caller.db.guide_quest_root_awakened = False
    caller.db.guide_quest_qi_guided = False
    set_main_quest_state(caller, ROOT_CHOICE_READY)
    return caller.db.guide_quest


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
    if state_attr and get_side_quest_state(caller, quest_key) != start_state:
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
    quest_flag = get_enemy_quest_flag(target)
    expected = COMBAT_PROGRESS_FLAGS.get(quest_flag)
    if not expected:
        return {"updated": [], "shared": []}

    state = expected["state"]
    progress_attr = expected["progress_attr"]
    updated = []
    if get_quest_state(caller) == state:
        if not bool(getattr(caller.db, progress_attr, False)):
            setattr(caller.db, progress_attr, True)
            updated.append(caller)

    shared = []
    teammates = get_same_area_team_members(caller, include_self=False)
    for teammate in teammates:
        if get_quest_state(teammate) != state:
            continue
        if bool(getattr(teammate.db, progress_attr, False)):
            continue
        setattr(teammate.db, progress_attr, True)
        updated.append(teammate)
        shared.append(teammate)

    if updated:
        recipients = []
        seen_ids = set()
        for recipient in [caller] + teammates:
            recipient_id = getattr(recipient, "id", None) or getattr(recipient, "pk", None)
            if recipient_id in seen_ids:
                continue
            seen_ids.add(recipient_id)
            recipients.append(recipient)
        if shared:
            send_system_message(
                f"{caller.key} 击败 {target.key}，队伍协同推进任务。同步队友：{'、'.join(member.key for member in shared)}。",
                recipients=recipients,
                code="quest_team_progress",
            )
        else:
            send_system_message(
                f"{caller.key} 击败 {target.key}，任务进度已更新。",
                recipients=recipients,
                code="quest_progress",
            )
    return {"updated": updated, "shared": shared}


def can_complete_main_stage(caller, state):
    stage = get_stage_data(state)
    if not stage or get_quest_state(caller) != state:
        return False
    progress_attr = stage.get("progress_attr")
    if not progress_attr:
        return False
    return bool(getattr(caller.db, progress_attr, False))


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


def mark_root_awakened(caller):
    caller.db.guide_quest_root_awakened = True
    caller.db.guide_quest = QI_GUIDANCE_READY
    return caller.db.guide_quest


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
