import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT.parent
sys.path.insert(0, str(PLAYGROUND / "evennia-local-env"))
sys.path.insert(0, str(ROOT / "game" / "mygame"))
os.chdir(ROOT / "game" / "mygame")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django  # noqa: E402

django.setup()

from commands.devtools import CmdTestChooseRoot, CmdTestResetRoot  # noqa: E402


class FakeCaller:
    def __init__(self, key="测试者"):
        self.key = key
        self.messages = []
        self.location = None
        self.db = SimpleNamespace(
            guide_quest=None,
            guide_quest_root_awakened=False,
            character_profile="starter",
            character_stage="mortal",
            spiritual_root=None,
            temp_effects={},
            hp=None,
            max_hp=None,
            mp=None,
            max_mp=None,
            stamina=None,
            max_stamina=None,
            exp=None,
            copper=None,
            spirit_stone=None,
            realm=None,
        )

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))

    def move_to(self, destination, quiet=True):
        self.location = destination


class DevtoolsCommandTests(unittest.TestCase):
    def test_test_choose_root_moves_to_spirit_stone_and_sets_root(self):
        caller = FakeCaller()
        command = CmdTestChooseRoot()
        command.caller = caller
        command.args = "水"
        room = SimpleNamespace(key="升仙台")
        spirit_stone = SimpleNamespace(key="测灵石")

        with (
            patch("commands.devtools._find_room_by_content_id", return_value=room),
            patch("commands.devtools._find_object_by_content_id", return_value=spirit_stone),
            patch("commands.devtools.reset_spiritual_root"),
            patch(
                "commands.devtools.trigger_object",
                return_value={"ok": True, "root": "water", "root_label": "水灵根"},
            ),
        ):
            command.func()

        self.assertEqual(caller.location, room)
        self.assertTrue(caller.db.guide_quest_stage_two_rewarded)
        self.assertTrue(caller.db.guide_quest_stage_three_rewarded)
        self.assertFalse(caller.db.guide_quest_root_awakened)
        self.assertFalse(caller.db.guide_quest_qi_guided)
        self.assertIn("水灵根", "".join(caller.messages))

    def test_test_reset_root_moves_to_platform_and_resets_state(self):
        caller = FakeCaller()
        caller.db.guide_quest = "completed"
        caller.db.guide_quest_root_awakened = True
        caller.db.character_stage = "cultivator"
        caller.db.spiritual_root = "water"
        command = CmdTestResetRoot()
        command.caller = caller
        command.args = ""
        room = SimpleNamespace(key="升仙台")

        with (
            patch("commands.devtools._find_room_by_content_id", return_value=room),
            patch("commands.devtools.reset_spiritual_root"),
        ):
            command.func()

        self.assertEqual(caller.location, room)
        self.assertTrue(caller.db.guide_quest_stage_two_rewarded)
        self.assertTrue(caller.db.guide_quest_stage_three_rewarded)
        self.assertFalse(caller.db.guide_quest_root_awakened)
        self.assertFalse(caller.db.guide_quest_qi_guided)
        self.assertIn("待选择状态", "".join(caller.messages))


if __name__ == "__main__":
    unittest.main()
