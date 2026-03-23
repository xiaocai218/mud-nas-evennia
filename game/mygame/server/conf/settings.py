r"""
Evennia settings file.
"""

from evennia.settings_default import *
from pathlib import Path

SERVERNAME = "九州群修"

# Keep the login chain on official cmdsets; only the in-game character cmdset is project-defined.
CMDSET_CHARACTER = "commands.default_cmdsets.CharacterCmdSet"
CMDSET_ACCOUNT = "evennia.commands.default.cmdset_account.AccountCmdSet"
CMDSET_UNLOGGEDIN = "evennia.commands.default.cmdset_unloggedin.UnloggedinCmdSet"
CMDSET_SESSION = "evennia.commands.default.cmdset_session.SessionCmdSet"

BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
BASE_ROOM_TYPECLASS = "typeclasses.rooms.Room"

FILE_HELP_ENTRY_MODULES = ["world.help_entries"]

GAME_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = GAME_DIR / "web"

TEMPLATES[0]["DIRS"] = [str(WEB_DIR / "templates"), *TEMPLATES[0]["DIRS"]]
STATICFILES_DIRS = [str(WEB_DIR / "static"), *STATICFILES_DIRS]

try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
