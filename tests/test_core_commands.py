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

from commands.core import CmdStatus  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.key = "测试者"
        self.location = SimpleNamespace(key="青云渡")
        self.messages = []

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class CoreCommandTests(unittest.TestCase):
    def test_status_command_renders_combat_rows_in_sectioned_layout(self):
        caller = FakeCaller()
        command = CmdStatus()
        command.caller = caller
        command.args = ""

        with (
            patch(
                "commands.core.get_stats",
                return_value={
                    "stage": "mortal",
                    "root": None,
                    "realm": "凡人",
                    "realm_display": "凡人",
                    "realm_info": {"realm_key": "mortal", "minor_stage": None, "stage_bucket": None},
                    "hp": 100,
                    "max_hp": 100,
                    "mp": 0,
                    "max_mp": 0,
                    "stamina": 50,
                    "max_stamina": 50,
                    "exp": 0,
                    "copper": 80,
                    "spirit_stone": 0,
                    "primary_currency": "copper",
                    "combat_stats": {"attack_power": 18, "defense": 11, "speed": 16},
                },
            ),
            patch("commands.core.get_area_for_room", return_value={"key": "渡口区域"}),
            patch("commands.core.get_inventory_items", return_value=[]),
            patch("commands.core.get_active_effect_text", return_value="无"),
            patch("commands.core.get_root_label", return_value="未觉醒"),
        ):
            command.func()

        output = "\n".join(caller.messages)
        self.assertIn("角色状态总览", output)
        self.assertIn("战斗属性", output)
        self.assertIn("攻击力", output)
        self.assertIn("18", output)
        self.assertIn("防御力", output)
        self.assertIn("11", output)
        self.assertIn("身法/速度", output)
        self.assertIn("16", output)


if __name__ == "__main__":
    unittest.main()
