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


from systems import action_router, client_protocol, serializers  # noqa: E402


class FakeExit:
    def __init__(self, key, destination):
        self.key = key
        self.destination = destination


class FakeRoom:
    def __init__(self, key, room_id, content_id, desc="room-desc", exits=None):
        self.key = key
        self.db = SimpleNamespace(room_id=room_id, content_id=content_id, desc=desc)
        self.exits = exits or {}


class FakeItem:
    def __init__(self, key, item_id, desc):
        self.key = key
        self.db = SimpleNamespace(item_id=item_id, desc=desc)


class FakeCaller:
    def __init__(self, key="tester", location=None):
        self.key = key
        self.location = location
        self.db = SimpleNamespace(
            character_profile="default",
            guide_quest=None,
            hp=None,
            max_hp=None,
            stamina=None,
            max_stamina=None,
            exp=None,
            copper=None,
            realm=None,
            temp_effects={},
        )
        self._search_map = {}
        self.messages = []

    def search(self, query, candidates=None, quiet=False, location=None):
        if candidates is not None:
            if hasattr(candidates, "items"):
                return candidates.get(query)
        if query in self._search_map:
            return self._search_map[query]
        return None

    def move_to(self, destination, quiet=True):
        self.location = destination

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class ClientProtocolTests(unittest.TestCase):
    def test_validate_action_message_success(self):
        ok, error = client_protocol.validate_action_message(
            {"type": "action", "action": "move", "payload": {"direction": "north"}}
        )
        self.assertTrue(ok)
        self.assertIsNone(error)

    def test_validate_action_message_missing_field(self):
        ok, error = client_protocol.validate_action_message(
            {"type": "action", "action": "move", "payload": {}}
        )
        self.assertFalse(ok)
        self.assertEqual(error, "missing_fields:direction")


class SerializerTests(unittest.TestCase):
    def test_serialize_character(self):
        caller = FakeCaller()
        inventory = [FakeItem("松纹草", "item_songwen_grass", "desc")]
        with (
            patch("systems.serializers.get_stats", return_value={
                "realm": "炼气一层",
                "hp": 90,
                "max_hp": 100,
                "stamina": 40,
                "max_stamina": 50,
                "exp": 12,
                "copper": 30,
            }),
            patch("systems.serializers.get_active_effect_text", return_value="无"),
            patch("systems.serializers.get_inventory_items", return_value=inventory),
        ):
            payload = serializers.serialize_character(caller)
        self.assertEqual(payload["name"], "tester")
        self.assertEqual(payload["realm"], "炼气一层")
        self.assertEqual(payload["inventory_count"], 1)
        self.assertEqual(payload["copper"], 30)

    def test_serialize_room_with_exits(self):
        target_room = FakeRoom("古松林", "old_pine_forest", "room_old_pine_forest")
        room = FakeRoom(
            "青云渡",
            "qingyundu",
            "room_qingyundu",
            exits={"东": FakeExit("东", target_room)},
        )
        with (
            patch("systems.serializers.get_area_for_room", return_value={"id": "area_ferry", "key": "青云渡新手村"}),
            patch.dict("systems.serializers.AREA_DEFINITIONS", {"starter_area": {"id": "area_ferry", "key": "青云渡新手村"}}, clear=True),
            patch("systems.serializers.serialize_shop_in_room", return_value=None),
        ):
            payload = serializers.serialize_room(room)
        self.assertEqual(payload["key"], "青云渡")
        self.assertEqual(payload["area_key"], "starter_area")
        self.assertEqual(payload["exits"][0]["destination"], "古松林")


class ActionRouterTests(unittest.TestCase):
    def test_bootstrap_action(self):
        caller = FakeCaller()
        with patch("systems.action_router.build_bootstrap_payload", return_value={"ok": "bootstrap"}):
            response = action_router.dispatch_action(caller, "bootstrap", {})
        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["ok"], "bootstrap")

    def test_move_action(self):
        start_room = FakeRoom("青云渡", "qingyundu", "room_qingyundu")
        next_room = FakeRoom("问道石阶", "stone_steps", "room_stone_steps")
        caller = FakeCaller(location=start_room)
        start_room.exits = {"北": FakeExit("北", next_room)}
        with patch("systems.action_router.serialize_room", side_effect=lambda room: {"key": room.key}):
            response = action_router.dispatch_action(caller, "move", {"direction": "北"})
        self.assertTrue(response["ok"])
        self.assertEqual(caller.location.key, "问道石阶")
        self.assertEqual(response["payload"]["room"]["key"], "问道石阶")

    def test_read_action(self):
        caller = FakeCaller(location=FakeRoom("青云渡", "qingyundu", "room_qingyundu"))
        target = SimpleNamespace(key="渡口告示牌")
        caller._search_map["渡口告示牌"] = target
        with (
            patch("systems.action_router.is_readable", return_value=True),
            patch("systems.action_router.get_readable_text", return_value="公告内容"),
        ):
            response = action_router.dispatch_action(caller, "read", {"target": "渡口告示牌"})
        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["text"], "公告内容")

    def test_talk_action(self):
        caller = FakeCaller()
        target = SimpleNamespace(key="守渡老人", db=SimpleNamespace(npc_role="guide", talk_route="guide_main"))
        caller._search_map["守渡老人"] = target
        with patch("systems.action_router.run_npc_route", side_effect=lambda c, route: c.msg("任务已接取")):
            response = action_router.dispatch_action(caller, "talk", {"target": "守渡老人"})
        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["target"], "守渡老人")
        self.assertIn("任务已接取", response["payload"]["messages"])

    def test_attack_action(self):
        caller = FakeCaller()
        target = SimpleNamespace(key="青木傀儡", db=SimpleNamespace(combat_target=True))
        caller._search_map["青木傀儡"] = target
        with (
            patch("systems.action_router.attack_training_target", return_value={"ok": True, "result": "hit", "target_name": "青木傀儡"}),
            patch("systems.action_router.get_stats", return_value={"hp": 90, "max_hp": 100, "stamina": 42, "max_stamina": 50, "realm": "炼气一层", "exp": 10, "copper": 0}),
            patch("systems.action_router.serialize_inventory", return_value=[]),
        ):
            response = action_router.dispatch_action(caller, "attack", {"target": "青木傀儡"})
        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["result"]["target_name"], "青木傀儡")
        self.assertEqual(response["payload"]["character_stats"]["hp"], 90)

    def test_attack_action_not_attackable(self):
        caller = FakeCaller()
        target = SimpleNamespace(key="守渡老人", db=SimpleNamespace(combat_target=False))
        caller._search_map["守渡老人"] = target
        response = action_router.dispatch_action(caller, "attack", {"target": "守渡老人"})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "target_not_attackable")


if __name__ == "__main__":
    unittest.main()
