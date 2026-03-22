"""
Object
"""

from evennia.objects.objects import DefaultObject


class ObjectParent:
    """
    Shared mixin for all in-game entities.
    """


class Object(ObjectParent, DefaultObject):
    """
    Root object typeclass for project items and world objects.
    """

    pass
