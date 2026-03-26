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

from typeclasses.rooms import _build_room_sections  # noqa: E402


class FakeObject:
    def __init__(self, key, *, db=None, destination=None):
        self.key = key
        self.db = db or SimpleNamespace()
        self.destination = destination


class FakeRoom:
    def __init__(self, contents=None):
        self.contents = contents or []


class RoomPresentationTests(unittest.TestCase):
    def test_build_room_sections_lists_action_hints(self):
        npc = FakeObject(
            "守渡老人",
            db=SimpleNamespace(
                identity={"kind": "npc"},
                npc_role="guide",
                talk_route="ferryman_intro",
                shop_id=None,
                character_profile=None,
            ),
        )
        player = FakeObject(
            "云游客",
            db=SimpleNamespace(
                identity={},
                character_profile="default",
            ),
        )
        enemy = FakeObject(
            "青木傀儡",
            db=SimpleNamespace(
                identity={"kind": "enemy"},
                character_profile=None,
            ),
        )
        room = FakeRoom(contents=[npc, player, enemy])

        with (
            patch("typeclasses.rooms.is_npc", side_effect=lambda obj: obj is npc),
            patch("typeclasses.rooms.is_enemy", side_effect=lambda obj: obj is enemy),
        ):
            lines = _build_room_sections(room)

        output = "\n".join(lines)
        self.assertIn("在场人物", output)
        self.assertIn("守渡老人（可 信息 / 交谈 / 关系）", output)
        self.assertIn("附近修士", output)
        self.assertIn("云游客（可 信息）", output)
        self.assertIn("敌对目标", output)
        self.assertIn("青木傀儡（可 信息 / 攻击）", output)


if __name__ == "__main__":
    unittest.main()
