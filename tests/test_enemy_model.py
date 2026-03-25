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

from systems.enemy_model import BEAST_ENEMY, MORTAL_ENEMY, ensure_enemy_model, get_enemy_definition, is_enemy, spawn_enemy_instance  # noqa: E402


class FakeTarget:
    def __init__(self, key="目标", **attrs):
        self.key = key
        self.db = SimpleNamespace(**attrs)


class EnemyModelTests(unittest.TestCase):
    def test_structured_enemy_definition_normalizes_mortal_enemy(self):
        enemy = get_enemy_definition("qingmu_dummy")

        self.assertEqual(enemy["identity"]["enemy_type"], MORTAL_ENEMY)
        self.assertEqual(enemy["identity"]["kind"], "enemy")
        self.assertEqual(enemy["progression"]["stage"], "mortal")
        self.assertEqual(enemy["enemy_meta"]["quest_hooks"]["quest_flag"], "dummy_kill")

    def test_beast_enemy_uses_element_and_core_type(self):
        target = FakeTarget(key="雾行山魈", enemy_id="mist_ape", combat_target=True)

        ensure_enemy_model(target)

        self.assertEqual(target.db.identity["enemy_type"], BEAST_ENEMY)
        self.assertEqual(target.db.affinities["element"], "wood")
        self.assertEqual(target.db.enemy_meta["core_type"], "wood_core")
        self.assertIn("recover_instinct", target.db.enemy_meta["battle_card_pool"])
        self.assertTrue(target.db.enemy_meta["decision_rules"])
        self.assertFalse(hasattr(target.db, "spiritual_root"))

    def test_boss_modifiers_apply_to_runtime_stats(self):
        target = FakeTarget(
            key="试炼首领",
            combat_target=True,
            enemy_id="trial_boss",
            content_id="enemy_trial_boss",
            hp=60,
            max_hp=60,
            reward_exp=36,
            damage_taken=15,
            counter_damage=10,
            quest_flag="boss_kill",
            identity={
                "kind": "enemy",
                "name": "试炼首领",
                "enemy_type": MORTAL_ENEMY,
                "faction": "trial",
                "is_boss": True,
                "content_id": "enemy_trial_boss",
                "template_id": "trial_boss",
                "tags": ["boss"],
            },
            progression={"stage": "mortal", "realm": "凡人", "rank_tier": "boss", "spawn_profile": {"room_id": "pine"}},
            primary_stats={"physique": 6, "aether": 4, "spirit": 4, "agility": 4, "bone": 6},
            combat_stats={
                "hp": 60,
                "max_hp": 60,
                "mp": 0,
                "max_mp": 0,
                "stamina": 60,
                "max_stamina": 60,
                "attack_power": 14,
                "spell_power": 0,
                "defense": 8,
                "speed": 9,
                "crit_rate": 0,
                "crit_damage": 150,
                "healing_power": 0,
                "shield_power": 0,
                "control_power": 0,
                "control_resist": 5,
                "threat_modifier": 120,
            },
            affinities={"element": "earth", "damage_tags": [], "resist_tags": [], "drop_theme": []},
            reserves={"resources": {}},
            enemy_meta={
                "boss_modifiers": {
                    "damage_reduction_pct": 10,
                    "penetration_pct": 5,
                    "bonus_max_hp_pct": 50,
                    "bonus_defense_pct": 25,
                    "control_resist_bonus": 12,
                    "phase_shield": 0,
                    "pressure_tags": ["suppression"],
                },
                "quest_hooks": {"quest_flag": "boss_kill"},
                "reward_exp": 36,
                "damage_taken": 15,
                "counter_damage": 10,
                "stamina_cost": 8,
                "drop_item_id": None,
                "drop_key": None,
                "drop_desc": None,
            },
        )

        ensure_enemy_model(target)

        self.assertTrue(target.db.is_boss)
        self.assertEqual(target.db.max_hp, 90)
        self.assertEqual(target.db.hp, 60)
        self.assertEqual(target.db.combat_stats["defense"], 10)
        self.assertEqual(target.db.combat_stats["control_resist"], 17)

    def test_is_enemy_accepts_template_backed_target(self):
        target = FakeTarget(key="青木傀儡", enemy_id="qingmu_dummy")
        self.assertTrue(is_enemy(target))

    def test_spawn_enemy_instance_creates_runtime_content_id(self):
        created = FakeTarget(key="占位对象")
        location = SimpleNamespace(key="试战木场")

        with patch("evennia.utils.create.create_object", return_value=created):
            enemy = spawn_enemy_instance("mist_ape", location)

        self.assertIs(enemy, created)
        self.assertEqual(enemy.key, "雾行山魈")
        self.assertEqual(enemy.db.enemy_id, "mist_ape")
        self.assertTrue(enemy.db.content_id.startswith("enemy_mist_ape__spawn_"))


if __name__ == "__main__":
    unittest.main()
