"""Shared interaction error helpers for command and action layers.

This module keeps common interaction error codes and terminal-facing
fallback text in one place so NPC/person/relationship interactions do not
duplicate near-identical error handling across commands and APIs.
"""

from systems.dialogues import get_dialogue


INTERACTION_ERROR_MESSAGES = {
    "target_not_found": None,
    "target_not_talkable": "{target} 当前不能交谈。",
    "target_not_person": "{target} 暂时没有可查看的人物信息。",
    "npc_relationship_unavailable": "{target} 暂时没有可查看的关系信息。",
    "target_not_attackable": "{target} 当前不能攻击。",
}


def build_interaction_error(code, target=None, fallback=None):
    """Build a structured interaction error payload."""
    return {
        "code": code,
        "message": resolve_interaction_error_message(code, target=target, fallback=fallback),
    }


def resolve_interaction_error_message(code, target=None, fallback=None):
    """Resolve terminal-facing text for an interaction error code."""
    if code == "target_not_found":
        return get_dialogue("common", "not_found")
    template = INTERACTION_ERROR_MESSAGES.get(code)
    if template:
        return template.format(target=target or "目标")
    return fallback or "交互失败。"
