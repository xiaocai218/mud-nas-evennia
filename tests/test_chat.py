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

from systems import chat, event_bus  # noqa: E402


class FakeAccount:
    def __init__(self, username):
        self.username = username
        self.key = username
        self.pk = hash(username) & 0xFFFF
        self.is_authenticated = True
        self.messages = []
        self.db = SimpleNamespace(h5_event_queue=[], _last_puppet=None)

    def msg(self, text=None, *args, **kwargs):
        self.messages.append("" if text is None else str(text))


class FakeCharacter:
    def __init__(self, key, account, pk=1, team_id=None):
        self.key = key
        self.account = account
        self.pk = pk
        self.db = SimpleNamespace(team_id=team_id)


class FakeSession:
    def __init__(self, account, puppet=None):
        self.account = account
        self.puppet = puppet


class FakeChannel:
    def __init__(self, key):
        self.key = key
        self.db_key = key
        self.connected = []
        self.db = SimpleNamespace(mute_list=[])
        self.lockstrings = []
        self.locks = SimpleNamespace(add=self._add_locks)
        self.aliases = SimpleNamespace(clear=self._clear_aliases)
        self.saved_fields = []

    @property
    def mutelist(self):
        return self.db.mute_list or []

    def _add_locks(self, lockstring):
        self.lockstrings.append(lockstring)

    def _clear_aliases(self):
        return None

    def save(self, update_fields=None):
        self.saved_fields.append(update_fields or [])

    def has_connection(self, account):
        return account in self.connected

    def connect(self, account):
        if account not in self.connected:
            self.connected.append(account)
        self.unmute(account)
        return True

    def mute(self, account):
        if account not in self.db.mute_list:
            self.db.mute_list.append(account)

    def unmute(self, account):
        if account in self.db.mute_list:
            self.db.mute_list.remove(account)


class ChatSystemTests(unittest.TestCase):
    def setUp(self):
        self.sender_account = FakeAccount("sender_account")
        self.target_account = FakeAccount("target_account")
        self.other_account = FakeAccount("other_account")
        self.sender = FakeCharacter("甲", self.sender_account, pk=11)
        self.target = FakeCharacter("乙", self.target_account, pk=12)
        self.other = FakeCharacter("丙", self.other_account, pk=13)
        self.sender_account.db._last_puppet = self.sender
        self.target_account.db._last_puppet = self.target
        self.other_account.db._last_puppet = self.other
        self.channels = {}

    def _search_channel(self, name):
        for channel in self.channels.values():
            names = {channel.key, getattr(channel, "db_key", channel.key)}
            if name in names:
                return [channel]
        return []

    def _create_channel(self, key, **kwargs):
        channel = FakeChannel(key)
        self.channels[key] = channel
        return channel

    def _patch_evennia(self, sessions=None, search_object=None, search_account=None):
        return patch.multiple(
            "systems.chat.evennia",
            search_channel=self._search_channel,
            create_channel=self._create_channel,
            search_object=search_object or (lambda name: []),
            search_account=search_account or (lambda name: []),
            SESSION_HANDLER=SimpleNamespace(get_sessions=lambda: sessions or []),
        )

    def test_cleanup_managed_channel_nicks_removes_aliases(self):
        removed = []

        class FakeNicks:
            def remove(self, key, category=None, **kwargs):
                removed.append((key, category))

        account = SimpleNamespace(nicks=FakeNicks())
        with patch("systems.chat.DefaultChannel.remove_user_channel_alias") as mocked_remove:
            mocked_remove.side_effect = lambda user, alias, **kwargs: removed.append((alias, "channel_cleanup"))
            chat.cleanup_managed_channel_nicks(accounts=[account])
        removed_aliases = {alias for alias, _ in removed}
        self.assertIn("世界", removed_aliases)
        self.assertIn("系统", removed_aliases)
        self.assertIn("chat_world", removed_aliases)

    def test_world_message_delivers_to_online_accounts(self):
        sessions = [
            FakeSession(self.sender_account, puppet=self.sender),
            FakeSession(self.target_account, puppet=self.target),
        ]
        with self._patch_evennia(sessions=sessions):
            result = chat.send_world_message(self.sender, "大家好")
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"]["channel"], "world")
        self.assertIn("[世界] 甲: 大家好", self.sender_account.messages)
        self.assertIn("[世界] 甲: 大家好", self.target_account.messages)
        self.assertEqual(result["event"]["event"], "chat.message")

    def test_private_message_only_reaches_sender_and_target(self):
        sessions = [
            FakeSession(self.sender_account, puppet=self.sender),
            FakeSession(self.target_account, puppet=self.target),
            FakeSession(self.other_account, puppet=self.other),
        ]
        with self._patch_evennia(
            sessions=sessions,
            search_object=lambda name: [self.target] if name == "乙" else [],
        ):
            result = chat.send_private_message(self.sender, "乙", "在吗")
        self.assertTrue(result["ok"])
        self.assertIn("[私聊] 甲 -> 乙: 在吗", self.sender_account.messages)
        self.assertIn("[私聊] 甲 -> 乙: 在吗", self.target_account.messages)
        self.assertEqual(self.other_account.messages, [])

    def test_private_message_target_not_found(self):
        with self._patch_evennia():
            result = chat.send_private_message(self.sender, "未知", "在吗")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "target_not_found")

    def test_team_message_requires_team_membership(self):
        sessions = [FakeSession(self.sender_account, puppet=self.sender)]
        with self._patch_evennia(sessions=sessions):
            result = chat.send_team_message(self.sender, "集合")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "team_not_joined")

    def test_system_message_respects_mutelist(self):
        sessions = [
            FakeSession(self.sender_account, puppet=self.sender),
            FakeSession(self.target_account, puppet=self.target),
        ]
        with self._patch_evennia(sessions=sessions):
            chat.mute_channel(self.target, "系统")
            result = chat.send_system_message("服务器维护公告")
        self.assertTrue(result["ok"])
        self.assertIn("[系统] 服务器维护公告", self.sender_account.messages)
        self.assertEqual(self.target_account.messages, [])

    def test_system_channel_is_read_only(self):
        with self._patch_evennia():
            channel = chat._ensure_channel(chat.CHANNEL_SYSTEM)
        self.assertIn("send:false()", channel.lockstrings[-1])
        self.assertEqual(channel.db_key, "chat_system")

    def test_mute_and_unmute_world_channel(self):
        sessions = [
            FakeSession(self.sender_account, puppet=self.sender),
            FakeSession(self.target_account, puppet=self.target),
        ]
        with self._patch_evennia(sessions=sessions):
            mute_result = chat.mute_channel(self.target, "世界")
            self.assertTrue(mute_result["ok"])
            chat.send_world_message(self.sender, "第一条")
            self.assertEqual(self.target_account.messages, [])

            unmute_result = chat.unmute_channel(self.target, "世界")
            self.assertTrue(unmute_result["ok"])
            chat.send_world_message(self.sender, "第二条")
        self.assertIn("[世界] 甲: 第二条", self.target_account.messages)

    def test_event_queue_roundtrip(self):
        event = event_bus.chat_message_event({"channel": "world", "text": "hello"})
        event_bus.enqueue_account_event(self.sender_account, event)
        events = event_bus.pop_account_events(self.sender_account)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "chat.message")
        self.assertEqual(event_bus.pop_account_events(self.sender_account), [])


if __name__ == "__main__":
    unittest.main()
