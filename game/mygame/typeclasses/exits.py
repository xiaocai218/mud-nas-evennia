from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Project exit typeclass using the local object parent mixin.
    """

    pass
