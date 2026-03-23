"""Cultivation and recovery commands."""

from .command import Command
from systems.player_stats import apply_exp, get_stats


class CmdCultivate(Command):
    key = "修炼"
    aliases = ["meditate", "xiulian"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        stats = get_stats(caller)
        cost = 10
        gain = 15
        if stats["stamina"] < cost:
            caller.msg(f"你尝试凝神运气，却觉得体力不济。当前体力仅有 |w{stats['stamina']}|n 点，至少需要 |w{cost}|n 点才能修炼。")
            return
        caller.db.stamina = max(0, stats["stamina"] - cost)
        old_realm, new_realm, exp = apply_exp(caller, gain)
        caller.msg(
            "你盘膝而坐，吐纳周天，缓缓引导四周稀薄灵气汇入经脉。\n"
            f"|g本次修炼收获|n: 修为 +{gain}，体力 -{cost}\n"
            f"|g当前状态|n: {new_realm}，修为 {exp}，体力 {caller.db.stamina}/{stats['max_stamina']}"
        )
        if new_realm != old_realm:
            caller.msg(f"|y你心神一振，灵息贯通，境界提升至 {new_realm}。|n")


class CmdRest(Command):
    key = "休息"
    aliases = ["rest", "recover"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        stats = get_stats(caller)
        gain = 15
        if stats["stamina"] >= stats["max_stamina"]:
            caller.msg("你调匀呼吸，发现自己气息平稳，暂时不需要额外休息。")
            return
        caller.db.stamina = min(stats["max_stamina"], stats["stamina"] + gain)
        caller.msg(
            "你找了处安稳地方略作休整，呼吸渐渐平缓，筋骨中的疲意也散去了不少。\n"
            f"|g体力恢复|n: +{caller.db.stamina - stats['stamina']}，当前体力 {caller.db.stamina}/{stats['max_stamina']}"
        )


class CmdRecoverHp(Command):
    key = "调息"
    aliases = ["heal", "recoverhp"]
    locks = "cmd:all()"
    help_category = "修炼"

    def func(self):
        caller = self.caller
        stats = get_stats(caller)
        gain = 20
        if stats["hp"] >= stats["max_hp"]:
            caller.msg("你默运周天，只觉气血充盈，暂时无需额外调息。")
            return
        caller.db.hp = min(stats["max_hp"], stats["hp"] + gain)
        caller.msg(
            "你收摄心神，缓缓调匀体内紊乱气机，胸腹间的闷痛也散去了不少。\n"
            f"|g气血恢复|n: +{caller.db.hp - stats['hp']}，当前气血 {caller.db.hp}/{stats['max_hp']}"
        )
