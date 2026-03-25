"""
Characters

Localized character defaults for the prototype world.
"""

from evennia.objects.objects import DefaultCharacter

from systems.character_model import ensure_character_model
from systems.character_profiles import get_default_profile_key

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """
    Project default character typeclass.
    """

    cmdset_character = "commands.default_cmdsets.CharacterCmdSet"

    def at_object_creation(self):
        super().at_object_creation()
        self.db.character_profile = self.db.character_profile or get_default_profile_key()
        ensure_character_model(self)
