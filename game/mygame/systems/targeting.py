"""Shared target lookup helpers.

These helpers normalize the most common "find something near the caller"
patterns used by commands and action handlers. The goal is to keep lookup
rules in one place instead of duplicating small `caller.search(...)`
wrappers across modules.
"""

from systems.enemy_model import is_enemy
from systems.npc_model import is_npc


def find_target_in_room(caller, target_name):
    """Find a nearby target by name using the caller's current location."""
    if not caller or not target_name:
        return None
    try:
        results = caller.search(target_name, location=caller.location, quiet=True)
    except TypeError:
        # Test doubles and some lightweight wrappers may not accept `quiet`.
        results = caller.search(target_name, location=caller.location)
    if isinstance(results, (list, tuple)):
        return results[0] if results else None
    return results


def find_npc_in_room(caller, target_name):
    """Find a nearby NPC target."""
    target = find_target_in_room(caller, target_name)
    if target and is_npc(target):
        return target
    return None


def find_enemy_in_room(caller, target_name):
    """Find a nearby enemy target."""
    target = find_target_in_room(caller, target_name)
    if target and is_enemy(target):
        return target
    return None
