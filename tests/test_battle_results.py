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

from systems.battle_results import build_basic_attack_result, build_guard_result, build_round_report, build_shield_result, snapshot_battle_state  # noqa: E402


class BattleResultTests(unittest.TestCase):
    def test_build_basic_attack_result_keeps_damage_modifiers(self):
        actor = {"combatant_id": "player_1", "name": "测试者", "side": "player", "entity_type": "player"}
        target = {"combatant_id": "enemy_1", "name": "试战恶徒", "side": "enemy", "hp": 26}
        applied = {"damage": 4, "shield_absorbed": 0, "guard_reduced": 6, "guard_blocked": False}

        result = build_basic_attack_result(actor, target, 10, applied)

        self.assertEqual(result["log"]["value"], 4)
        self.assertEqual(result["log"]["raw_value"], 10)
        self.assertEqual(result["log"]["guard_reduced"], 6)
        self.assertFalse(result["log"]["guard_blocked"])
        self.assertEqual(result["action_result"]["result"]["damage"], 4)
        self.assertEqual(result["action_result"]["modifiers"]["raw_damage"], 10)
        self.assertEqual(result["action_result"]["resource_delta"]["source_stamina"], -3)
        self.assertEqual(result["log"]["action_result"]["result"]["damage"], 4)

    def test_snapshot_battle_state_groups_players_and_enemies(self):
        battle = {
            "participants": [
                {"combatant_id": "player_1", "name": "测试者", "side": "player", "alive": True, "hp": 90, "max_hp": 100, "mp": 10, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 0, "effects": []},
                {"combatant_id": "enemy_1", "name": "试战恶徒", "side": "enemy", "alive": True, "hp": 30, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 9, "effects": [{"type": "guard"}]},
            ]
        }

        snapshot = snapshot_battle_state(battle)

        self.assertEqual(snapshot["player"][0]["name"], "测试者")
        self.assertEqual(snapshot["enemy"][0]["name"], "试战恶徒")
        self.assertEqual(snapshot["enemy"][0]["shield"], 9)
        self.assertEqual(snapshot["enemy"][0]["resources"]["shield"], 9)
        self.assertEqual(snapshot["meta"]["alive_player_count"], 1)
        self.assertEqual(snapshot["meta"]["alive_enemy_count"], 1)

    def test_build_round_report_keeps_before_after_snapshots(self):
        battle = {"turn_state": {"turn_count": 4}}
        actor = {"name": "测试者", "side": "player"}
        entry = {"type": "guard", "card_id": "guard", "action_result": {"action_type": "guard", "card_id": "guard"}}
        before = {"player": [{"name": "测试者"}], "enemy": [{"name": "试战恶徒"}], "meta": {"alive_player_count": 1, "alive_enemy_count": 1}}
        after = {"player": [{"name": "测试者", "effects": [{"type": "guard"}]}], "enemy": [{"name": "试战恶徒"}], "meta": {"alive_player_count": 1, "alive_enemy_count": 1}}

        report = build_round_report(battle, actor, entry, before, after, auto=False)

        self.assertEqual(report["turn_count"], 4)
        self.assertEqual(report["actor_name"], "测试者")
        self.assertEqual(report["card_id"], "guard")
        self.assertEqual(report["before"], before)
        self.assertEqual(report["after"], after)
        self.assertEqual(report["action_result"]["action_type"], "guard")

    def test_guard_and_shield_results_include_action_result(self):
        actor = {"combatant_id": "player_1", "name": "测试者", "side": "player", "hp": 90}

        guard = build_guard_result(actor, "guard", 60, 5, source_mp=0)
        shield = build_shield_result(actor, "water_barrier", 16, source_mp=-5)

        self.assertEqual(guard["action_result"]["action_type"], "guard")
        self.assertEqual(guard["log"]["action_result"]["state_delta"]["source_effects_added"], ["guard"])
        self.assertEqual(shield["action_result"]["result"]["shield_gain"], 16)
        self.assertEqual(shield["log"]["action_result"]["resource_delta"]["source_mp"], -5)


if __name__ == "__main__":
    unittest.main()
