"""
Room

Rooms are simple containers that has no location of their own.
"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent
from systems.enemy_model import is_enemy
from systems.npc_model import is_npc


class Room(ObjectParent, DefaultRoom):
    """
    Basic project room typeclass.
    """

    def at_object_creation(self):
        super().at_object_creation()
        if not self.db.desc:
            self.db.desc = "这里暂时还很空旷，但已经能感觉到一丝灵气流转。"

    def return_appearance(self, looker, **kwargs):
        lines = [f"|c{self.key}|n", self.db.desc or ""]
        exits = _list_exit_names(self)
        if exits:
            lines.append(f"|g出口|n: {' / '.join(exits)}")
        sections = _build_room_sections(self, looker=looker)
        if sections:
            lines.extend(sections)
        return "\n".join(line for line in lines if line)


def _build_room_sections(room, looker=None):
    npcs = []
    enemies = []
    players = []
    for obj in _get_room_contents(room):
        if obj is looker:
            continue
        if getattr(obj, "destination", None):
            continue
        if is_npc(obj):
            npcs.append(obj)
        elif is_enemy(obj):
            enemies.append(obj)
        elif getattr(getattr(obj, "db", None), "character_profile", None) is not None:
            players.append(obj)

    lines = []
    if npcs:
        lines.append("|g在场人物|n:")
        lines.extend(_format_npc_line(npc) for npc in npcs)
    if players:
        lines.append("|g附近修士|n:")
        lines.extend(f"- {player.key}（可 信息）" for player in players)
    if enemies:
        lines.append("|r敌对目标|n:")
        lines.extend(f"- {enemy.key}（可 信息 / 攻击）" for enemy in enemies)
    return lines


def _format_npc_line(npc):
    actions = ["信息"]
    if getattr(npc.db, "talk_route", None) or getattr(npc.db, "npc_role", None):
        actions.append("交谈")
    if getattr(npc.db, "shop_id", None):
        actions.append("商店")
    actions.append("关系")
    return f"- {npc.key}（可 {' / '.join(actions)}）"


def _get_room_contents(room):
    contents_get = getattr(room, "contents_get", None)
    if callable(contents_get):
        return list(contents_get())
    return list(getattr(room, "contents", []) or [])


def _list_exit_names(room):
    exits = getattr(room, "exits", None)
    if hasattr(exits, "items"):
        return list(exits.keys())
    if exits:
        return [getattr(exit_obj, "key", None) for exit_obj in exits if getattr(exit_obj, "key", None)]
    return []
