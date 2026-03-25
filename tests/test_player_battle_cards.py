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

from systems.player_battle_cards import can_use_player_card, get_player_available_skill_cards, get_player_battle_card_pool  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.db = SimpleNamespace()


class PlayerBattleCardTests(unittest.TestCase):
    def test_mortal_player_uses_default_template_pool(self):
        caller = FakeCaller()
        with patch(
            "systems.player_battle_cards.get_stats",
            return_value={"stage": "mortal", "root": None, "realm": "凡人"},
        ):
            pool = get_player_battle_card_pool(caller)
        self.assertIn("basic_attack", pool)
        self.assertIn("guard", pool)
        self.assertIn("use_combat_item", pool)

    def test_cultivator_template_pool_exposes_placeholder_skill(self):
        caller = FakeCaller()
        with patch(
            "systems.player_battle_cards.get_stats",
            return_value={"stage": "cultivator", "root": None, "realm": "启灵"},
        ):
            cards = get_player_available_skill_cards(caller)
            pool = get_player_battle_card_pool(caller)
            can_use = can_use_player_card(caller, "spirit_blast")
        self.assertIn("spirit_blast", cards)
        self.assertIn("spirit_blast", pool)
        self.assertTrue(can_use)

    def test_water_root_gets_root_specific_skill_template(self):
        caller = FakeCaller()
        with patch(
            "systems.player_battle_cards.get_stats",
            return_value={"stage": "cultivator", "root": "water", "realm": "启灵"},
        ):
            cards = get_player_available_skill_cards(caller)
            pool = get_player_battle_card_pool(caller)
            can_use = can_use_player_card(caller, "water_barrier")
        self.assertIn("water_barrier", cards)
        self.assertIn("water_barrier", pool)
        self.assertNotIn("spirit_blast", cards)
        self.assertTrue(can_use)


if __name__ == "__main__":
    unittest.main()
