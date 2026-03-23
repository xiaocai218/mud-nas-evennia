"""
Characters

Localized character defaults for the prototype world.
"""

from evennia.objects.objects import DefaultCharacter

from systems.character_profiles import get_character_profile, get_default_profile_key
from systems.realms import get_default_realm

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """
    Project default character typeclass.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.character_profile = self.db.character_profile or get_default_profile_key()
        profile = get_character_profile(self.db.character_profile)
        self.db.realm = self.db.realm or profile["realm"] or get_default_realm()
        self.db.hp = profile["hp"] if self.db.hp is None else self.db.hp
        self.db.max_hp = profile["max_hp"] if self.db.max_hp is None else self.db.max_hp
        self.db.stamina = profile["stamina"] if self.db.stamina is None else self.db.stamina
        self.db.max_stamina = profile["max_stamina"] if self.db.max_stamina is None else self.db.max_stamina
        self.db.exp = profile["exp"] if self.db.exp is None else self.db.exp
