"""NPC talk route configuration helpers."""

from systems.chat import notify_player
from systems.content_loader import load_content
from systems.dialogues import get_dialogue
from systems.quests import (
    can_complete_main_stage,
    can_complete_side_quest,
    complete_main_stage,
    complete_side_quest,
    get_main_stage_summary,
    get_quest_state,
    get_side_quest_summary,
    get_side_quest_state,
    grant_side_quest_rewards,
    grant_stage_rewards,
    notify_team_main_stage_completed,
    start_side_quest,
    set_main_quest_state,
)


NPC_ROUTES = load_content("npc_routes")


def get_npc_route(route_key):
    return NPC_ROUTES.get(route_key)


def _match_condition(caller, condition):
    if "main_state_is" in condition and get_quest_state(caller) != condition["main_state_is"]:
        return False
    if "main_stage_completable" in condition and not can_complete_main_stage(caller, condition["main_stage_completable"]):
        return False
    if "side_state_is" in condition and get_side_quest_state(caller) != condition["side_state_is"]:
        return False
    if "side_quest_state_is" in condition:
        side_condition = condition["side_quest_state_is"]
        quest_key = side_condition.get("quest")
        state = side_condition.get("state")
        if not quest_key or get_side_quest_state(caller, quest_key) != state:
            return False
    if "side_quest_completable" in condition and not can_complete_side_quest(caller, condition["side_quest_completable"]):
        return False
    return True


def _build_dialogue_kwargs(action, reward):
    kwargs = {}
    for key, value in action.get("dialogue_kwargs", {}).items():
        if value == "{reward_key}" and reward:
            kwargs[key] = reward.key
        else:
            kwargs[key] = value
    return kwargs


def _send_reward_messages(caller, action, rewards):
    reward = rewards["reward"]
    summary = f"|g{action['reward_label']}|n: 修为 +{rewards['reward_exp']}"
    if reward:
        summary += f"，获得 |w{reward.key}|n。"
    else:
        summary += "。"
    caller.msg(summary)
    if rewards["new_realm"] != rewards["old_realm"] and action.get("realm_up_text"):
        caller.msg(f"|y{action['realm_up_text'].format(new_realm=rewards['new_realm'])}|n")


def _perform_action(caller, action):
    handler = ACTION_HANDLERS.get(action["type"])
    if not handler:
        return False
    return handler(caller, action)


def _handle_dialogue(caller, action):
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1)))
    return True


def _handle_start_main_stage(caller, action):
    set_main_quest_state(caller, action["stage"])
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1)))
    notify_player(caller, get_main_stage_summary(action["stage"], prefix="主线已更新"), code="quest_main_started")
    return True


def _handle_complete_main_stage(caller, action):
    complete_main_stage(caller, action["stage"])
    rewards = grant_stage_rewards(caller, action["stage"])
    reward = rewards["reward"]
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1), **_build_dialogue_kwargs(action, reward)))
    _send_reward_messages(caller, action, rewards)
    notify_team_main_stage_completed(caller, action["stage"])
    notify_player(caller, get_main_stage_summary(action["stage"], prefix="主线已推进"), code="quest_main_completed")
    return True


def _handle_start_side_quest(caller, action):
    start_side_quest(caller, action["quest"])
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1)))
    notify_player(caller, get_side_quest_summary(action["quest"], prefix="支线已接取"), code="quest_side_started")
    return True


def _handle_complete_side_quest(caller, action):
    complete_side_quest(caller, action["quest"])
    rewards = grant_side_quest_rewards(caller, action["quest"])
    reward = rewards["reward"]
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1), **_build_dialogue_kwargs(action, reward)))
    _send_reward_messages(caller, action, rewards)
    notify_player(caller, get_side_quest_summary(action["quest"], prefix="支线已完成"), code="quest_side_completed")
    return True


ACTION_HANDLERS = {
    "dialogue": _handle_dialogue,
    "start_main_stage": _handle_start_main_stage,
    "complete_main_stage": _handle_complete_main_stage,
    "start_side_quest": _handle_start_side_quest,
    "complete_side_quest": _handle_complete_side_quest,
}


def run_npc_route(caller, route_key):
    route = get_npc_route(route_key)
    if not route:
        return False

    for step in route.get("steps", []):
        if _match_condition(caller, step["condition"]):
            return _perform_action(caller, step["action"])

    fallback = route.get("fallback_dialogue")
    if fallback:
        caller.msg(get_dialogue(*fallback.split(".", 1)))
        return True
    return False
