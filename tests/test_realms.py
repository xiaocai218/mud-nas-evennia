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

from systems.realms import (
    build_entity_realm_payload,
    build_mortal_progression,
    evaluate_breakthrough_requirements,
    format_breakthrough_requirements,
    get_cultivation_progress_messages,
    get_breakthrough_requirements,
    get_progression_hint,
    get_progression_status_rows,
    get_stage_bucket_display,
    is_formal_realm_without_minor_stage,
    resolve_realm_progression,
)  # noqa: E402


class RealmHelperTests(unittest.TestCase):
    def test_mortal_progression_has_no_minor_stage(self):
        progression = build_mortal_progression(0)
        self.assertEqual(progression["display_name"], "凡人")
        self.assertIsNone(progression["minor_stage"])
        self.assertFalse(progression["can_breakthrough"])

    def test_qi_refining_stage_buckets_are_mapped(self):
        self.assertEqual(resolve_realm_progression(0, realm_key="qi_refining")["stage_bucket"], "初阶")
        self.assertEqual(resolve_realm_progression(180, realm_key="qi_refining")["stage_bucket"], "中阶")
        self.assertEqual(resolve_realm_progression(330, realm_key="qi_refining")["stage_bucket"], "高阶")
        self.assertEqual(resolve_realm_progression(630, realm_key="qi_refining")["stage_bucket"], "巅峰")

    def test_peak_stage_does_not_auto_advance_realm(self):
        progression = resolve_realm_progression(700, realm_key="qi_refining")
        self.assertEqual(progression["display_name"], "炼气10阶")
        self.assertEqual(progression["next_realm_key"], "foundation_establishment")
        self.assertFalse(progression["can_breakthrough"])

    def test_formal_realm_without_minor_stages_keeps_realm_name(self):
        progression = resolve_realm_progression(750, realm_key="foundation_establishment")
        self.assertEqual(progression["display_name"], "筑基")
        self.assertEqual(progression["realm"], "筑基")
        self.assertEqual(progression["realm_key"], "foundation_establishment")
        self.assertIsNone(progression["minor_stage"])
        self.assertEqual(progression["breakthrough_state"], "unavailable")

    def test_formal_realm_without_minor_stages_has_placeholder_hint(self):
        progression = resolve_realm_progression(750, realm_key="foundation_establishment")
        self.assertEqual(get_progression_hint(progression), "筑基 已达成，后续小阶内容暂未开放")

    def test_stage_bucket_display_uses_placeholder_for_formal_realm_without_minor_stage(self):
        progression = resolve_realm_progression(750, realm_key="foundation_establishment")
        self.assertTrue(is_formal_realm_without_minor_stage(progression))
        self.assertEqual(get_stage_bucket_display(progression), "小阶待开放")

    def test_stage_bucket_display_keeps_mortal_as_none_display(self):
        progression = build_mortal_progression(0)
        self.assertFalse(is_formal_realm_without_minor_stage(progression))
        self.assertEqual(get_stage_bucket_display(progression), "无")

    def test_progression_status_rows_for_minor_stage_include_exp_breakthrough_and_hint(self):
        progression = resolve_realm_progression(271, realm_key="qi_refining")
        self.assertEqual(
            get_progression_status_rows(progression),
            [("当前阶修为", "21/80"), ("突破状态", "未满足"), ("下一步", "距离 炼气6阶 下一阶还差 59 修为")],
        )

    def test_cultivation_progress_messages_for_formal_realm_without_minor_stage_use_placeholder_copy(self):
        progression = resolve_realm_progression(750, realm_key="foundation_establishment")
        self.assertEqual(
            get_cultivation_progress_messages(progression),
            ["|g当前境界|n: 筑基（小阶暂未开放）", "|g下一步|n: 筑基 已达成，后续小阶内容暂未开放"],
        )

    def test_build_entity_realm_payload_formats_enemy_title_with_yaojie_display(self):
        payload = build_entity_realm_payload({"realm": "炼气3阶"}, entity_kind="enemy", enemy_type="beast", suffix="雾猿")
        self.assertEqual(payload["realm"], "炼气3阶")
        self.assertEqual(payload["realm_display"], "炼气妖阶3阶")
        self.assertEqual(payload["realm_title"], "炼气妖阶3阶·雾猿")

    def test_breakthrough_requirements_default_to_empty_and_pass(self):
        requirements = get_breakthrough_requirements("foundation_establishment")
        result = evaluate_breakthrough_requirements(None, "foundation_establishment")
        self.assertEqual(requirements, [])
        self.assertTrue(result["can_breakthrough"])
        self.assertEqual(result["missing_requirements"], [])

    def test_format_breakthrough_requirements_outputs_readable_lines(self):
        lines = format_breakthrough_requirements(
            [
                {"type": "quest", "label": "宗门任务", "description": "完成引气入体", "status": "missing"},
                {"type": "pill", "description": "准备筑基丹", "status": "missing", "optional": True},
            ]
        )
        self.assertEqual(lines, ["需要宗门任务：完成引气入体", "可选丹药：准备筑基丹"])


if __name__ == "__main__":
    unittest.main()
