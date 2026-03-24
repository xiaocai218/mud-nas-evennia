import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT.parent
sys.path.insert(0, str(PLAYGROUND / "evennia-local-env"))
sys.path.insert(0, str(ROOT / "game" / "mygame"))
os.chdir(ROOT / "game" / "mygame")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django  # noqa: E402

django.setup()

from systems import quests  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.db = SimpleNamespace(
            guide_quest="completed",
            guide_quest_dummy_kill=True,
            guide_quest_stone_kill=True,
            guide_quest_mist_kill=True,
            guide_quest_stage_two_rewarded=True,
            guide_quest_stage_three_rewarded=True,
            side_herb_quest="side_herb_completed",
            side_dewgrass_quest="side_dewgrass_started",
        )


class QuestResetTests(unittest.TestCase):
    def test_reset_all_quest_progress_returns_character_to_not_started(self):
        caller = FakeCaller()
        result = quests.reset_all_quest_progress(caller)

        self.assertEqual(result["main_state"], quests.NOT_STARTED)
        self.assertEqual(caller.db.guide_quest, quests.NOT_STARTED)
        self.assertFalse(caller.db.guide_quest_dummy_kill)
        self.assertFalse(caller.db.guide_quest_stone_kill)
        self.assertFalse(caller.db.guide_quest_mist_kill)
        self.assertFalse(caller.db.guide_quest_stage_two_rewarded)
        self.assertFalse(caller.db.guide_quest_stage_three_rewarded)
        self.assertEqual(caller.db.side_herb_quest, quests.NOT_STARTED)
        self.assertEqual(caller.db.side_dewgrass_quest, quests.NOT_STARTED)


if __name__ == "__main__":
    unittest.main()
