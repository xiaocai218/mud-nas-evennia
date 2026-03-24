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

from systems import chat, teams  # noqa: E402


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
    def __init__(self, key, account, pk):
        self.key = key
        self.account = account
        self.id = pk
        self.pk = pk
        self.db = SimpleNamespace(
            team_id=None,
            team_name=None,
            team_role=None,
            team_invites=[],
        )

    def msg(self, text=None, *args, **kwargs):
        self.account.msg(text, *args, **kwargs)


class FakeChannel:
    def __init__(self, key):
        self.key = key
        self.connected = []
        self.db = SimpleNamespace(mute_list=[])
        self.lockstrings = []
        self.locks = SimpleNamespace(add=self._add_locks)

    @property
    def mutelist(self):
        return self.db.mute_list or []

    def _add_locks(self, lockstring):
        self.lockstrings.append(lockstring)

    def has_connection(self, account):
        return account in self.connected

    def connect(self, account):
        if account not in self.connected:
            self.connected.append(account)
        return True

    def mute(self, account):
        if account not in self.db.mute_list:
            self.db.mute_list.append(account)

    def unmute(self, account):
        if account in self.db.mute_list:
            self.db.mute_list.remove(account)


class FakeSession:
    def __init__(self, account, puppet):
        self.account = account
        self.puppet = puppet


class TeamSystemTests(unittest.TestCase):
    def setUp(self):
        self.registry = {}
        self.channels = {}
        self.leader_account = FakeAccount("leader_account")
        self.member_account = FakeAccount("member_account")
        self.other_account = FakeAccount("other_account")
        self.leader = FakeCharacter("甲", self.leader_account, pk=11)
        self.member = FakeCharacter("乙", self.member_account, pk=12)
        self.other = FakeCharacter("丙", self.other_account, pk=13)
        self.by_id = {11: self.leader, 12: self.member, 13: self.other}
        self.by_name = {"甲": self.leader, "乙": self.member, "丙": self.other}
        self.leader_account.db._last_puppet = self.leader
        self.member_account.db._last_puppet = self.member
        self.other_account.db._last_puppet = self.other
        self.sessions = [
            FakeSession(self.leader_account, self.leader),
            FakeSession(self.member_account, self.member),
            FakeSession(self.other_account, self.other),
        ]

    def _search_channel(self, name):
        channel = self.channels.get(name)
        return [channel] if channel else []

    def _create_channel(self, key, **kwargs):
        channel = FakeChannel(key)
        self.channels[key] = channel
        return channel

    def _search_object(self, name):
        if isinstance(name, str) and name.startswith("#"):
            character = self.by_id.get(int(name[1:]))
            return [character] if character else []
        character = self.by_name.get(name)
        return [character] if character else []

    def _search_account(self, name):
        mapping = {
            "leader_account": self.leader_account,
            "member_account": self.member_account,
            "other_account": self.other_account,
        }
        account = mapping.get(name)
        return [account] if account else []

    def _conf(self, key=None, value=None, delete=False, default=None):
        if value is not None:
            self.registry[key] = value
            return None
        if delete:
            self.registry.pop(key, None)
            return None
        if key not in self.registry:
            return default() if callable(default) else default
        return self.registry[key]

    def _patch_all(self):
        return patch.multiple(
            "systems.teams.evennia",
            search_object=self._search_object,
            search_account=self._search_account,
            SESSION_HANDLER=SimpleNamespace(get_sessions=lambda: self.sessions),
        ), patch.multiple(
            "systems.chat.evennia",
            search_channel=self._search_channel,
            create_channel=self._create_channel,
            search_object=self._search_object,
            search_account=self._search_account,
            SESSION_HANDLER=SimpleNamespace(get_sessions=lambda: self.sessions),
        ), patch(
            "systems.teams.ServerConfig.objects.conf",
            side_effect=self._conf,
        )

    def test_create_invite_accept_and_team_chat(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with teams_patch, chat_patch, conf_patch:
            created = teams.create_team(self.leader, "巡山小队")
            self.assertTrue(created["ok"])
            invited = teams.invite_to_team(self.leader, "乙")
            self.assertTrue(invited["ok"])
            accepted = teams.accept_team_invite(self.member, "甲")
            self.assertTrue(accepted["ok"])
            self.assertEqual(self.member.db.team_id, self.leader.db.team_id)

            result = chat.send_team_message(self.leader, "集合")
            self.assertTrue(result["ok"])
            self.assertIn("[队伍] 甲: 集合", self.member_account.messages)

    def test_only_leader_can_invite(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
            teams.accept_team_invite(self.member, "甲")
            result = teams.invite_to_team(self.member, "丙")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "not_team_leader")

    def test_leave_team_promotes_next_leader(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
            teams.accept_team_invite(self.member, "甲")
            result = teams.leave_team(self.leader)
            snapshot = teams.get_team_snapshot(self.member)
        self.assertTrue(result["ok"])
        self.assertFalse(result["disbanded"])
        self.assertEqual(snapshot["leader_name"], "乙")
        self.assertEqual(self.member.db.team_role, "leader")

    def test_reject_invite_notifies_leader(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
            result = teams.reject_team_invite(self.member, "甲")
        self.assertTrue(result["ok"])
        self.assertIn("乙 拒绝了加入队伍", "".join(self.leader_account.messages))
        self.assertEqual(self.member.db.team_invites, [])

    def test_accept_expired_invite_returns_invite_expired(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with patch("systems.teams.time.time", return_value=1000), teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
        with patch("systems.teams.time.time", return_value=1000 + teams.INVITE_TTL_SECONDS + 1), teams_patch, chat_patch, conf_patch:
            result = teams.accept_team_invite(self.member, "甲")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "invite_expired")

    def test_list_team_status_returns_invite_details(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with patch("systems.teams.time.time", return_value=1000), teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
        with patch("systems.teams.time.time", return_value=1060), teams_patch, chat_patch, conf_patch:
            result = teams.list_team_status(self.member)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["pending_invites"]), 1)
        self.assertEqual(result["pending_invites"][0]["leader_name"], "甲")
        self.assertEqual(result["pending_invites"][0]["team_name"], "巡山小队")
        self.assertEqual(result["pending_invites"][0]["expires_in"], teams.INVITE_TTL_SECONDS - 60)

    def test_list_team_status_reports_expired_invite_cleanup(self):
        teams_patch, chat_patch, conf_patch = self._patch_all()
        with patch("systems.teams.time.time", return_value=1000), teams_patch, chat_patch, conf_patch:
            teams.create_team(self.leader, "巡山小队")
            teams.invite_to_team(self.leader, "乙")
        with patch("systems.teams.time.time", return_value=1000 + teams.INVITE_TTL_SECONDS + 1), teams_patch, chat_patch, conf_patch:
            result = teams.list_team_status(self.member)
        self.assertFalse(result["ok"])
        self.assertEqual(result["expired_invites_count"], 1)
        self.assertEqual(result["pending_invites"], [])


if __name__ == "__main__":
    unittest.main()
