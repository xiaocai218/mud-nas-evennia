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

from systems.npc_model import ensure_npc_model, get_npc_definition, get_npc_sheet  # noqa: E402
from systems.npc_relationships import (  # noqa: E402
    adjust_npc_relationship_metric,
    clear_npc_relationship,
    get_npc_relationship,
    set_npc_relationship,
)


class FakeNpc:
    def __init__(self, key="守渡老人"):
        self.key = key
        self.db = SimpleNamespace(
            desc="desc",
            content_id=None,
            template_id=None,
            npc_id=None,
            npc_role=None,
            talk_route=None,
            shop_id=None,
            gender=None,
            realm=None,
            hp=None,
            max_hp=None,
        )


class FakeCaller:
    def __init__(self):
        self.db = SimpleNamespace(npc_relationships=None)


class NpcModelTests(unittest.TestCase):
    def test_legacy_npc_definition_is_normalized(self):
        target = FakeNpc("守渡老人")
        target.db.content_id = "npc_old_ferryman"
        target.db.template_id = "npc_old_ferryman"
        target.db.npc_role = "guide"
        target.db.talk_route = "guide_main"

        sheet = ensure_npc_model(target)

        self.assertEqual(sheet["identity"]["kind"], "npc")
        self.assertEqual(sheet["identity"]["npc_role"], "guide")
        self.assertEqual(sheet["identity"]["gender"], "unknown")
        self.assertEqual(sheet["npc_meta"]["combat_profile"]["attackable"], False)
        self.assertEqual(target.db.talk_route, "guide_main")
        self.assertGreater(sheet["combat_stats"]["max_hp"], 0)

    def test_structured_npc_definition_is_normalized(self):
        with patch("systems.npc_model.NPC_DEFINITIONS", [
            {
                "id": "npc_structured_tester",
                "room_id": "qingyundu",
                "identity": {
                    "kind": "npc",
                    "name": "结构化执事",
                    "gender": "female",
                    "npc_role": "steward",
                },
                "progression": {
                    "stage": "cultivator",
                    "realm": "炼气2阶",
                },
                "primary_stats": {
                    "physique": 5,
                    "aether": 7,
                    "spirit": 6,
                    "agility": 4,
                    "bone": 5,
                },
                "combat_stats": {
                    "hp": 120,
                    "max_hp": 120,
                    "mp": 30,
                    "max_mp": 30,
                    "stamina": 50,
                    "max_stamina": 50,
                    "attack_power": 12,
                    "spell_power": 16,
                    "defense": 9,
                    "speed": 10,
                    "crit_rate": 2,
                    "crit_damage": 160,
                    "healing_power": 8,
                    "shield_power": 4,
                    "control_power": 3,
                    "control_resist": 6,
                    "threat_modifier": 100,
                },
                "npc_meta": {
                    "talk_route": "guide_main",
                    "combat_profile": {"attackable": False},
                },
            }
        ]):
            definition = get_npc_definition("npc_structured_tester")

        self.assertEqual(definition["identity"]["gender"], "female")
        self.assertEqual(definition["progression"]["realm"], "炼气2阶")
        self.assertEqual(definition["npc_meta"]["combat_profile"]["attackable"], False)
        self.assertEqual(definition["primary_stats"]["aether"], 7)

    def test_npc_realm_falls_back_to_area_recommended_realm(self):
        with patch("systems.npc_model.NPC_DEFINITIONS", [
            {
                "id": "npc_realm_fallback",
                "room_id": "qingyundu",
                "key": "渡口客卿",
                "desc": "desc",
                "attrs": {"npc_role": "guest"},
            }
        ]):
            definition = get_npc_definition("npc_realm_fallback")

        self.assertEqual(definition["progression"]["realm"], "炼气2阶")

    def test_get_npc_sheet_returns_compatibility_runtime(self):
        target = FakeNpc("杂货摊掌柜")
        target.db.content_id = "npc_general_store_keeper"
        target.db.template_id = "npc_general_store_keeper"
        target.db.shop_id = "shop_ferry_general_store"
        target.db.npc_role = "shopkeeper"

        sheet = get_npc_sheet(target)

        self.assertEqual(sheet["identity"]["npc_role"], "shopkeeper")
        self.assertEqual(sheet["npc_meta"]["shop_id"], "shop_ferry_general_store")


class NpcRelationshipTests(unittest.TestCase):
    def test_relationship_defaults_can_be_initialized(self):
        caller = FakeCaller()

        record = get_npc_relationship(caller, "npc_old_ferryman")

        self.assertEqual(record["npc_id"], "npc_old_ferryman")
        self.assertEqual(record["affection"], 0)
        self.assertFalse(record["projection_state"]["active"])
        self.assertFalse(record["relocation_state"]["hidden"])

    def test_relationship_updates_merge_nested_state(self):
        caller = FakeCaller()

        set_npc_relationship(
            caller,
            "npc_old_ferryman",
            {
                "affection": 12,
                "quest_flags": ["guide_done"],
                "projection_state": {"active": True, "projection_mode": "companion"},
                "relocation_state": {"hidden": True, "room_id_override": "outer_court"},
            },
        )
        record = get_npc_relationship(caller, "npc_old_ferryman")

        self.assertEqual(record["affection"], 12)
        self.assertEqual(record["quest_flags"], ["guide_done"])
        self.assertTrue(record["projection_state"]["active"])
        self.assertEqual(record["projection_state"]["projection_mode"], "companion")
        self.assertTrue(record["relocation_state"]["hidden"])
        self.assertEqual(record["relocation_state"]["room_id_override"], "outer_court")

    def test_adjust_relationship_metric_updates_single_value(self):
        caller = FakeCaller()

        record = adjust_npc_relationship_metric(caller, "npc_old_ferryman", "affection", 7)

        self.assertEqual(record["affection"], 7)
        self.assertEqual(get_npc_relationship(caller, "npc_old_ferryman")["affection"], 7)

    def test_clear_relationship_restores_default_record(self):
        caller = FakeCaller()
        set_npc_relationship(caller, "npc_old_ferryman", {"affection": 9, "trust": 4})

        clear_npc_relationship(caller, "npc_old_ferryman")
        record = get_npc_relationship(caller, "npc_old_ferryman")

        self.assertEqual(record["affection"], 0)
        self.assertEqual(record["trust"], 0)


if __name__ == "__main__":
    unittest.main()
