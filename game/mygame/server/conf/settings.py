r"""
Evennia settings file.
"""

from evennia.settings_default import *

SERVERNAME = "九州群修"

# Explicitly pin project paths so future maintenance is easier.
CMDSET_CHARACTER = "commands.default_cmdsets.CharacterCmdSet"
CMDSET_ACCOUNT = "commands.default_cmdsets.AccountCmdSet"
CMDSET_UNLOGGEDIN = "commands.default_cmdsets.UnloggedinCmdSet"
CMDSET_SESSION = "commands.default_cmdsets.SessionCmdSet"

BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
BASE_ROOM_TYPECLASS = "typeclasses.rooms.Room"

FILE_HELP_ENTRY_MODULES = ["world.help_entries"]

try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
