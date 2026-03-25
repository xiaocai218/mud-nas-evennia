import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT.parent
sys.path.insert(0, str(PLAYGROUND / "evennia-local-env"))
sys.path.insert(0, str(ROOT / "game" / "mygame"))
os.chdir(ROOT / "game" / "mygame")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django  # noqa: E402

django.setup()

from systems.battle_ai import choose_card, match_rule  # noqa: E402


class BattleAiTests(unittest.TestCase):
    def test_match_rule_supports_missing_effect_and_shield_lte(self):
        battle = {
            "participants": [
                {"combatant_id": "enemy_1", "side": "enemy", "hp": 20, "max_hp": 40, "alive": True, "shield": 0},
                {"combatant_id": "player_1", "side": "player", "hp": 60, "max_hp": 100, "alive": True, "shield": 0},
            ]
        }
        actor = {
            "combatant_id": "enemy_1",
            "side": "enemy",
            "hp": 20,
            "max_hp": 40,
            "shield": 0,
            "cooldowns": {},
            "effects": [],
        }
        rule = {"when": {"self_hp_lte_pct": 50, "missing_effect": "guard", "shield_lte": 0}, "use_card": "guard"}

        self.assertTrue(match_rule(battle, actor, rule))

    def test_match_rule_supports_target_hp_lte_pct(self):
        battle = {
            "participants": [
                {"combatant_id": "enemy_1", "side": "enemy", "hp": 30, "max_hp": 40, "alive": True, "shield": 0},
                {"combatant_id": "player_1", "side": "player", "hp": 18, "max_hp": 100, "alive": True, "shield": 0},
            ]
        }
        actor = {
            "combatant_id": "enemy_1",
            "side": "enemy",
            "hp": 30,
            "max_hp": 40,
            "shield": 0,
            "cooldowns": {},
            "effects": [],
        }
        rule = {"when": {"target_hp_lte_pct": 20}, "use_card": "fire_burst"}

        self.assertTrue(match_rule(battle, actor, rule))

    def test_choose_card_prefers_matching_rule(self):
        battle = {
            "participants": [
                {"combatant_id": "enemy_1", "side": "enemy", "hp": 12, "max_hp": 36, "alive": True, "shield": 0},
                {"combatant_id": "player_1", "side": "player", "hp": 80, "max_hp": 100, "alive": True, "shield": 0},
            ]
        }
        actor = {
            "combatant_id": "enemy_1",
            "side": "enemy",
            "hp": 12,
            "max_hp": 36,
            "shield": 0,
            "cooldowns": {},
            "effects": [],
            "available_cards": [
                {"card_id": "basic_attack", "card_type": "basic_attack", "target_rule": "enemy_single"},
                {"card_id": "recover_instinct", "card_type": "skill_card", "target_rule": "self"},
            ],
            "decision_rules": [{"when": {"self_hp_lte_pct": 50, "card_ready": "recover_instinct"}, "use_card": "recover_instinct"}],
        }

        selected = choose_card(battle, actor)

        self.assertEqual(selected["card_id"], "recover_instinct")
        self.assertEqual(selected["target_id"], "enemy_1")


if __name__ == "__main__":
    unittest.main()
