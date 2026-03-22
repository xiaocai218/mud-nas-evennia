"""
Item typeclasses for simple loot objects.
"""

from .objects import Object


class Item(Object):
    """
    Basic portable item.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_item = True
