import json
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

from django.test import RequestFactory  # noqa: E402

from web.api import views  # noqa: E402


class FakeCharacter:
    def __init__(self, key="tester", pk=7):
        self.key = key
        self.pk = pk
        self.location = None
        self.db = SimpleNamespace()


class FakeAccount:
    def __init__(self, characters=None, authenticated=True, last_puppet=None):
        self.is_authenticated = authenticated
        self.characters = characters or []
        self.db = SimpleNamespace(_last_puppet=last_puppet)
        self.id = 1
        self.pk = 1
        self.username = "tester"


class H5HttpRouteTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.character = FakeCharacter()
        self.account = FakeAccount(characters=[self.character], last_puppet=self.character)

    def _decode(self, response):
        return json.loads(response.content.decode("utf-8"))

    def test_protocol_overview_view(self):
        request = self.factory.get("/api/h5/")
        response = views.protocol_overview_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("attack", payload["payload"]["actions"])
        self.assertIn("login", payload["payload"]["routes"])
        self.assertIn("event_poll", payload["payload"]["routes"])
        self.assertIn("market_detail", payload["payload"]["routes"])

    def test_ws_meta_view_returns_poll_fallback(self):
        request = self.factory.get("/api/h5/ws-meta/")
        request.user = self.account
        request.session = {}
        response = views.ws_meta_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["payload"]["transports"]["poll"]["available"])
        self.assertEqual(payload["payload"]["poll_endpoint"], "/api/h5/events/poll/")
        self.assertIn("chat.message", payload["payload"]["events"]["supported"])

    def test_event_poll_view_requires_active_character(self):
        request = self.factory.get("/api/h5/events/poll/")
        request.user = SimpleNamespace(is_authenticated=False)
        request.session = {}
        response = views.event_poll_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload["error"]["code"], "not_authenticated")

    def test_event_poll_view_returns_empty_batch(self):
        request = self.factory.get("/api/h5/events/poll/?cursor=abc")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.pop_account_events", return_value=[]):
            response = views.event_poll_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["transport"], "poll")
        self.assertEqual(payload["payload"]["cursor"], "abc")
        self.assertEqual(payload["payload"]["events"], [])
        self.assertEqual(payload["payload"]["active_character_id"], 7)

    def test_event_poll_view_returns_chat_events(self):
        request = self.factory.get("/api/h5/events/poll/?cursor=next")
        request.user = self.account
        request.session = {}
        with patch(
            "web.api.views.pop_account_events",
            return_value=[{"event": "chat.message", "payload": {"channel": "world", "text": "hi"}}],
        ):
            response = views.event_poll_view(request)
        payload = self._decode(response)
        self.assertEqual(payload["payload"]["events"][0]["event"], "chat.message")

    def test_action_view_requires_active_character_for_chat(self):
        body = json.dumps({"type": "action", "action": "chat_world", "payload": {"text": "hi"}})
        request = self.factory.post("/api/h5/action/", data=body, content_type="application/json")
        request.user = SimpleNamespace(is_authenticated=False)
        request.session = {}
        response = views.action_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload["error"]["code"], "not_authenticated")

    def test_login_view_invalid_credentials(self):
        request = self.factory.post(
            "/api/h5/auth/login/",
            data=json.dumps({"username": "bad", "password": "bad"}),
            content_type="application/json",
        )
        request.session = {}
        request.user = SimpleNamespace(is_authenticated=False)
        with patch("web.api.views.authenticate", return_value=None):
            response = views.login_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload["error"]["code"], "invalid_credentials")

    def test_login_view_success(self):
        request = self.factory.post(
            "/api/h5/auth/login/",
            data=json.dumps({"username": "tester", "password": "pw"}),
            content_type="application/json",
        )
        request.session = {}
        request.user = SimpleNamespace(is_authenticated=False)
        account = FakeAccount(characters=[self.character], authenticated=True)
        account.id = 12
        account.pk = 12
        account.username = "tester"
        with (
            patch("web.api.views.authenticate", return_value=account),
            patch("web.api.views.login"),
            patch("web.api.views.serialize_character_summary", return_value={"id": 7, "key": "tester", "realm": "炼气一层"}),
            patch("web.api.views.serialize_account", return_value={"id": 12, "username": "tester", "is_authenticated": True}),
            patch("web.api.views._get_active_character", return_value=(self.character, None)),
        ):
            response = views.login_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["payload"]["active_character_id"], 7)

    def test_post_endpoints_are_csrf_exempt_for_h5_session_calls(self):
        self.assertTrue(getattr(views.login_view, "csrf_exempt", False))
        self.assertTrue(getattr(views.logout_view, "csrf_exempt", False))
        self.assertTrue(getattr(views.character_select_view, "csrf_exempt", False))
        self.assertTrue(getattr(views.ui_preferences_view, "csrf_exempt", False))
        self.assertTrue(getattr(views.action_view, "csrf_exempt", False))

    def test_logout_view(self):
        request = self.factory.post("/api/h5/auth/logout/")
        request.session = {"puppet": 7, "website_authenticated_uid": 1, "webclient_authenticated_uid": 1}
        request.user = self.account
        with patch("web.api.views.logout"):
            response = views.logout_view(request)
        payload = self._decode(response)
        self.assertTrue(payload["payload"]["logged_out"])
        self.assertIsNone(request.session["puppet"])

    def test_bootstrap_view_requires_authentication(self):
        request = self.factory.get("/api/h5/bootstrap/")
        request.user = SimpleNamespace(is_authenticated=False)
        request.session = {}
        response = views.bootstrap_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_authenticated")

    def test_bootstrap_view_returns_payload(self):
        request = self.factory.get("/api/h5/bootstrap/")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.build_bootstrap_payload", return_value={"character": {"name": "tester"}}):
            response = views.bootstrap_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["payload"]["character"]["name"], "tester")

    def test_chat_status_view_returns_recent_messages_and_preferences(self):
        request = self.factory.get("/api/h5/chat-status/")
        request.user = self.account
        request.session = {}
        with (
            patch(
                "web.api.views.serialize_chat_status",
                return_value={
                    "channels": [{"channel": "aggregate"}, {"channel": "world"}],
                    "recent_messages": [{"formatted": "[世界] hi"}],
                    "recent_combat_logs": [{"formatted": "回合 2 | hi", "type": "combat.log"}],
                },
            ),
            patch("web.api.views.serialize_ui_preferences", return_value={"chat_layout": {"dock": "right-sidebar"}}),
        ):
            response = views.chat_status_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["channels"][0]["channel"], "aggregate")
        self.assertEqual(payload["payload"]["recent_combat_logs"][0]["type"], "combat.log")
        self.assertEqual(payload["payload"]["ui_preferences"]["chat_layout"]["dock"], "right-sidebar")

    def test_battle_status_view_returns_summary(self):
        request = self.factory.get("/api/h5/battle-status/")
        request.user = self.account
        request.session = {}
        with (
            patch("web.api.views.get_battle_snapshot", return_value={"battle_id": "battle_1", "status": "active", "turn_count": 3, "current_actor_id": "obj_1", "log": [{"turn_count": 2}]}),
            patch("web.api.views.render_battle_summary", return_value="战斗状态: active / 回合数 3"),
        ):
            response = views.battle_status_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["battle"]["battle_id"], "battle_1")
        self.assertEqual(payload["payload"]["summary"], "战斗状态: active / 回合数 3")
        self.assertEqual(payload["payload"]["signature"], "battle_1:active:3:obj_1:2")

    def test_ui_preferences_get_view(self):
        request = self.factory.get("/api/h5/ui/preferences/")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.serialize_ui_preferences", return_value={"chat_layout": {"dock": "top-strip"}}):
            response = views.ui_preferences_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["ui_preferences"]["chat_layout"]["dock"], "top-strip")

    def test_ui_preferences_post_view_updates_preferences(self):
        request = self.factory.post(
            "/api/h5/ui/preferences/",
            data=json.dumps({"chat_layout": {"dock": "bottom-strip"}}),
            content_type="application/json",
        )
        request.user = self.account
        request.session = {}
        with patch("web.api.views.update_ui_preferences", return_value={"chat_layout": {"dock": "bottom-strip"}}):
            response = views.ui_preferences_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["ui_preferences"]["chat_layout"]["dock"], "bottom-strip")

    def test_character_list_view(self):
        request = self.factory.get("/api/h5/account/characters/")
        request.user = self.account
        request.session = {}
        with (
            patch("web.api.views.serialize_account", return_value={"id": 1, "username": "tester", "is_authenticated": True}),
            patch("web.api.views.serialize_character_summary", return_value={"id": 7, "key": "tester", "realm": "炼气一层"}),
        ):
            response = views.character_list_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["characters"][0]["id"], 7)

    def test_character_select_view(self):
        request = self.factory.post(
            "/api/h5/account/characters/select/",
            data=json.dumps({"character_id": 7}),
            content_type="application/json",
        )
        request.user = self.account
        request.session = {}
        with patch("web.api.views.build_bootstrap_payload", return_value={"character": {"name": "tester"}}):
            response = views.character_select_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["active_character_id"], 7)
        self.assertEqual(request.session["puppet"], 7)

    def test_quest_log_view_returns_structured_log(self):
        request = self.factory.get("/api/h5/quests/")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.serialize_quest_log", return_value={"main": {"id": "quest_main_stage_01"}, "side": []}):
            response = views.quest_log_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["quests"]["main"]["id"], "quest_main_stage_01")

    def test_shop_detail_view_returns_not_found(self):
        request = self.factory.get("/api/h5/shops/missing/")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.serialize_shop_by_id", return_value=None):
            response = views.shop_detail_view(request, "missing")
        payload = self._decode(response)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "shop_not_found")

    def test_shop_detail_view_returns_shop(self):
        request = self.factory.get("/api/h5/shops/shop_ferry_general_store/")
        request.user = self.account
        request.session = {}
        with (
            patch("web.api.views.serialize_shop_by_id", return_value={"id": "shop_ferry_general_store", "inventory": []}),
            patch("web.api.views.build_bootstrap_payload", return_value={"character": {"name": "tester"}}),
        ):
            response = views.shop_detail_view(request, "shop_ferry_general_store")
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["shop"]["id"], "shop_ferry_general_store")

    def test_market_detail_view_returns_not_found(self):
        request = self.factory.get("/api/h5/markets/missing/")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.serialize_market_by_id", return_value=None):
            response = views.market_detail_view(request, "missing")
        payload = self._decode(response)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "market_not_found")

    def test_market_detail_view_returns_market(self):
        request = self.factory.get("/api/h5/markets/market_qingyun_outer_gate/?page=2&keyword=青木")
        request.user = self.account
        request.session = {}
        with (
            patch(
                "web.api.views.serialize_market_by_id",
                return_value={"id": "market_qingyun_outer_gate", "listings": [], "paging": {"page": 2, "keyword": "青木"}},
            ),
            patch("web.api.views.build_bootstrap_payload", return_value={"character": {"name": "tester"}}),
        ):
            response = views.market_detail_view(request, "market_qingyun_outer_gate")
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["payload"]["market"]["id"], "market_qingyun_outer_gate")
        self.assertEqual(payload["payload"]["market"]["paging"]["page"], 2)

    def test_action_view_rejects_invalid_json(self):
        request = self.factory.post("/api/h5/action/", data=b"{bad", content_type="application/json")
        request.user = self.account
        request.session = {}
        response = views.action_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_json")

    def test_action_view_dispatches_message(self):
        body = json.dumps({"type": "action", "action": "look", "payload": {}})
        request = self.factory.post("/api/h5/action/", data=body, content_type="application/json")
        request.user = self.account
        request.session = {}
        with patch("web.api.views.dispatch_action", return_value={"type": "response", "ok": True, "payload": {"room": {"key": "青云渡"}}}):
            response = views.action_view(request)
        payload = self._decode(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["payload"]["room"]["key"], "青云渡")


if __name__ == "__main__":
    unittest.main()
