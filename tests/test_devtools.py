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

from commands.devtools import (  # noqa: E402
    CmdTestBattleRoom,
    CmdTestBattleLog,
    CmdTestChooseRoot,
    CmdTestClearBattle,
    CmdTestCultivationExp,
    CmdTestForceBattle,
    CmdTestAdjustNpcRelationship,
    CmdTestRealm,
    CmdTestRealmStatus,
    CmdTestSpawnBeast,
    CmdTestSpawnCultivatorEnemy,
    CmdTestRefreshEnemy,
    CmdTestResetBattle,
    CmdTestResetNpcRelationship,
    CmdTestResetRoot,
    CmdTestStamina,
)


class FakeCaller:
    def __init__(self, key="测试者"):
        self.key = key
        self.messages = []
        self.location = None
        self.db = SimpleNamespace(
            guide_quest=None,
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
            battle_id=None,
        )

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))

    def move_to(self, destination, quiet=True):
        self.location = destination

    def search(self, query, location=None):
        return None


class DevtoolsCommandTests(unittest.TestCase):
    def test_test_realm_sets_qi_refining_stage(self):
        caller = FakeCaller()
        command = CmdTestRealm()
        command.caller = caller
        command.args = "炼气6阶"

        def fake_sync(target, *, exp_total=None, current_realm=None, realm_key=None):
            target.db.exp = exp_total
            target.db.realm = "炼气6阶"
            return {"display_name": "炼气6阶"}

        with (
            patch("commands.devtools.ensure_character_model"),
            patch("commands.devtools.sync_cultivation_progression", side_effect=fake_sync),
            patch(
                "commands.devtools.get_stats",
                return_value={
                    "stage": "cultivator",
                    "realm": "炼气6阶",
                    "realm_info": {
                        "stage_bucket": "中阶",
                        "cultivation_exp_total": 250,
                    },
                },
            ),
        ):
            command.func()

        self.assertEqual(caller.db.character_stage, "cultivator")
        self.assertEqual(caller.db.exp, 250)
        self.assertEqual(caller.db.realm, "炼气6阶")
        self.assertIn("炼气6阶", "".join(caller.messages))

    def test_test_realm_can_set_breakthrough_ready_state(self):
        caller = FakeCaller()
        caller.db.spiritual_root = "water"
        command = CmdTestRealm()
        command.caller = caller
        command.args = "炼气可突破"

        def fake_sync(target, *, exp_total=None, current_realm=None, realm_key=None):
            target.db.exp = exp_total
            target.db.realm = "炼气10阶"
            return {"display_name": "炼气10阶"}

        with (
            patch("commands.devtools.ensure_character_model"),
            patch("commands.devtools.sync_cultivation_progression", side_effect=fake_sync),
            patch(
                "commands.devtools.get_stats",
                return_value={
                    "stage": "cultivator",
                    "realm": "炼气10阶",
                    "realm_info": {
                        "stage_bucket": "巅峰",
                        "cultivation_exp_total": 750,
                    },
                },
            ),
        ):
            command.func()

        self.assertEqual(caller.db.exp, 750)
        self.assertEqual(caller.db.realm, "炼气10阶")
        self.assertIn("750", "".join(caller.messages))

    def test_test_cultivation_exp_sets_total_exp(self):
        caller = FakeCaller()
        caller.db.progression = {"realm_key": "qi_refining"}
        command = CmdTestCultivationExp()
        command.caller = caller
        command.args = "330"

        def fake_set_total(target, exp_total):
            target.db.exp = exp_total
            target.db.realm = "炼气7阶"
            return {"realm": "炼气7阶", "exp": exp_total}

        with (
            patch("commands.devtools.ensure_character_model"),
            patch("commands.devtools.set_total_cultivation_exp", side_effect=fake_set_total),
            patch(
                "commands.devtools.get_stats",
                return_value={
                    "realm": "炼气7阶",
                    "realm_info": {
                        "cultivation_exp_in_stage": 0,
                        "cultivation_exp_required": 90,
                    },
                },
            ),
        ):
            command.func()

        self.assertEqual(caller.db.exp, 330)
        self.assertEqual(caller.db.realm, "炼气7阶")
        self.assertIn("炼气7阶", "".join(caller.messages))

    def test_test_cultivation_exp_warns_when_target_is_awakened_realm(self):
        caller = FakeCaller()
        caller.db.progression = {"realm_key": None}
        command = CmdTestCultivationExp()
        command.caller = caller
        command.args = "750"

        with (
            patch("commands.devtools.ensure_character_model"),
            patch("commands.devtools.set_total_cultivation_exp", return_value={"realm": "启灵", "exp": 750}),
            patch(
                "commands.devtools.get_stats",
                return_value={
                    "realm": "启灵",
                    "realm_info": {
                        "cultivation_exp_in_stage": 0,
                        "cultivation_exp_required": 0,
                    },
                },
            ),
        ):
            command.func()

        self.assertIn("启灵过渡态", "".join(caller.messages))

    def test_test_stamina_sets_current_stamina(self):
        caller = FakeCaller()
        command = CmdTestStamina()
        command.caller = caller
        command.args = "12"

        with patch("commands.devtools.get_stats", return_value={"max_stamina": 67}):
            command.func()

        self.assertEqual(caller.db.stamina, 12)
        self.assertIn("12/67", "".join(caller.messages))

    def test_test_realm_status_renders_progression_snapshot(self):
        caller = FakeCaller()
        command = CmdTestRealmStatus()
        command.caller = caller
        command.args = ""

        with patch(
            "commands.devtools.get_stats",
            return_value={
                "stage": "cultivator",
                "realm": "炼气6阶",
                "realm_display": "炼气6阶",
                "realm_info": {
                    "stage_bucket": "中阶",
                    "cultivation_exp_total": 271,
                    "cultivation_exp_in_stage": 21,
                    "cultivation_exp_required": 80,
                    "breakthrough_state": "progressing",
                },
            },
        ), patch("commands.devtools.get_progression_hint", return_value="距离 炼气6阶 下一阶还差 59 修为"):
            command.func()

        text = "".join(caller.messages)
        self.assertIn("炼气6阶", text)
        self.assertIn("59 修为", text)
        self.assertIn("炼气6阶·测试者", text)

    def test_test_choose_root_moves_to_spirit_stone_and_sets_root(self):
        caller = FakeCaller()
        command = CmdTestChooseRoot()
        command.caller = caller
        command.args = "水"
        room = SimpleNamespace(key="升仙台")
        spirit_stone = SimpleNamespace(key="测灵石")

        with (
            patch("commands.devtools._find_room_by_content_id", return_value=room),
            patch("commands.devtools._find_object_by_content_id", return_value=spirit_stone),
            patch("commands.devtools.reset_spiritual_root"),
            patch(
                "commands.devtools.trigger_object",
                return_value={"ok": True, "root": "water", "root_label": "水灵根"},
            ),
        ):
            command.func()

        self.assertEqual(caller.location, room)
        self.assertTrue(caller.db.guide_quest_stage_two_rewarded)
        self.assertTrue(caller.db.guide_quest_stage_three_rewarded)
        self.assertFalse(caller.db.guide_quest_root_awakened)
        self.assertFalse(caller.db.guide_quest_qi_guided)
        self.assertIn("水灵根", "".join(caller.messages))

    def test_test_reset_root_moves_to_platform_and_resets_state(self):
        caller = FakeCaller()
        caller.db.guide_quest = "completed"
        caller.db.guide_quest_root_awakened = True
        caller.db.character_stage = "cultivator"
        caller.db.spiritual_root = "water"
        command = CmdTestResetRoot()
        command.caller = caller
        command.args = ""
        room = SimpleNamespace(key="升仙台")

        with (
            patch("commands.devtools._find_room_by_content_id", return_value=room),
            patch("commands.devtools.reset_spiritual_root"),
        ):
            command.func()

        self.assertEqual(caller.location, room)
        self.assertTrue(caller.db.guide_quest_stage_two_rewarded)
        self.assertTrue(caller.db.guide_quest_stage_three_rewarded)
        self.assertFalse(caller.db.guide_quest_root_awakened)
        self.assertFalse(caller.db.guide_quest_qi_guided)
        self.assertIn("待选择状态", "".join(caller.messages))

    def test_test_battle_room_moves_caller_to_battle_yard(self):
        caller = FakeCaller()
        command = CmdTestBattleRoom()
        command.caller = caller
        command.args = ""
        room = SimpleNamespace(key="试战木场")

        with patch("commands.devtools._find_room_by_content_id", return_value=room):
            command.func()

        self.assertEqual(caller.location, room)
        self.assertIn("试战木场", "".join(caller.messages))

    def test_test_refresh_enemy_resets_enemy_hp(self):
        caller = FakeCaller()
        enemy = SimpleNamespace(
            key="试战恶徒",
            db=SimpleNamespace(enemy_id="battle_yard_ruffian", battle_id="battle_1", hp=12, max_hp=60, combat_stats={"hp": 12, "max_hp": 60}),
        )
        caller.location = SimpleNamespace(contents=[enemy])
        command = CmdTestRefreshEnemy()
        command.caller = caller
        command.args = ""

        with (
            patch("commands.devtools.is_enemy", return_value=True),
            patch(
                "commands.devtools.ensure_enemy_model",
                return_value={"combat_stats": {"hp": 60, "max_hp": 60}},
            ),
            patch("commands.devtools.get_enemy_definition", return_value={"id": "enemy_battle_yard_ruffian"}),
        ):
            command.func()

        self.assertEqual(enemy.db.battle_id, None)
        self.assertEqual(enemy.db.hp, 60)
        self.assertEqual(enemy.db.combat_stats["hp"], 60)
        self.assertIn("HP 60/60", "".join(caller.messages))

    def test_test_reset_battle_restores_character_resources(self):
        caller = FakeCaller()
        caller.db.battle_id = "battle_1"
        caller.db.hp = 12
        caller.db.mp = 1
        caller.db.stamina = 3
        command = CmdTestResetBattle()
        command.caller = caller
        command.args = ""

        with patch(
            "commands.devtools.get_stats",
            return_value={"max_hp": 100, "max_mp": 20, "max_stamina": 50},
        ):
            command.func()

        self.assertEqual(caller.db.battle_id, None)
        self.assertEqual(caller.db.hp, 100)
        self.assertEqual(caller.db.mp, 20)
        self.assertEqual(caller.db.stamina, 50)
        self.assertIn("测试重置战斗完成", "".join(caller.messages))

    def test_test_spawn_beast_creates_enemy_in_current_room(self):
        caller = FakeCaller()
        caller.location = SimpleNamespace(key="试战木场")
        command = CmdTestSpawnBeast()
        command.caller = caller
        command.args = ""

        with patch("commands.devtools.spawn_enemy_instance", return_value=SimpleNamespace(key="雾行山魈")) as mock_spawn:
            command.func()

        mock_spawn.assert_called_once_with("mist_ape", caller.location)
        self.assertIn("雾行山魈", "".join(caller.messages))

    def test_test_spawn_cultivator_creates_enemy_in_current_room(self):
        caller = FakeCaller()
        caller.location = SimpleNamespace(key="试战木场")
        command = CmdTestSpawnCultivatorEnemy()
        command.caller = caller
        command.args = ""

        with patch("commands.devtools.spawn_enemy_instance", return_value=SimpleNamespace(key="试战散修")) as mock_spawn:
            command.func()

        mock_spawn.assert_called_once_with("battle_yard_renegade_disciple", caller.location)
        self.assertIn("试战散修", "".join(caller.messages))

    def test_test_adjust_npc_relationship_updates_metric(self):
        caller = FakeCaller()
        npc = SimpleNamespace(key="守渡老人", db=SimpleNamespace(content_id="npc_old_ferryman"))
        caller.location = SimpleNamespace()
        caller.search = lambda query, location=None: npc if query == "守渡老人" else None
        command = CmdTestAdjustNpcRelationship()
        command.caller = caller
        command.args = "守渡老人 好感 12"

        with (
            patch("commands.devtools.find_npc_in_room", return_value=npc),
            patch("commands.devtools.get_npc_sheet", return_value={"identity": {"content_id": "npc_old_ferryman"}}),
            patch("commands.devtools.adjust_npc_relationship_metric", return_value={"affection": 12}),
        ):
            command.func()

        self.assertIn("好感 +12", "".join(caller.messages))

    def test_test_reset_npc_relationship_clears_record(self):
        caller = FakeCaller()
        npc = SimpleNamespace(key="守渡老人", db=SimpleNamespace(content_id="npc_old_ferryman"))
        caller.location = SimpleNamespace()
        caller.search = lambda query, location=None: npc if query == "守渡老人" else None
        command = CmdTestResetNpcRelationship()
        command.caller = caller
        command.args = "守渡老人"

        with (
            patch("commands.devtools.find_npc_in_room", return_value=npc),
            patch("commands.devtools.get_npc_sheet", return_value={"identity": {"content_id": "npc_old_ferryman"}}),
            patch("commands.devtools.clear_npc_relationship"),
            patch("commands.devtools.get_npc_relationship", return_value={"affection": 0, "reputation": 0, "trust": 0}),
        ):
            command.func()

        self.assertIn("关系已恢复默认", "".join(caller.messages))

    def test_test_force_battle_starts_battle_against_room_enemies(self):
        caller = FakeCaller()
        enemy = SimpleNamespace(key="试战恶徒")
        caller.location = SimpleNamespace(key="试战木场", contents=[enemy])
        command = CmdTestForceBattle()
        command.caller = caller
        command.args = ""

        with (
            patch("commands.devtools.is_enemy", side_effect=lambda obj: obj is enemy),
            patch(
                "commands.devtools.start_battle",
                return_value={"ok": True, "battle": {"battle_id": "battle_1", "participants": [caller, enemy]}},
            ) as mock_start,
        ):
            command.func()

        mock_start.assert_called_once_with(caller, [enemy], team_mode=True)
        self.assertIn("battle_1", "".join(caller.messages))

    def test_test_clear_battle_ends_active_battle(self):
        caller = FakeCaller()
        caller.db.battle_id = "battle_1"
        command = CmdTestClearBattle()
        command.caller = caller
        command.args = ""

        with patch(
            "commands.devtools.clear_battle",
            return_value={"battle_id": "battle_1", "status": "finished"},
        ) as mock_clear:
            command.func()

        mock_clear.assert_called_once_with(caller, reset_players=True, reset_enemies=True)
        self.assertIn("battle_1", "".join(caller.messages))

    def test_test_battle_log_formats_entries(self):
        caller = FakeCaller()
        caller.db.battle_id = "battle_1"
        command = CmdTestBattleLog()
        command.caller = caller
        command.args = ""

        with patch(
            "commands.devtools.get_battle_log",
            return_value=[
                {"type": "basic_attack", "actor_name": "测试者", "target_name": "试战恶徒", "value": 12},
                {"type": "guard", "actor_name": "试战恶徒", "card_id": "guard", "value": 8},
            ],
        ):
            command.func()

        text = "".join(caller.messages)
        self.assertIn("战斗日志 battle_1", text)
        self.assertIn("造成 12 点伤害", text)
        self.assertIn("使用 防御", text)
        self.assertIn("获得 8 点护盾", text)


if __name__ == "__main__":
    unittest.main()
