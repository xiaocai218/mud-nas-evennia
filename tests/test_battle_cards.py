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

from systems.battle_cards import build_card_payload, get_card_display_name, resolve_card_alias  # noqa: E402


class BattleCardTests(unittest.TestCase):
    def test_build_card_payload_reads_config_definition(self):
        card = build_card_payload("water_barrier")

        self.assertEqual(card["name"], "水幕诀")
        self.assertEqual(card["card_type"], "skill_card")
        self.assertEqual(card["costs"]["mp"], 5)
        self.assertEqual(card["effect_params"]["base_shield"], 12)

    def test_resolve_card_alias_maps_display_name_to_card_id(self):
        self.assertEqual(resolve_card_alias("防御"), "guard")
        self.assertEqual(resolve_card_alias("水幕诀"), "water_barrier")
        self.assertEqual(resolve_card_alias("basic_attack"), "basic_attack")

    def test_get_card_display_name_prefers_card_definition(self):
        self.assertEqual(get_card_display_name(card_id="recover_instinct"), "兽性回生")
        self.assertEqual(get_card_display_name(entry_type="basic_attack"), "普通攻击")


if __name__ == "__main__":
    unittest.main()
