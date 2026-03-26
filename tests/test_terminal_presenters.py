import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT.parent
sys.path.insert(0, str(PLAYGROUND / "evennia-local-env"))
sys.path.insert(0, str(ROOT / "game" / "mygame"))
os.chdir(ROOT / "game" / "mygame")

from systems.terminal_presenters import render_npc_relationship_detail, render_person_detail  # noqa: E402


class TerminalPresenterTests(unittest.TestCase):
    def test_render_person_detail_includes_relationship_summary(self):
        text = render_person_detail(
            {
                "key": "守渡老人",
                "tag": "NPC",
                "title": "guide",
                "gender_label": "未知",
                "realm": "炼气一层",
                "desc": "一位须发半白的老人。",
                "stats": [{"label": "气血", "value": "80/80"}],
                "actions": ["交谈", "关系"],
                "relationship": {
                    "stats": [
                        {"label": "好感", "value": "12"},
                        {"label": "声望", "value": "0"},
                        {"label": "信任", "value": "5"},
                    ]
                },
            }
        )
        self.assertIn("关系摘要:", text)
        self.assertIn("好感：12", text)

    def test_render_relationship_detail_lists_all_stats(self):
        text = render_npc_relationship_detail(
            {
                "target": "守渡老人",
                "stats": [
                    {"label": "好感", "value": "12"},
                    {"label": "声望", "value": "3"},
                    {"label": "信任", "value": "5"},
                ],
            }
        )
        self.assertIn("类型: NPC关系", text)
        self.assertIn("声望：3", text)


if __name__ == "__main__":
    unittest.main()
