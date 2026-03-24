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

from systems import trade  # noqa: E402


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


class FakeItem:
    def __init__(self, key, object_id, location):
        self.key = key
        self.id = object_id
        self.location = location
        self.db = SimpleNamespace(is_item=True, item_id=None)

    def move_to(self, destination, **kwargs):
        self.location = destination
        return True


class FakeCharacter:
    def __init__(self, key, account, pk, copper=0, location=None):
        self.key = key
        self.account = account
        self.id = pk
        self.pk = pk
        self.location = location
        self.contents = []
        self.db = SimpleNamespace(
            copper=copper,
            realm="炼气一层",
            hp=100,
            max_hp=100,
            stamina=50,
            max_stamina=50,
            exp=0,
            temp_effects={},
            character_profile=None,
        )

    def contents_get(self, content_type=None):
        return list(self.contents)

    def msg(self, text=None, *args, **kwargs):
        self.account.msg(text, *args, **kwargs)


class FakeChannel:
    def __init__(self, key):
        self.key = key
        self.db_key = key
        self.connected = []
        self.db = SimpleNamespace(mute_list=[])
        self.lockstrings = []
        self.locks = SimpleNamespace(add=self._add_locks)
        self.aliases = SimpleNamespace(clear=lambda: None)

    @property
    def mutelist(self):
        return self.db.mute_list or []

    def _add_locks(self, lockstring):
        self.lockstrings.append(lockstring)

    def save(self, update_fields=None):
        return None


class TradeSystemTests(unittest.TestCase):
    def setUp(self):
        self.registry = {}
        self.channels = {}
        self.room = object()
        self.other_room = object()
        self.sender_account = FakeAccount("sender_account")
        self.target_account = FakeAccount("target_account")
        self.other_account = FakeAccount("other_account")
        self.sender = FakeCharacter("甲", self.sender_account, 11, copper=5, location=self.room)
        self.target = FakeCharacter("乙", self.target_account, 12, copper=30, location=self.room)
        self.other = FakeCharacter("丙", self.other_account, 13, copper=0, location=self.other_room)
        self.sender_account.db._last_puppet = self.sender
        self.target_account.db._last_puppet = self.target
        self.other_account.db._last_puppet = self.other
        self.item = FakeItem("青木碎片", 101, self.sender)
        self.sender.contents.append(self.item)
        self.by_name = {"甲": self.sender, "乙": self.target, "丙": self.other, "sender_account": self.sender, "target_account": self.target}
        self.by_id = {11: self.sender, 12: self.target, 13: self.other, 101: self.item}

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

    def _search_object(self, name):
        if isinstance(name, str) and name.startswith("#"):
            obj = self.by_id.get(int(name[1:]))
            return [obj] if obj else []
        obj = self.by_name.get(name)
        return [obj] if obj else []

    def _search_account(self, name):
        account_map = {
            "sender_account": self.sender_account,
            "target_account": self.target_account,
            "other_account": self.other_account,
        }
        account = account_map.get(name)
        return [account] if account else []

    def _search_channel(self, name):
        channel = self.channels.get(name)
        return [channel] if channel else []

    def _create_channel(self, key, **kwargs):
        channel = FakeChannel(key)
        self.channels[key] = channel
        return channel

    def _patch_all(self):
        return patch.multiple(
            "systems.trade.evennia",
            search_object=self._search_object,
            search_account=self._search_account,
        ), patch.multiple(
            "systems.chat.evennia",
            search_channel=self._search_channel,
            create_channel=self._create_channel,
            search_object=self._search_object,
            search_account=self._search_account,
            SESSION_HANDLER=SimpleNamespace(get_sessions=lambda: []),
        ), patch("systems.trade.ServerConfig.objects.conf", side_effect=self._conf)

    def test_create_and_accept_free_trade_offer_moves_item(self):
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            created = trade.create_trade_offer(self.sender, "乙", "青木碎片")
            accepted = trade.accept_trade_offer(self.target, "甲")

        self.assertTrue(created["ok"])
        self.assertTrue(accepted["ok"])
        self.assertEqual(self.item.location, self.target)
        self.assertIn("你接受了来自 甲 的交易", "".join(self.target_account.messages))
        self.assertIn("乙 接受了你的交易", "".join(self.sender_account.messages))

    def test_accept_priced_trade_transfers_currency(self):
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            trade.create_trade_offer(self.sender, "乙", "青木碎片", 12)
            result = trade.accept_trade_offer(self.target, "甲")

        self.assertTrue(result["ok"])
        self.assertEqual(self.target.db.copper, 18)
        self.assertEqual(self.sender.db.copper, 17)
        self.assertEqual(self.item.location, self.target)

    def test_reject_trade_notifies_sender(self):
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            trade.create_trade_offer(self.sender, "乙", "青木碎片")
            result = trade.reject_trade_offer(self.target, "甲")

        self.assertTrue(result["ok"])
        self.assertIn("乙 拒绝了你的交易", "".join(self.sender_account.messages))

    def test_trade_requires_same_room(self):
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            result = trade.create_trade_offer(self.sender, "丙", "青木碎片")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "target_not_nearby")

    def test_trade_accept_checks_currency(self):
        self.target.db.copper = 3
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            trade.create_trade_offer(self.sender, "乙", "青木碎片", 12)
            result = trade.accept_trade_offer(self.target, "甲")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "not_enough_money")

    def test_cancel_trade_notifies_target(self):
        trade_patch, chat_patch, conf_patch = self._patch_all()
        with trade_patch, chat_patch, conf_patch:
            trade.create_trade_offer(self.sender, "乙", "青木碎片")
            result = trade.cancel_trade_offer(self.sender, "乙")

        self.assertTrue(result["ok"])
        self.assertIn("甲 取消了发给你的交易", "".join(self.target_account.messages))


if __name__ == "__main__":
    unittest.main()
