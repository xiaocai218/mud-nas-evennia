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

from systems.targeting import find_enemy_in_room, find_npc_in_room, find_target_in_room  # noqa: E402


class FakeCaller:
    def __init__(self, result=None):
        self.location = SimpleNamespace()
        self._result = result

    def search(self, query, location=None, quiet=False):
        if quiet:
            return [self._result] if self._result else []
        return self._result


class TargetingTests(unittest.TestCase):
    def test_find_target_in_room_returns_first_quiet_match(self):
        target = SimpleNamespace(key="守渡老人")
        caller = FakeCaller(result=target)

        found = find_target_in_room(caller, "守渡老人")

        self.assertEqual(found, target)

    def test_find_npc_in_room_filters_non_npc(self):
        target = SimpleNamespace(key="守渡老人")
        caller = FakeCaller(result=target)

        with patch("systems.targeting.is_npc", return_value=False):
            found = find_npc_in_room(caller, "守渡老人")

        self.assertIsNone(found)

    def test_find_enemy_in_room_filters_enemy(self):
        target = SimpleNamespace(key="青木傀儡")
        caller = FakeCaller(result=target)

        with patch("systems.targeting.is_enemy", return_value=True):
            found = find_enemy_in_room(caller, "青木傀儡")

        self.assertEqual(found, target)


if __name__ == "__main__":
    unittest.main()
