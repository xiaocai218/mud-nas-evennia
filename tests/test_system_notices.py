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

from systems import combat, npc_routes, quests, shops  # noqa: E402


class FakeCaller:
    def __init__(self):
        self.key = "测试者"
        self.db = SimpleNamespace(stamina=50, hp=100)
        self.messages = []

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class FakeTarget:
    def __init__(self):
        self.key = "青木傀儡"
        self.db = SimpleNamespace(
            hp=10,
            max_hp=30,
            damage_taken=12,
            reward_exp=15,
            counter_damage=6,
            drop_item_id="item_greenwood_fragment",
            drop_key="青木碎片",
            drop_desc="desc",
            quest_flag="qingmu_kill",
        )


class SystemNoticeTests(unittest.TestCase):
    def test_shop_purchase_emits_system_notice(self):
        caller = FakeCaller()
        caller.location = SimpleNamespace(db=SimpleNamespace(room_id="general_store", content_id="general_store"))
        with (
            patch("systems.shops.get_shop_in_room", return_value={
                "key": "渡口杂货摊",
                "currency": "铜钱",
                "inventory": [{"item_id": "item_songwen_grass", "key": "松纹草", "price": 8}],
            }),
            patch("systems.shops.spend_currency", return_value=(True, 12)),
            patch("systems.shops.create_reward_item", return_value=SimpleNamespace(key="松纹草")),
            patch("systems.shops.notify_player") as notify_mock,
        ):
            result = shops.buy_item(caller, "松纹草")
        self.assertTrue(result["ok"])
        notify_mock.assert_called_once()
        self.assertIn("购买成功", notify_mock.call_args.args[1])

    def test_combat_kill_emits_system_notice(self):
        caller = FakeCaller()
        target = FakeTarget()
        with (
            patch("systems.combat.get_stats", return_value={"stamina": 50, "hp": 100, "max_hp": 100, "max_stamina": 50}),
            patch("systems.combat.apply_exp", return_value=("炼气一层", "炼气一层", 15)),
            patch("systems.combat.mark_combat_kill"),
            patch("systems.combat.notify_team_combat_kill"),
            patch("systems.combat.create_loot", return_value=SimpleNamespace(key="青木碎片")),
            patch("systems.combat.notify_player") as notify_mock,
        ):
            result = combat.attack_training_target(caller, target)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "kill")
        notify_mock.assert_called_once()
        self.assertIn("掉落：青木碎片", notify_mock.call_args.args[1])

    def test_combat_kill_notifies_same_area_teammates(self):
        caller = FakeCaller()
        teammate = FakeCaller()
        teammate.key = "队友"
        target = FakeTarget()
        with (
            patch("systems.combat.get_same_area_team_members", return_value=[teammate]),
            patch("systems.combat.notify_player") as notify_mock,
        ):
            result = combat.notify_team_combat_kill(caller, target)
        self.assertTrue(result)
        self.assertEqual(notify_mock.call_count, 2)
        self.assertIn("协同战斗提示", notify_mock.call_args_list[0].args[1])
        self.assertIn("奖励与掉落仍归击杀者个人所有", notify_mock.call_args_list[1].args[1])

    def test_combat_kill_skips_team_notice_without_teammates(self):
        caller = FakeCaller()
        target = FakeTarget()
        with (
            patch("systems.combat.get_same_area_team_members", return_value=[]),
            patch("systems.combat.notify_player") as notify_mock,
        ):
            result = combat.notify_team_combat_kill(caller, target)
        self.assertFalse(result)
        notify_mock.assert_not_called()

    def test_npc_route_start_main_stage_emits_system_notice(self):
        caller = FakeCaller()
        route = {
            "steps": [
                {
                    "condition": {"main_state_is": "not_started"},
                    "action": {"type": "start_main_stage", "stage": "stage_one_started", "dialogue": "common.talk_usage"},
                }
            ]
        }
        with (
            patch("systems.npc_routes.get_npc_route", return_value=route),
            patch("systems.npc_routes.get_quest_state", return_value="not_started"),
            patch("systems.npc_routes.get_dialogue", return_value="任务已接取"),
            patch("systems.npc_routes.set_main_quest_state"),
            patch("systems.npc_routes.notify_player") as notify_mock,
        ):
            result = npc_routes.run_npc_route(caller, "guide_main")
        self.assertTrue(result)
        notify_mock.assert_called_once()
        self.assertEqual(notify_mock.call_args.kwargs["code"], "quest_main_started")

    def test_npc_route_complete_main_stage_notifies_team(self):
        caller = FakeCaller()
        route = {
            "steps": [
                {
                    "condition": {"main_stage_completable": "stage_one_started"},
                    "action": {
                        "type": "complete_main_stage",
                        "stage": "stage_one_started",
                        "dialogue": "guide_old_ferryman.stage_one_complete",
                        "reward_label": "试炼奖励",
                    },
                }
            ]
        }
        with (
            patch("systems.npc_routes.get_npc_route", return_value=route),
            patch("systems.npc_routes.can_complete_main_stage", return_value=True),
            patch("systems.npc_routes.get_dialogue", return_value="任务完成"),
            patch("systems.npc_routes.complete_main_stage"),
            patch("systems.npc_routes.grant_stage_rewards", return_value={"reward_exp": 12, "reward": None, "old_realm": "炼气一层", "new_realm": "炼气一层", "exp": 12}),
            patch("systems.npc_routes.notify_team_main_stage_completed") as team_notice_mock,
            patch("systems.npc_routes.notify_player") as notify_mock,
        ):
            result = npc_routes.run_npc_route(caller, "guide_main")
        self.assertTrue(result)
        team_notice_mock.assert_called_once_with(caller, "stage_one_started")
        notify_mock.assert_called_once()

    def test_main_stage_delivery_notifies_team_members(self):
        caller = FakeCaller()
        teammate = FakeCaller()
        teammate.key = "队友"
        with patch("systems.quests.get_team_member_characters", return_value=[teammate]), patch(
            "systems.quests.send_system_message"
        ) as send_mock:
            result = quests.notify_team_main_stage_completed(caller, "stage_one_started")
        self.assertTrue(result)
        send_mock.assert_called_once()
        self.assertIn("已完成主线交付", send_mock.call_args.args[0])

    def test_main_stage_delivery_skips_team_notice_without_teammates(self):
        caller = FakeCaller()
        with patch("systems.quests.get_team_member_characters", return_value=[]), patch(
            "systems.quests.send_system_message"
        ) as send_mock:
            result = quests.notify_team_main_stage_completed(caller, "stage_one_started")
        self.assertFalse(result)
        send_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
