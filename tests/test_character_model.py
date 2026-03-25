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
from systems.player_stats import add_currency, apply_exp, get_stats, spend_currency  # noqa: E402


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
        self.assertEqual(stats["root"], None)
        self.assertEqual(stats["primary_currency"], PRIMARY_CURRENCY_COPPER)
        self.assertEqual(stats["spirit_stone"], 0)
        self.assertEqual(stats["equipment"]["slots"], {"chest": None, "legs": None})

    def test_awaken_spiritual_root_switches_stage_and_primary_currency(self):
        caller = FakeCaller()

        awaken_spiritual_root(caller, ROOT_WATER)
        stats = get_stats(caller)

        self.assertEqual(caller.db.character_stage, CULTIVATOR_STAGE)
        self.assertEqual(stats["root"], ROOT_WATER)
        self.assertEqual(stats["realm"], AWAKENED_REALM)
        self.assertEqual(stats["primary_currency"], PRIMARY_CURRENCY_SPIRIT_STONE)
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
        self.assertEqual(caller.db.spirit_stone, 7)

        success, remaining = spend_currency(caller, 3)
        self.assertTrue(success)
        self.assertEqual(remaining, 4)
        self.assertEqual(caller.db.spirit_stone, 4)

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
        caller.db.realm = "炼气四层"

        old_realm, new_realm, exp = apply_exp(caller, 0)

        self.assertEqual(old_realm, "炼气三层")
        self.assertEqual(new_realm, "炼气三层")
        self.assertEqual(exp, 90)
        self.assertEqual(caller.db.realm, "炼气三层")

    def test_promote_awakened_realm_enters_default_realm_progression(self):
        caller = FakeCaller()

        awaken_spiritual_root(caller, ROOT_WATER)
        promote_awakened_realm(caller)
        old_realm, new_realm, exp = apply_exp(caller, 30)

        self.assertEqual(old_realm, "炼气一层")
        self.assertEqual(new_realm, "炼气二层")
        self.assertEqual(exp, 30)


if __name__ == "__main__":
    unittest.main()
