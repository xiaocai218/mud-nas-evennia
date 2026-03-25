"""NPC 交谈路由收口层。

负责内容：
- 从 `npc_routes.json` 读取 NPC 对话步骤，并按条件顺序匹配可执行动作。
- 把“交谈 -> 对话 / 接任务 / 交付 / 奖励 / 境界推进”收口到统一 handler 映射。
- 让 NPC 交互尽量走配置驱动，而不是把分支逻辑写死在命令层。

不负责内容：
- 不维护任务状态本体；主线 / 支线状态仍由 `quests.py` 负责。
- 不保存 NPC live object 状态；这里只消费 route key 和玩家当前状态。

主要输入 / 输出：
- 输入：玩家对象 `caller`、route key、route action 配置。
- 输出：是否成功命中并执行某条 route。

上游调用者：
- 主要由 `action_router.py` 和 `commands/social.py` 的交谈逻辑调用。

排错优先入口：
- `run_npc_route`
- `_match_condition`
- `_perform_action`
- `_handle_complete_main_stage`
- `_handle_complete_side_quest`
"""

from systems.chat import notify_player
from systems.character_model import promote_awakened_realm
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


def _handle_complete_main_stage_realm_step(caller, action):
    complete_main_stage(caller, action["stage"])
    sheet = promote_awakened_realm(caller)
    caller.msg(get_dialogue(*action["dialogue"].split(".", 1)))
    if action.get("reward_label"):
        caller.msg(f"|g{action['reward_label']}|n: 境界稳固至 {sheet['progression']['realm']}。")
    notify_player(caller, get_main_stage_summary(action["stage"], prefix="主线已完成"), code="quest_main_completed")
    return True


ACTION_HANDLERS = {
    "dialogue": _handle_dialogue,
    "start_main_stage": _handle_start_main_stage,
    "complete_main_stage": _handle_complete_main_stage,
    "complete_main_stage_realm_step": _handle_complete_main_stage_realm_step,
    "start_side_quest": _handle_start_side_quest,
    "complete_side_quest": _handle_complete_side_quest,
}


def run_npc_route(caller, route_key):
    route = get_npc_route(route_key)
    if not route:
        return False

    # route.steps 按顺序命中，前面的规则优先级更高。
    # 因此新增分支时应把“更具体、更窄”的条件放前面，fallback 或宽条件放后面，
    # 否则很容易出现玩家总是命中旧对话、无法进入交付分支的表象故障。
    for step in route.get("steps", []):
        if _match_condition(caller, step["condition"]):
            return _perform_action(caller, step["action"])

    fallback = route.get("fallback_dialogue")
    if fallback:
        caller.msg(get_dialogue(*fallback.split(".", 1)))
        return True
    return False
