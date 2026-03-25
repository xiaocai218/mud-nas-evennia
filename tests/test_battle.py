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

from systems import battle  # noqa: E402
from commands.combat import CmdPlayCard, _render_battle_summary  # noqa: E402


class FakeCaller:
    def __init__(self, key="测试者"):
        self.key = key
        self.location = SimpleNamespace(db=SimpleNamespace(room_id="pine", area_id="starter"))
        self.db = SimpleNamespace(battle_id=None, hp=100, max_hp=100, mp=12, max_mp=12, stamina=50, max_stamina=50)
        self.messages = []

    def search(self, query, global_search=False, quiet=True, location=None):
        if query == "青云渡":
            return [SimpleNamespace(key="青云渡")]
        return None

    def move_to(self, destination, quiet=True):
        self.location = destination

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class FakeEnemy:
    def __init__(self, key="青木傀儡"):
        self.key = key
        self.location = SimpleNamespace(db=SimpleNamespace(room_id="pine", area_id="starter"))
        self.db = SimpleNamespace(
            battle_id=None,
            combat_target=True,
            enemy_id="qingmu_dummy",
            hp=30,
            max_hp=30,
            reward_exp=12,
            drop_item_id=None,
            drop_key=None,
            drop_desc=None,
            quest_flag="dummy_kill",
            combat_stats={},
        )


class BattleTests(unittest.TestCase):
    def setUp(self):
        battle.reset_battle_registry()

    def test_start_battle_creates_instance(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            result = battle.start_battle(caller, [enemy], team_mode=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "battle_started")
        self.assertEqual(result["battle"]["status"], "active")
        self.assertEqual(len(result["battle"]["participants"]), 2)

    def test_submit_action_basic_attack_updates_battle(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            battle.start_battle(caller, [enemy], team_mode=False)
            result = battle.submit_action(caller, "basic_attack")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["type"], "basic_attack")
        self.assertLess(result["battle"]["participants"][1]["hp"], 30)
        self.assertTrue(result["battle"]["round_reports"])
        self.assertEqual(result["battle"]["round_reports"][-1]["actor_side"], "enemy")

    def test_shield_skill_card_consumes_mp_and_enters_cooldown(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="试战恶徒")
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "water_barrier"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "试战恶徒", "tags": []},
                "combat_stats": {"hp": 60, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 50, "max_stamina": 50, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {"tags": []},
            }),
        ):
            battle.start_battle(caller, [enemy], team_mode=False)
            result = battle.submit_action(caller, "water_barrier")

        player_state = next(entry for entry in result["battle"]["participants"] if entry["side"] == "player")
        self.assertEqual(player_state["mp"], 7)
        self.assertEqual(player_state["cooldowns"]["water_barrier"], 1)
        self.assertGreater(player_state["shield"], 0)
        self.assertNotIn("水幕诀", [card["name"] for card in result["battle"]["available_cards"]])

    def test_attack_or_start_battle_does_not_auto_submit_first_basic_attack(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="试战恶徒")
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "试战恶徒"},
                "combat_stats": {"hp": 60, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 50, "max_stamina": 50, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            result = battle.attack_or_start_battle(caller, enemy)

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "battle_started")
        self.assertEqual(result["battle"]["participants"][1]["hp"], 60)
        self.assertFalse(result["battle"]["log"])
        self.assertEqual(result["battle"]["current_actor_name"], caller.key)

    def test_enemy_ai_uses_configured_recovery_rule(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="雾行山魈")
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 4},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "雾行山魈"},
                "combat_stats": {"hp": 12, "max_hp": 36, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 20},
                "enemy_meta": {
                    "battle_ai_profile": {"mode": "basic"},
                    "battle_card_pool": ["basic_attack", "recover_instinct"],
                    "decision_rules": [{"when": {"self_hp_lte_pct": 50, "card_ready": "recover_instinct"}, "use_card": "recover_instinct"}],
                },
            }),
        ):
            result = battle.start_battle(caller, [enemy], team_mode=False)
        self.assertTrue(result["ok"])
        self.assertTrue(any(entry.get("card_id") == "recover_instinct" for entry in result["battle"]["log"]))

    def test_apply_damage_clears_guard_effect_when_shield_is_spent(self):
        target = {"shield": 9, "effects": [{"type": "water_barrier", "shield": 9}], "hp": 30, "alive": True}

        damage = battle._apply_damage(target, 12)

        self.assertEqual(damage["damage"], 3)
        self.assertEqual(target["shield"], 0)
        self.assertEqual(target["effects"], [])

    def test_guard_reduces_next_basic_attack_and_is_consumed(self):
        target = {
            "shield": 0,
            "effects": [{"type": "guard", "damage_reduction_pct": 60, "block_chance_pct": 5}],
            "hp": 30,
            "alive": True,
        }

        with patch("systems.battle_effects.random.random", return_value=0.99):
            damage = battle._apply_damage(target, 10, attack_type="basic_attack")

        self.assertEqual(damage["damage"], 4)
        self.assertEqual(damage["guard_reduced"], 6)
        self.assertFalse(damage["guard_blocked"])
        self.assertEqual(target["hp"], 26)
        self.assertEqual(target["effects"], [])

    def test_guard_can_fully_block_basic_attack(self):
        target = {
            "shield": 0,
            "effects": [{"type": "guard", "damage_reduction_pct": 60, "block_chance_pct": 5}],
            "hp": 30,
            "alive": True,
        }

        with patch("systems.battle_effects.random.random", return_value=0.0):
            damage = battle._apply_damage(target, 10, attack_type="basic_attack")

        self.assertEqual(damage["damage"], 0)
        self.assertTrue(damage["guard_blocked"])
        self.assertEqual(target["hp"], 30)
        self.assertEqual(target["effects"], [])

    def test_test_enemy_is_reset_to_full_hp_when_battle_starts(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="试战恶徒")
        enemy.db.hp = 50
        enemy.db.max_hp = 60
        enemy.db.identity = {"kind": "enemy", "name": "试战恶徒", "enemy_type": "mortal_enemy", "tags": ["test_enemy"]}
        enemy.db.combat_stats = {"hp": 50, "max_hp": 60}
        enemy.db.enemy_meta = {"tags": ["test_enemy"]}
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard"]),
            patch(
                "systems.battle.get_enemy_sheet",
                side_effect=lambda target: {
                    "identity": {"name": "试战恶徒", "tags": ["test_enemy"]},
                    "combat_stats": {
                        "hp": target.db.hp,
                        "max_hp": 60,
                        "mp": 0,
                        "max_mp": 0,
                        "stamina": 50,
                        "max_stamina": 50,
                        "attack_power": 8,
                        "spell_power": 0,
                        "defense": 4,
                        "speed": 8,
                    },
                    "enemy_meta": {"tags": ["test_enemy"]},
                },
            ),
        ):
            result = battle.start_battle(caller, [enemy], team_mode=False)
        self.assertEqual(enemy.db.hp, 60)
        self.assertEqual(result["battle"]["participants"][1]["hp"], 60)

    def test_clear_battle_resets_ids_and_returns_cancelled_snapshot(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            started = battle.start_battle(caller, [enemy], team_mode=False)
            snapshot = battle.clear_battle(caller, reset_players=True, reset_enemies=True)
        self.assertEqual(started["battle"]["battle_id"], snapshot["battle_id"])
        self.assertEqual(snapshot["result"], "cancelled")
        self.assertEqual(caller.db.battle_id, None)
        self.assertEqual(enemy.db.battle_id, None)

    def test_get_battle_log_returns_latest_entries(self):
        caller = FakeCaller()
        enemy = FakeEnemy()
        with (
            patch("systems.battle.get_stats", return_value={
                "combat_stats": {"hp": 100, "max_hp": 100, "mp": 12, "max_mp": 12, "stamina": 50, "max_stamina": 50, "attack_power": 12, "spell_power": 10, "defense": 6, "speed": 14},
                "hp": 100,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 12,
                "stamina": 50,
                "max_stamina": 50,
            }),
            patch("systems.battle.get_player_battle_card_pool", return_value=["basic_attack", "guard", "spirit_blast"]),
            patch("systems.battle.get_enemy_sheet", return_value={
                "identity": {"name": "青木傀儡"},
                "combat_stats": {"hp": 30, "max_hp": 30, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "attack_power": 8, "spell_power": 0, "defense": 4, "speed": 8},
                "enemy_meta": {},
            }),
        ):
            battle.start_battle(caller, [enemy], team_mode=False)
            battle.submit_action(caller, "basic_attack")
            logs = battle.get_battle_log(caller, limit=5)
        self.assertTrue(logs)
        self.assertEqual(logs[-1]["type"], "basic_attack")

    def test_play_card_accepts_direct_card_command_alias(self):
        caller = FakeCaller()
        command = CmdPlayCard()
        command.caller = caller
        command.args = ""
        command.cmdstring = "防御"

        with (
            patch("commands.combat.get_battle_snapshot", return_value={"battle_id": "battle_1", "available_cards": [], "participants": [], "status": "active", "turn_count": 1, "current_actor_name": caller.key, "log": []}),
            patch("commands.combat.submit_action", return_value={"ok": True, "battle": {"battle_id": "battle_1", "available_cards": [], "participants": [], "status": "active", "turn_count": 1, "current_actor_name": caller.key, "log": [{"actor_name": caller.key, "card_id": "guard", "value": 8}]}}) as mock_submit,
        ):
            command.func()

        mock_submit.assert_called_once_with(caller, "guard", target_id=None, item_id=None)

    def test_victory_with_zero_exp_does_not_emit_false_realm_up_message(self):
        caller = FakeCaller()
        enemy = FakeEnemy(key="试战恶徒")
        enemy.db.reward_exp = 0
        battle_state = {
            "participants": [
                {"side": "player", "entity_ref": caller},
                {"side": "enemy", "entity_ref": enemy, "max_hp": 60},
            ]
        }

        with (
            patch("systems.battle.apply_exp", return_value=("炼气三层", "炼气四层", 90)),
            patch("systems.battle.mark_combat_kill"),
            patch("systems.battle.notify_player") as mock_notify,
        ):
            battle._grant_victory_rewards(battle_state)

        message = mock_notify.call_args.args[1]
        self.assertNotIn("修为 +0", message)
        self.assertNotIn("境界提升至", message)

    def test_finished_battle_clears_current_actor_in_snapshot(self):
        summary = _render_battle_summary(
            {
                "status": "finished",
                "turn_count": 7,
                "current_actor_name": None,
                "participants": [
                    {
                        "name": "测试者",
                        "side": "player",
                        "alive": True,
                        "hp": 90,
                        "max_hp": 100,
                        "mp": 12,
                        "max_mp": 20,
                        "stamina": 40,
                        "max_stamina": 50,
                        "shield": 0,
                        "cooldowns": {},
                    }
                ],
                "log": [],
                "available_cards": [{"name": "普通攻击"}],
            }
        )
        self.assertIn("当前行动者|n: 无", summary)
        self.assertIn("当前节奏|n: 当前没有可行动单位。", summary)
        self.assertNotIn("可用卡牌", summary)

    def test_render_battle_summary_groups_sides_and_recent_report(self):
        summary = _render_battle_summary(
            {
                "status": "active",
                "turn_count": 4,
                "current_actor_name": "测试者",
                "participants": [
                    {
                        "name": "测试者",
                        "side": "player",
                        "alive": True,
                        "hp": 90,
                        "max_hp": 100,
                        "mp": 12,
                        "max_mp": 20,
                        "stamina": 40,
                        "max_stamina": 50,
                        "shield": 8,
                        "resources": {"hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 8},
                        "cooldowns": {},
                        "effects": [{"type": "guard", "damage_reduction_pct": 60, "block_chance_pct": 5}],
                    },
                    {
                        "name": "试战恶徒",
                        "side": "enemy",
                        "alive": True,
                        "hp": 30,
                        "max_hp": 60,
                        "mp": 0,
                        "max_mp": 0,
                        "stamina": 30,
                        "max_stamina": 30,
                        "shield": 0,
                        "resources": {"hp": 30, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 0},
                        "cooldowns": {},
                        "effects": [],
                    },
                ],
                "log": [
                    {"type": "basic_attack", "actor_name": "试战恶徒", "target_name": "测试者", "value": 7},
                    {"type": "guard", "actor_name": "测试者", "card_id": "guard", "value": 60, "block_chance_pct": 5},
                ],
                "round_reports": [
                    {
                        "turn_count": 3,
                        "actor_name": "试战恶徒",
                        "actor_side": "enemy",
                        "entry": {
                            "type": "basic_attack",
                            "actor_name": "试战恶徒",
                            "target_name": "测试者",
                            "value": 7,
                            "action_result": {
                                "action_type": "basic_attack",
                                "result": {"damage": 7},
                                "modifiers": {"guard_blocked": False, "guard_reduced": 0, "shield_absorbed": 0},
                            },
                        },
                        "before": {
                            "player": [{"name": "测试者", "hp": 97, "max_hp": 100, "mp": 12, "max_mp": 20, "shield": 0, "resources": {"hp": 97, "max_hp": 100, "mp": 12, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 0}, "effects": []}],
                            "enemy": [{"name": "试战恶徒", "hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "shield": 0, "resources": {"hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 0}, "effects": []}],
                            "meta": {"alive_player_count": 1, "alive_enemy_count": 1},
                        },
                        "after": {
                            "player": [{"name": "测试者", "hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "shield": 0, "resources": {"hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 0}, "effects": []}],
                            "enemy": [{"name": "试战恶徒", "hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "shield": 0, "resources": {"hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 0}, "effects": []}],
                            "meta": {"alive_player_count": 1, "alive_enemy_count": 1},
                        },
                    },
                    {
                        "turn_count": 4,
                        "actor_name": "测试者",
                        "actor_side": "player",
                        "entry": {"type": "guard", "actor_name": "测试者", "card_id": "guard", "value": 60, "block_chance_pct": 5, "action_result": {"action_type": "guard", "result": {"damage": 0, "heal": 0, "shield_gain": 0}}},
                        "before": {
                            "player": [{"name": "测试者", "hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "shield": 0, "resources": {"hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 0}, "effects": []}],
                            "enemy": [{"name": "试战恶徒", "hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "shield": 0, "resources": {"hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 0}, "effects": []}],
                            "meta": {"alive_player_count": 1, "alive_enemy_count": 1},
                        },
                        "after": {
                            "player": [{"name": "测试者", "hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "shield": 0, "resources": {"hp": 90, "max_hp": 100, "mp": 12, "max_mp": 20, "stamina": 40, "max_stamina": 50, "shield": 0}, "effects": [{"type": "guard", "damage_reduction_pct": 60, "block_chance_pct": 5}]}],
                            "enemy": [{"name": "试战恶徒", "hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "shield": 0, "resources": {"hp": 40, "max_hp": 60, "mp": 0, "max_mp": 0, "stamina": 30, "max_stamina": 30, "shield": 0}, "effects": []}],
                            "meta": {"alive_player_count": 1, "alive_enemy_count": 1},
                        },
                    },
                ],
                "available_cards": [{"name": "普通攻击"}, {"name": "防御"}],
            }
        )

        self.assertIn("我方状态", summary)
        self.assertIn("敌方状态", summary)
        self.assertIn("战场摘要", summary)
        self.assertIn("我方存活 1 人 / 敌方存活 1 人", summary)
        self.assertIn("当前对阵", summary)
        self.assertIn("测试者(气血 90/100, 灵力 12/20, 护盾 8, 体力 40/50, 状态 防御(减普攻60%, 格挡5%))", summary)
        self.assertIn("试战恶徒(气血 30/60, 灵力 0/0, 护盾 0, 体力 30/30)", summary)
        self.assertIn("轮到你方行动", summary)
        self.assertIn("最近回合战报", summary)
        self.assertIn("敌方回合", summary)
        self.assertIn("我方回合", summary)
        self.assertIn("[存活 我方 1 / 敌方 1]", summary)
        self.assertIn("测试者 使用 防御，进入防御架势：普通攻击减伤 60%，并有 5% 概率完全格挡。", summary)


if __name__ == "__main__":
    unittest.main()
