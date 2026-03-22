"""
Room

Rooms are simple containers that has no location of their own.
"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Basic project room typeclass.
    """

    def at_object_creation(self):
        super().at_object_creation()
        if not self.db.desc:
            self.db.desc = "这里暂时还很空旷，但已经能感觉到一丝灵气流转。"
