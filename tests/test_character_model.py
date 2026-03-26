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

from systems.character_model import (  # noqa: E402
    AWAKENED_REALM,
    CULTIVATOR_STAGE,
    MORTAL_REALM,
    MORTAL_STAGE,
    PRIMARY_CURRENCY_COPPER,
    PRIMARY_CURRENCY_SPIRIT_STONE,
    ROOT_WATER,
    awaken_spiritual_root,
    ensure_character_model,
    get_root_definition,
    promote_awakened_realm,
    resolve_character_realm,
)
from systems.realms import resolve_realm_progression  # noqa: E402
from systems.player_stats import add_currency, apply_exp, get_stats, spend_currency, try_breakthrough  # noqa: E402
from systems.player_stats import set_total_cultivation_exp, sync_cultivation_progression  # noqa: E402
from unittest.mock import patch  # noqa: E402


class FakeCaller:
    def __init__(self, key="tester"):
        self.key = key
        self.db = SimpleNamespace(
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


class CharacterModelTests(unittest.TestCase):
    def test_new_character_defaults_to_mortal_model(self):
        caller = FakeCaller()

        ensure_character_model(caller)
        stats = get_stats(caller)

        self.assertEqual(caller.db.character_stage, MORTAL_STAGE)
        self.assertEqual(stats["realm"], MORTAL_REALM)
        self.assertEqual(stats["realm_info"]["display_name"], MORTAL_REALM)
        self.assertEqual(stats["root"], None)
        self.assertEqual(stats["gender"], "unknown")
        self.assertEqual(stats["primary_currency"], PRIMARY_CURRENCY_COPPER)
        self.assertEqual(stats["spirit_stone"], 0)
        self.assertEqual(stats["equipment"]["slots"], {"chest": None, "legs": None})
        self.assertEqual(caller.db.npc_relationships, {})

    def test_awaken_spiritual_root_switches_stage_and_primary_currency(self):
        caller = FakeCaller()

        awaken_spiritual_root(caller, ROOT_WATER)
        stats = get_stats(caller)

        self.assertEqual(caller.db.character_stage, CULTIVATOR_STAGE)
        self.assertEqual(stats["root"], ROOT_WATER)
        self.assertEqual(stats["realm"], AWAKENED_REALM)
        self.assertEqual(stats["primary_currency"], PRIMARY_CURRENCY_COPPER)
        self.assertGreater(stats["max_mp"], 0)
        self.assertIn("liquid", stats["affinities"]["life"])

    def test_water_root_definition_includes_liquid_affinity(self):
        definition = get_root_definition(ROOT_WATER)
        self.assertIn("liquid", definition["life_affinity"])

    def test_cultivator_with_root_and_low_exp_uses_awakened_realm(self):
        self.assertEqual(resolve_character_realm(CULTIVATOR_STAGE, 0, current_realm=None, root=ROOT_WATER), AWAKENED_REALM)

    def test_primary_currency_helpers_switch_to_spirit_stone_after_awakening(self):
        caller = FakeCaller()

        add_currency(caller, 12)
        self.assertEqual(caller.db.copper, 92)

        awaken_spiritual_root(caller, ROOT_WATER)
        add_currency(caller, 7)
        self.assertEqual(caller.db.copper, 99)

        success, remaining = spend_currency(caller, 3)
        self.assertTrue(success)
        self.assertEqual(remaining, 96)
        self.assertEqual(caller.db.copper, 96)

    def test_apply_exp_does_not_downgrade_awakened_cultivator_to_mortal_realm(self):
        caller = FakeCaller()

        awaken_spiritual_root(caller, ROOT_WATER)
        old_realm, new_realm, exp = apply_exp(caller, 0)

        self.assertEqual(old_realm, AWAKENED_REALM)
        self.assertEqual(new_realm, AWAKENED_REALM)
        self.assertEqual(exp, 0)

    def test_apply_exp_zero_does_not_promote_stale_realm(self):
        caller = FakeCaller()
        caller.db.character_stage = CULTIVATOR_STAGE
        caller.db.spiritual_root = ROOT_WATER
        caller.db.exp = 90
        caller.db.realm = "炼气4阶"

        old_realm, new_realm, exp = apply_exp(caller, 0)

        self.assertEqual(old_realm, "炼气3阶")
        self.assertEqual(new_realm, "炼气3阶")
        self.assertEqual(exp, 90)
        self.assertEqual(caller.db.realm, "炼气3阶")

    def test_promote_awakened_realm_enters_default_realm_progression(self):
        caller = FakeCaller()

        awaken_spiritual_root(caller, ROOT_WATER)
        promote_awakened_realm(caller)
        old_realm, new_realm, exp = apply_exp(caller, 30)

        self.assertEqual(old_realm, "炼气1阶")
        self.assertEqual(new_realm, "炼气2阶")
        self.assertEqual(exp, 30)

    def test_realm_progression_exposes_stage_bucket_and_breakthrough_state(self):
        progression = resolve_realm_progression(750, realm_key="qi_refining")
        self.assertEqual(progression["display_name"], "炼气10阶")
        self.assertEqual(progression["stage_bucket"], "巅峰")
        self.assertTrue(progression["can_breakthrough"])

    def test_try_breakthrough_promotes_to_next_realm_key(self):
        caller = FakeCaller()
        awaken_spiritual_root(caller, ROOT_WATER)
        promote_awakened_realm(caller)
        caller.db.exp = 750
        ensure_character_model(caller)

        result = try_breakthrough(caller)

        self.assertTrue(result["ok"])
        self.assertEqual(caller.db.progression["realm_key"], "foundation_establishment")
        self.assertEqual(caller.db.primary_currency, PRIMARY_CURRENCY_SPIRIT_STONE)

    def test_set_total_cultivation_exp_preserves_awakened_transition_state(self):
        caller = FakeCaller()
        awaken_spiritual_root(caller, ROOT_WATER)

        result = set_total_cultivation_exp(caller, 750)

        self.assertEqual(result["realm"], AWAKENED_REALM)
        self.assertEqual(caller.db.realm, AWAKENED_REALM)
        self.assertEqual(caller.db.progression["cultivation_exp_total"], 750)

    def test_sync_cultivation_progression_can_switch_to_target_formal_realm_key(self):
        caller = FakeCaller()
        awaken_spiritual_root(caller, ROOT_WATER)
        promote_awakened_realm(caller)
        caller.db.exp = 750
        ensure_character_model(caller)

        progression = sync_cultivation_progression(caller, exp_total=750, realm_key="foundation_establishment")

        self.assertEqual(progression["display_name"], "筑基")
        self.assertEqual(caller.db.progression["realm_key"], "foundation_establishment")

    def test_try_breakthrough_returns_requirement_payload_when_conditions_are_missing(self):
        caller = FakeCaller()
        awaken_spiritual_root(caller, ROOT_WATER)
        promote_awakened_realm(caller)
        caller.db.exp = 750
        ensure_character_model(caller)

        with patch(
            "systems.player_stats.evaluate_breakthrough_requirements",
            return_value={
                "can_breakthrough": False,
                "requirements": [{"type": "quest", "label": "宗门任务", "description": "完成引气入体", "status": "missing"}],
                "missing_requirements": [{"type": "quest", "label": "宗门任务", "description": "完成引气入体", "status": "missing"}],
                "target_realm_key": "foundation_establishment",
            },
        ):
            result = try_breakthrough(caller)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "requirements_not_met")
        self.assertEqual(result["requirements"]["missing_requirements"][0]["label"], "宗门任务")


if __name__ == "__main__":
    unittest.main()
