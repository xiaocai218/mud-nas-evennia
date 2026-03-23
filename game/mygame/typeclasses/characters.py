"""
Characters

Localized character defaults for the prototype world.
"""

from evennia.objects.objects import DefaultCharacter

from systems.realms import get_default_realm

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """
    Project default character typeclass.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.realm = self.db.realm or get_default_realm()
        self.db.hp = 100 if self.db.hp is None else self.db.hp
        self.db.max_hp = 100 if self.db.max_hp is None else self.db.max_hp
        self.db.stamina = 50 if self.db.stamina is None else self.db.stamina
        self.db.max_stamina = 50 if self.db.max_stamina is None else self.db.max_stamina
        self.db.exp = 0 if self.db.exp is None else self.db.exp
