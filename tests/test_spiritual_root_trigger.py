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

from commands.core import parse_trigger_input  # noqa: E402
from systems import world_objects  # noqa: E402


class FakeCaller:
    def __init__(self, guide_quest="root_choice_ready"):
        self.key = "测试者"
        self.db = SimpleNamespace(
            guide_quest=guide_quest,
            guide_quest_root_awakened=False,
            character_profile="starter",
            character_stage="mortal",
            spiritual_root=None,
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

    def move_to(self, destination, quiet=True):
        return None


class FakeTarget:
    def __init__(self, content_id="obj_spirit_stone_01"):
        self.key = "测灵石"
        self.db = SimpleNamespace(
            content_id=content_id,
            trigger_requirements={
                "main_state_in": ["root_choice_ready", "qi_guidance_ready", "completed"],
                "fail_text": "还不到时候。",
            },
            trigger_effect={
                "type": "spiritual_root",
                "text": "请选择灵根",
                "confirm_text": "已定下 {root_label}",
                "already_awakened_text": "已经定过灵根。",
            },
        )


class SpiritualRootTriggerTests(unittest.TestCase):
    def test_parse_trigger_input_extracts_root_choice(self):
        target, option = parse_trigger_input("测灵石 水")
        self.assertEqual(target, "测灵石")
        self.assertEqual(option, "水")

    def test_trigger_spirit_stone_shows_choices_without_selection(self):
        caller = FakeCaller()
        target = FakeTarget()

        result = world_objects.trigger_object(caller, target)

        self.assertTrue(result["ok"])
        self.assertTrue(result["awaiting_choice"])
        self.assertIn("water", result["choices"])

    def test_trigger_spirit_stone_rejects_before_quest_stage(self):
        caller = FakeCaller(guide_quest="stage_three_started")
        target = FakeTarget()

        result = world_objects.trigger_object(caller, target)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "locked")

    def test_gate_access_uses_intro_progress_helper(self):
        caller = FakeCaller(guide_quest="stage_three_started")
        gate = SimpleNamespace(
            key="青云山门",
            db=SimpleNamespace(
                content_id="obj_qingyun_gate_01",
                trigger_effect={"type": "teleport", "room_id": "room_shengxian_platform", "text": "前往升仙台"},
                trigger_requirements={"main_state_in": ["root_choice_ready", "completed"]},
            ),
        )

        result = world_objects.trigger_object(caller, gate)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "locked")

    def test_trigger_spirit_stone_confirms_root_and_completes_quest(self):
        caller = FakeCaller()
        target = FakeTarget()

        result = world_objects.trigger_object(caller, target, option="水")

        self.assertTrue(result["ok"])
        self.assertEqual(caller.db.character_stage, "cultivator")
        self.assertEqual(caller.db.spiritual_root, "water")
        self.assertEqual(caller.db.realm, "启灵")
        self.assertEqual(caller.db.primary_currency, "spirit_stone")
        self.assertEqual(caller.db.guide_quest, "qi_guidance_ready")
        self.assertTrue(caller.db.guide_quest_root_awakened)
        self.assertIn("水灵根", result["text"])

    def test_trigger_spirit_stone_after_completion_returns_already_awakened_text(self):
        caller = FakeCaller(guide_quest="qi_guidance_ready")
        caller.db.guide_quest_stage_two_rewarded = True
        caller.db.guide_quest_stage_three_rewarded = True
        caller.db.guide_quest_root_awakened = True
        caller.db.character_stage = "cultivator"
        caller.db.spiritual_root = "water"
        target = FakeTarget()

        result = world_objects.trigger_object(caller, target)

        self.assertTrue(result["ok"])
        self.assertTrue(result["already_awakened"])

    def test_unknown_trigger_type_returns_unsupported_trigger(self):
        caller = FakeCaller()
        target = SimpleNamespace(
            key="未知石柱",
            db=SimpleNamespace(
                trigger_effect={"type": "mystery"},
                trigger_requirements={},
            ),
        )

        result = world_objects.trigger_object(caller, target)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "unsupported_trigger")


if __name__ == "__main__":
    unittest.main()
