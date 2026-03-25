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

from systems import battle  # noqa: E402


class FakeCaller:
    def __init__(self, key="测试者"):
        self.key = key
        self.location = SimpleNamespace(db=SimpleNamespace(room_id="pine", area_id="starter"))
        self.db = SimpleNamespace(battle_id=None, hp=100, max_hp=100, mp=12, max_mp=12, stamina=50, max_stamina=50)
        self.messages = []

    def search(self, query, global_search=False, quiet=True, location=None):
        if query == "青云渡":
            return [SimpleNamespace(key="青云渡")]
        return None

    def move_to(self, destination, quiet=True):
        self.location = destination

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class FakeEnemy:
    def __init__(self, key="青木傀儡"):
        self.key = key
        self.location = SimpleNamespace(db=SimpleNamespace(room_id="pine", area_id="starter"))
        self.db = SimpleNamespace(
            battle_id=None,
            combat_target=True,
            enemy_id="qingmu_dummy",
            hp=30,
            max_hp=30,
            reward_exp=12,
            drop_item_id=None,
            drop_key=None,
            drop_desc=None,
            quest_flag="dummy_kill",
            combat_stats={},
        )


class BattleTests(unittest.TestCase):
    def setUp(self):
        battle.reset_battle_registry()

    def test_start_battle_creates_instance(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            result = battle.start_battle(caller, [enemy], team_mode=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "battle_started")
        self.assertEqual(result["battle"]["status"], "active")
        self.assertEqual(len(result["battle"]["participants"]), 2)

    def test_submit_action_basic_attack_updates_battle(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            battle.start_battle(caller, [enemy], team_mode=False)
            result = battle.submit_action(caller, "basic_attack")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["type"], "basic_attack")
        self.assertLess(result["battle"]["participants"][1]["hp"], 30)

    def test_enemy_ai_uses_configured_recovery_rule(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="雾行山魈")
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 4},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "雾行山魈"},
                "combat_stats": {"hp": 12, "max_hp": 36, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 20},
                "enemy_meta": {
                    "battle_ai_profile": {"mode": "basic"},
                    "battle_card_pool": ["basic_attack", "recover_instinct"],
                    "decision_rules": [{"when": {"self_hp_lte_pct": 50, "card_ready": "recover_instinct"}, "use_card": "recover_instinct"}],
                },
            }),
        ):
            result = battle.start_battle(caller, [enemy], team_mode=False)
        self.assertTrue(result["ok"])
        self.assertTrue(any(entry.get("card_id") == "recover_instinct" for entry in result["battle"]["log"]))

    def test_clear_battle_resets_ids_and_returns_cancelled_snapshot(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            started = battle.start_battle(caller, [enemy], team_mode=False)
            snapshot = battle.clear_battle(caller, reset_players=True, reset_enemies=True)
        self.assertEqual(started["battle"]["battle_id"], snapshot["battle_id"])
        self.assertEqual(snapshot["result"], "cancelled")
        self.assertEqual(caller.db.battle_id, None)
        self.assertEqual(enemy.db.battle_id, None)

    def test_get_battle_log_returns_latest_entries(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            battle.start_battle(caller, [enemy], team_mode=False)
            battle.submit_action(caller, "basic_attack")
            logs = battle.get_battle_log(caller, limit=5)
        self.assertTrue(logs)
        self.assertEqual(logs[-1]["type"], "basic_attack")


if __name__ == "__main__":
    unittest.main()
