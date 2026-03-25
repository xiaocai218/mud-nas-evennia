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
from unittest.mock import patch

django.setup()

from systems.character_model import ROOT_WATER, awaken_spiritual_root  # noqa: E402
from systems.npc_routes import run_npc_route  # noqa: E402
from systems.quests import QI_GUIDANCE_READY  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.key = "测试者"
        self.messages = []
        self.db = SimpleNamespace(
            guide_quest=QI_GUIDANCE_READY,
            guide_quest_root_awakened=True,
            guide_quest_qi_guided=False,
            character_profile="starter",
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

    def msg(self, text):
        self.messages.append(text)


class SpiritGuideRouteTests(unittest.TestCase):
    def test_spirit_guide_promotes_awakened_character_to_qi_one(self):
        caller = FakeCaller()
        awaken_spiritual_root(caller, ROOT_WATER)

        with patch("systems.npc_routes.notify_player"):
            result = run_npc_route(caller, "spirit_guide")

        self.assertTrue(result)
        self.assertEqual(caller.db.realm, "炼气一层")
        self.assertEqual(caller.db.guide_quest, "completed")
        self.assertTrue(caller.db.guide_quest_qi_guided)
        self.assertTrue(any("引气入体" in msg or "炼气一层" in msg for msg in caller.messages))


if __name__ == "__main__":
    unittest.main()
