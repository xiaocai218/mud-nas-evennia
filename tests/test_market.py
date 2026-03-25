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

from commands.market import CmdClaimMarketEarnings, CmdListMarketItem, CmdListMyMarket, CmdMarket  # noqa: E402
from systems import market, trade  # noqa: E402


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


class FakeRoom:
    def __init__(self, room_id):
        self.db = SimpleNamespace(room_id=room_id, content_id=f"room_{room_id}")


class FakeItem:
    def __init__(self, key, object_id, location):
        self.key = key
        self.id = object_id
        self.location = location
        self.db = SimpleNamespace(is_item=True, item_id=None, market_listing_id=None, desc=f"{key}说明")

    def move_to(self, destination, **kwargs):
        self.location = destination
        return True

    def save(self):
        return None


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


class MarketSystemTests(unittest.TestCase):
    def setUp(self):
        self.registry = {}
        self.channels = {}
        self.market_room = FakeRoom("outer_market")
        self.other_room = FakeRoom("qingyundu")
        self.seller_account = FakeAccount("seller_account")
        self.buyer_account = FakeAccount("buyer_account")
        self.other_account = FakeAccount("other_account")
        self.seller = FakeCharacter("甲", self.seller_account, 11, copper=5, location=self.market_room)
        self.buyer = FakeCharacter("乙", self.buyer_account, 12, copper=30, location=self.market_room)
        self.other = FakeCharacter("丙", self.other_account, 13, copper=8, location=self.market_room)
        self.seller_account.db._last_puppet = self.seller
        self.buyer_account.db._last_puppet = self.buyer
        self.other_account.db._last_puppet = self.other
        self.item = FakeItem("青木碎片", 101, self.seller)
        self.other_item = FakeItem("止血散", 102, self.seller)
        self.seller.contents.extend([self.item, self.other_item])
        self.by_name = {"甲": self.seller, "乙": self.buyer, "丙": self.other}
        self.by_id = {11: self.seller, 12: self.buyer, 13: self.other, 101: self.item, 102: self.other_item}

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
            "seller_account": self.seller_account,
            "buyer_account": self.buyer_account,
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
        return (
            patch.multiple(
                "systems.market.evennia",
                search_object=self._search_object,
            ),
            patch.multiple(
                "systems.trade.evennia",
                search_object=self._search_object,
                search_account=self._search_account,
            ),
            patch.multiple(
                "systems.chat.evennia",
                search_channel=self._search_channel,
                create_channel=self._create_channel,
                search_object=self._search_object,
                search_account=self._search_account,
                SESSION_HANDLER=SimpleNamespace(get_sessions=lambda: []),
            ),
            patch("systems.market.ServerConfig.objects.conf", side_effect=self._conf),
            patch("systems.trade.ServerConfig.objects.conf", side_effect=self._conf),
        )

    def test_create_listing_moves_item_out_of_inventory_and_blocks_trade(self):
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            created = market.create_market_listing(self.seller, "青木碎片", 12)
            traded = trade.create_trade_offer(self.seller, "乙", "青木碎片", 12)

        self.assertTrue(created["ok"])
        self.assertIsNone(self.item.location)
        self.assertFalse(traded["ok"])
        self.assertEqual(traded["reason"], "item_not_found")

    def test_buy_listing_moves_item_and_accumulates_pending_earnings(self):
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            created = market.create_market_listing(self.seller, "青木碎片", 12)
            result = market.buy_market_listing(self.buyer, created["listing"]["id"])
            status = market.list_my_market_status(self.seller)

        self.assertTrue(result["ok"])
        self.assertEqual(self.item.location, self.buyer)
        self.assertEqual(self.buyer.db.copper, 18)
        self.assertEqual(self.seller.db.copper, 5)
        self.assertEqual(status["pending_earnings"], 12)
        self.assertIn("乙 购买了你在 外门坊市 挂牌的 青木碎片", "".join(self.seller_account.messages))

    def test_claim_market_earnings_adds_currency(self):
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            created = market.create_market_listing(self.seller, "青木碎片", 12)
            market.buy_market_listing(self.buyer, created["listing"]["id"])
            claimed = market.claim_market_earnings(self.seller)

        self.assertTrue(claimed["ok"])
        self.assertEqual(self.seller.db.copper, 17)
        self.assertIn("你从 外门坊市 领取了 12 铜钱", "".join(self.seller_account.messages))

    def test_expired_listing_can_be_reclaimed(self):
        self.registry[market.MARKET_REGISTRY_KEY] = {
            "counter": 1,
            "listings": {
                "1": {
                    "id": "1",
                    "market_id": "market_qingyun_outer_gate",
                    "seller_id": self.seller.id,
                    "seller_name": self.seller.key,
                    "item_object_id": self.item.id,
                    "item_name": self.item.key,
                    "price": 12,
                    "currency": "铜钱",
                    "status": "active",
                    "created_at": 100,
                    "expires_at": 101,
                }
            },
            "pending_earnings": {},
        }
        self.item.location = None
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with patch("systems.market.time.time", return_value=200), market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            result = market.cancel_market_listing(self.seller, "1")
            status = market.list_my_market_status(self.seller)

        self.assertTrue(result["ok"])
        self.assertEqual(self.item.location, self.seller)
        self.assertEqual(status["reclaimable"], [])

    def test_market_command_requires_market_room(self):
        self.seller.location = self.other_room
        command = CmdMarket()
        command.caller = self.seller
        command.args = ""
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            command.func()

        self.assertIn("这里只有在坊市里才能操作寄售", "".join(self.seller_account.messages))

    def test_market_command_lists_listing_rows(self):
        command = CmdMarket()
        command.caller = self.seller
        command.args = ""
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            market.create_market_listing(self.seller, "青木碎片", 12)
            command.func()

        message = "".join(self.seller_account.messages)
        self.assertIn("外门坊市", message)
        self.assertIn("#1", message)
        self.assertIn("青木碎片", message)
        self.assertIn("12 铜钱", message)
        self.assertIn("可用命令：坊市 [页码] [关键词]", message)

    def test_market_command_supports_paging(self):
        command = CmdMarket()
        command.caller = self.seller
        command.args = "2"
        self.registry[market.MARKET_REGISTRY_KEY] = {
            "counter": 3,
            "listings": {
                "1": {
                    "id": "1",
                    "market_id": "market_qingyun_outer_gate",
                    "seller_id": self.seller.id,
                    "seller_name": self.seller.key,
                    "item_object_id": self.item.id,
                    "item_name": "青木碎片",
                    "price": 12,
                    "currency": "铜钱",
                    "status": "active",
                    "created_at": 100,
                    "expires_at": 9999999999,
                },
                "2": {
                    "id": "2",
                    "market_id": "market_qingyun_outer_gate",
                    "seller_id": self.other.id,
                    "seller_name": self.other.key,
                    "item_object_id": self.other_item.id,
                    "item_name": "止血散",
                    "price": 8,
                    "currency": "铜钱",
                    "status": "active",
                    "created_at": 200,
                    "expires_at": 9999999999,
                },
                "3": {
                    "id": "3",
                    "market_id": "market_qingyun_outer_gate",
                    "seller_id": self.other.id,
                    "seller_name": self.other.key,
                    "item_object_id": 103,
                    "item_name": "回春散",
                    "price": 18,
                    "currency": "铜钱",
                    "status": "active",
                    "created_at": 300,
                    "expires_at": 9999999999,
                },
            },
            "pending_earnings": {},
        }
        with patch.dict("systems.market.MARKET_DEFINITIONS", {"qingyun_outer_market": {**market.MARKET_DEFINITIONS["qingyun_outer_market"], "visible_listings": 2}}, clear=True):
            market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
            with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
                command.func()

        message = "".join(self.seller_account.messages)
        self.assertIn("第 2 / 2 页，共 3 条", message)
        self.assertIn("青木碎片", message)
        self.assertNotIn("回春散", message)

    def test_market_command_supports_keyword_filter(self):
        command = CmdMarket()
        command.caller = self.seller
        command.args = "止血"
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            market.create_market_listing(self.seller, "青木碎片", 12)
            market.create_market_listing(self.seller, "止血散", 8)
            self.seller_account.messages.clear()
            command.func()

        message = "".join(self.seller_account.messages)
        self.assertIn("筛选：止血", message)
        self.assertIn("止血散", message)
        self.assertNotIn("青木碎片", message)

    def test_my_market_command_shows_summary(self):
        command = CmdListMyMarket()
        command.caller = self.seller
        command.args = ""
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            created = market.create_market_listing(self.seller, "青木碎片", 12)
            market.buy_market_listing(self.buyer, created["listing"]["id"])
            market.create_market_listing(self.seller, "止血散", 8)
            command.func()

        message = "".join(self.seller_account.messages)
        self.assertIn("概览：在售 1 条 / 已售 1 条 / 可取回 0 条", message)
        self.assertIn("待领取收益：12 铜钱", message)
        self.assertIn("在售：", message)
        self.assertIn("已售：", message)

    def test_claim_command_requires_market_room(self):
        self.seller.location = self.other_room
        command = CmdClaimMarketEarnings()
        command.caller = self.seller
        command.args = ""
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            command.func()

        self.assertIn("这里只有在坊市里才能操作寄售", "".join(self.seller_account.messages))

    def test_list_command_requires_price(self):
        command = CmdListMarketItem()
        command.caller = self.seller
        command.args = "青木碎片"
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            command.func()

        self.assertIn("用法：上架 物品名 价格", "".join(self.seller_account.messages))

    def test_list_command_echoes_listing_id_after_success(self):
        command = CmdListMarketItem()
        command.caller = self.seller
        command.args = "青木碎片 12"
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            command.func()

        self.assertIn("挂牌成功：#1 / 青木碎片 / 12 铜钱。", "".join(self.seller_account.messages))

    def test_claim_command_echoes_summary_after_success(self):
        command = CmdClaimMarketEarnings()
        command.caller = self.seller
        command.args = ""
        market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch = self._patch_all()
        with market_patch, trade_patch, chat_patch, market_conf_patch, trade_conf_patch:
            created = market.create_market_listing(self.seller, "青木碎片", 12)
            market.buy_market_listing(self.buyer, created["listing"]["id"])
            self.seller_account.messages.clear()
            command.func()

        self.assertIn("领取完成：12 铜钱。当前铜钱 17。", "".join(self.seller_account.messages))


if __name__ == "__main__":
    unittest.main()
