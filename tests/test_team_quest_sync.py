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

from systems import quests  # noqa: E402


class FakeCharacter:
    def __init__(self, key, area_id="qingyundu_village", guide_quest="stage_one_started"):
        self.key = key
        self.id = hash(key) & 0xFFFF
        self.pk = self.id
        self.location = SimpleNamespace(db=SimpleNamespace(area_id=area_id))
        self.db = SimpleNamespace(guide_quest=guide_quest, guide_quest_dummy_kill=False)


class FakeTarget:
    def __init__(self, key="青木傀儡", quest_flag="dummy_kill"):
        self.key = key
        self.db = SimpleNamespace(quest_flag=quest_flag)


class TeamQuestSyncTests(unittest.TestCase):
    def test_mark_combat_kill_syncs_same_area_teammate(self):
        caller = FakeCharacter("甲")
        teammate = FakeCharacter("乙")
        target = FakeTarget()
        with (
            patch("systems.quests.get_same_area_team_members", return_value=[teammate]),
            patch("systems.quests.send_system_message") as send_mock,
        ):
            result = quests.mark_combat_kill(caller, target)
        self.assertTrue(caller.db.guide_quest_dummy_kill)
        self.assertTrue(teammate.db.guide_quest_dummy_kill)
        self.assertEqual([member.key for member in result["shared"]], ["乙"])
        send_mock.assert_called_once()
        self.assertIn("队伍协同推进任务", send_mock.call_args.args[0])

    def test_mark_combat_kill_only_updates_matching_teammates(self):
        caller = FakeCharacter("甲")
        teammate = FakeCharacter("乙", guide_quest="stage_two_started")
        target = FakeTarget()
        with (
            patch("systems.quests.get_same_area_team_members", return_value=[teammate]),
            patch("systems.quests.send_system_message") as send_mock,
        ):
            result = quests.mark_combat_kill(caller, target)
        self.assertTrue(caller.db.guide_quest_dummy_kill)
        self.assertFalse(teammate.db.guide_quest_dummy_kill)
        self.assertEqual(result["shared"], [])
        send_mock.assert_called_once()
        self.assertIn("任务进度已更新", send_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
