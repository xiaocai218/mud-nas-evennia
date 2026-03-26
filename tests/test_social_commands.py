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

from commands.social import CmdNpcRelationship, CmdPersonInfo  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.location = SimpleNamespace()
        self.messages = []
        self._search_map = {}

    def search(self, query, location=None, quiet=False):
        result = self._search_map.get(query)
        if quiet:
            return [result] if result else []
        return result

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class SocialCommandTests(unittest.TestCase):
    def test_person_info_command_renders_npc_detail(self):
        caller = FakeCaller()
        caller._search_map["守渡老人"] = SimpleNamespace(key="守渡老人")
        command = CmdPersonInfo()
        command.caller = caller
        command.args = "守渡老人"

        with patch(
            "commands.social.serialize_person_detail",
            return_value={
                "key": "守渡老人",
                "tag": "NPC",
                "title": "guide",
                "gender_label": "未知",
                "realm": "炼气一层",
                "desc": "一位须发半白的老人。",
                "stats": [{"label": "气血", "value": "80/80"}],
                "actions": ["交谈"],
            },
        ):
            command.func()

        output = "\n".join(caller.messages)
        self.assertIn("守渡老人", output)
        self.assertIn("类型: NPC", output)
        self.assertIn("境界: 炼气一层", output)
        self.assertIn("可交互: 交谈", output)

    def test_npc_relationship_command_renders_detail(self):
        caller = FakeCaller()
        caller._search_map["守渡老人"] = SimpleNamespace(key="守渡老人")
        command = CmdNpcRelationship()
        command.caller = caller
        command.args = "守渡老人"

        with patch(
            "commands.social.serialize_npc_relationship_detail",
            return_value={
                "target": "守渡老人",
                "stats": [
                    {"label": "好感", "value": "12"},
                    {"label": "声望", "value": "3"},
                    {"label": "信任", "value": "5"},
                ],
            },
        ):
            command.func()

        output = "\n".join(caller.messages)
        self.assertIn("类型: NPC关系", output)
        self.assertIn("好感：12", output)


if __name__ == "__main__":
    unittest.main()
