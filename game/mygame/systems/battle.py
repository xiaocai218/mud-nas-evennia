"""ATB battle system for turn-based combat."""

from __future__ import annotations

import time
import uuid

from .battle_ai import choose_card as choose_ai_card
from .battle_cards import build_card_payload
from .battle_effects import apply_damage, apply_guard_effect, apply_heal_effect, apply_shield_effect, spend_card_costs
from .battle_results import build_basic_attack_result, build_item_result, build_round_report, build_spell_damage_result, snapshot_battle_state
from .chat import notify_player
from .enemy_model import get_enemy_sheet, is_enemy
from .event_bus import (
    combat_action_resolved,
    combat_finished,
    combat_started,
    combat_turn_ready,
    combat_updated,
    enqueue_account_event,
)
from .items import find_item, get_inventory_items, use_item
from .player_battle_cards import get_player_battle_card_pool
from .player_stats import apply_exp, get_stats
from .quests import mark_combat_kill
from .teams import get_team_member_characters, get_same_area_team_members


ATB_THRESHOLD = 100
ACTION_TIMEOUT_SECONDS = 30
MIN_FAILURE_HP = 1
MIN_FAILURE_STAMINA = 5

_BATTLE_REGISTRY = {}


def reset_battle_registry():
    _BATTLE_REGISTRY.clear()


def is_character_in_battle(caller):
    battle_id = getattr(getattr(caller, "db", None), "battle_id", None)
    battle = _BATTLE_REGISTRY.get(battle_id)
    if not battle or battle.get("status") == "finished":
        if battle_id:
            caller.db.battle_id = None
        return False
    return True


def get_battle_snapshot(caller_or_battle_id):
    battle = _resolve_battle(caller_or_battle_id)
    if not battle:
        return None
    _settle_battle_until_player_input(battle)
    return _serialize_battle(battle)


def get_battle_log(caller_or_battle_id, limit=10):
    battle = _resolve_battle(caller_or_battle_id)
    if not battle:
        return []
    return list((battle.get("log") or [])[-max(0, int(limit)):])


def clear_battle(caller_or_battle_id, *, reset_players=False, reset_enemies=False):
    battle = _resolve_battle(caller_or_battle_id)
    if not battle:
        return None

    battle["status"] = "finished"
    battle["result"] = "cancelled"
    battle["action_deadline_ts"] = None
    battle["_result_resolved"] = True

    for combatant in battle["participants"]:
        ref = combatant["entity_ref"]
        if combatant["entity_type"] == "player" and reset_players:
            stats = get_stats(ref)
            ref.db.hp = stats["max_hp"]
            ref.db.mp = stats["max_mp"]
            ref.db.stamina = stats["max_stamina"]
        if combatant["entity_type"] == "enemy" and reset_enemies:
            ref.db.hp = combatant["max_hp"]
            ref.db.max_hp = combatant["max_hp"]
            if getattr(ref.db, "combat_stats", None):
                ref.db.combat_stats = {**ref.db.combat_stats, "hp": combatant["max_hp"], "max_hp": combatant["max_hp"]}
        if getattr(getattr(ref, "db", None), "battle_id", None) == battle["battle_id"]:
            ref.db.battle_id = None

    _BATTLE_REGISTRY.pop(battle["battle_id"], None)
    return _serialize_battle(battle)


def list_available_cards(caller):
    battle = _get_battle_for_character(caller)
    if not battle:
        return []
    _settle_battle_until_player_input(battle)
    actor = _get_current_actor(battle)
    if not actor or actor["entity_ref"] != caller:
        return []
    return _build_available_cards(battle, actor)


def list_available_targets(caller):
    battle = _get_battle_for_character(caller)
    if not battle:
        return []
    _settle_battle_until_player_input(battle)
    actor = _get_current_actor(battle)
    if not actor or actor["entity_ref"] != caller:
        return []
    return _serialize_targets_for_actor(battle, actor)


def start_battle(caller, targets, team_mode=False):
    if is_character_in_battle(caller):
        battle = _get_battle_for_character(caller)
        _settle_battle_until_player_input(battle)
        return {"ok": True, "result": "already_in_battle", "battle": _serialize_battle(battle)}

    enemies = [target for target in list(targets or []) if is_enemy(target)]
    if not enemies:
        return {"ok": False, "reason": "target_not_attackable"}

    allies = [caller]
    if team_mode:
        allies.extend(_get_same_room_teammates(caller))

    battle = {
        "battle_id": f"battle_{uuid.uuid4().hex[:10]}",
        "status": "active",
        "room_id": getattr(getattr(getattr(caller, "location", None), "db", None), "room_id", None),
        "started_at": time.time(),
        "participants": [],
        "teams": {"player": [], "enemy": []},
        "turn_state": {"current_actor_id": None, "turn_count": 0},
        "timeline_state": {"threshold": ATB_THRESHOLD},
        "action_deadline_ts": None,
        "result": None,
        "log": [],
        "round_reports": [],
    }
    for ally in allies:
        combatant = _create_player_combatant(ally)
        battle["participants"].append(combatant)
        battle["teams"]["player"].append(combatant["combatant_id"])
        ally.db.battle_id = battle["battle_id"]
    for enemy in enemies:
        combatant = _create_enemy_combatant(enemy)
        battle["participants"].append(combatant)
        battle["teams"]["enemy"].append(combatant["combatant_id"])
        enemy.db.battle_id = battle["battle_id"]

    _BATTLE_REGISTRY[battle["battle_id"]] = battle
    _settle_battle_until_player_input(battle)
    _emit_battle_event(battle, combat_started(_serialize_battle(battle)))
    return {"ok": True, "result": "battle_started", "battle": _serialize_battle(battle)}


def submit_action(caller, card_id, target_id=None, item_id=None):
    battle = _get_battle_for_character(caller)
    if not battle:
        return {"ok": False, "reason": "battle_not_found"}
    _settle_battle_until_player_input(battle)
    if battle["status"] == "finished":
        return {"ok": True, "result": "battle_finished", "battle": _serialize_battle(battle)}

    actor = _get_current_actor(battle)
    if not actor or actor["entity_ref"] != caller:
        return {"ok": False, "reason": "not_your_turn"}

    result = _resolve_action(battle, actor, card_id, target_id=target_id, item_id=item_id)
    _check_battle_finished(battle)
    if battle["status"] != "finished":
        _advance_battle_to_next_actor(battle)
        _settle_battle_until_player_input(battle)
        _emit_battle_event(battle, combat_updated(_serialize_battle(battle)))
    else:
        _resolve_battle_result(battle)
    return {"ok": True, "result": result, "battle": _serialize_battle(battle)}


def advance_battle(battle_id):
    battle = _resolve_battle(battle_id)
    if not battle:
        return None
    _settle_battle_until_player_input(battle)
    return _serialize_battle(battle)


def resolve_battle_result(battle_id):
    battle = _resolve_battle(battle_id)
    if not battle:
        return None
    _check_battle_finished(battle)
    if battle["status"] == "finished":
        _resolve_battle_result(battle)
    return _serialize_battle(battle)


def attack_or_start_battle(caller, target):
    battle = _get_battle_for_character(caller)
    if battle:
        return submit_action(caller, "basic_attack", target_id=_combatant_id_for_entity(battle, target))
    return start_battle(caller, [target], team_mode=True)


def _create_player_combatant(caller):
    stats = get_stats(caller)
    combat = dict(stats["combat_stats"])
    card_pool = get_player_battle_card_pool(caller)
    return {
        "combatant_id": _entity_ref_id(caller),
        "name": caller.key,
        "side": "player",
        "entity_type": "player",
        "entity_ref": caller,
        "alive": stats["hp"] > 0,
        "hp": combat["hp"],
        "mp": combat["mp"],
        "stamina": combat["stamina"],
        "max_hp": combat["max_hp"],
        "max_mp": combat["max_mp"],
        "max_stamina": combat["max_stamina"],
        "combat_stats_snapshot": combat,
        "effects": [],
        "cooldowns": {},
        "timeline_progress": 0,
        "shield": 0,
        "available_cards": [],
        "battle_card_pool": card_pool,
    }


def _create_enemy_combatant(enemy):
    _prepare_enemy_for_battle(enemy)
    sheet = get_enemy_sheet(enemy)
    combat = dict(sheet["combat_stats"])
    meta = dict(sheet["enemy_meta"])
    identity = dict(sheet["identity"])
    return {
        "combatant_id": _entity_ref_id(enemy),
        "name": identity["name"],
        "side": "enemy",
        "entity_type": "enemy",
        "entity_ref": enemy,
        "alive": combat["hp"] > 0,
        "hp": combat["hp"],
        "mp": combat["mp"],
        "stamina": combat["stamina"],
        "max_hp": combat["max_hp"],
        "max_mp": combat["max_mp"],
        "max_stamina": combat["max_stamina"],
        "combat_stats_snapshot": combat,
        "effects": [],
        "cooldowns": {},
        "timeline_progress": 0,
        "shield": 0,
        "available_cards": [],
        "battle_ai_profile": meta.get("battle_ai_profile") or {"mode": "basic"},
        "battle_card_pool": meta.get("battle_card_pool") or [],
        "decision_rules": meta.get("decision_rules") or [],
    }


def _resolve_battle(value):
    if isinstance(value, str):
        return _BATTLE_REGISTRY.get(value)
    battle_id = getattr(getattr(value, "db", None), "battle_id", None)
    return _BATTLE_REGISTRY.get(battle_id)


def _get_battle_for_character(caller):
    return _resolve_battle(caller)


def _get_same_room_teammates(caller):
    teammates = get_team_member_characters(caller, include_self=False)
    return [member for member in teammates if getattr(member, "location", None) == getattr(caller, "location", None)]


def _settle_battle_until_player_input(battle):
    while battle["status"] == "active":
        actor = _get_current_actor(battle)
        if not actor:
            _advance_battle_to_next_actor(battle)
            actor = _get_current_actor(battle)
            if not actor:
                break
        if actor["entity_type"] == "player":
            deadline = battle.get("action_deadline_ts")
            if deadline and time.time() >= deadline:
                _resolve_action(battle, actor, "basic_attack", target_id=None, item_id=None, auto=True)
                _check_battle_finished(battle)
                if battle["status"] == "finished":
                    _resolve_battle_result(battle)
                    break
                _advance_battle_to_next_actor(battle)
                continue
            break
        actor["available_cards"] = _build_available_cards(battle, actor)
        selected = choose_ai_card(battle, actor)
        _resolve_action(battle, actor, selected["card_id"], target_id=selected.get("target_id"), auto=True)
        _check_battle_finished(battle)
        if battle["status"] == "finished":
            _resolve_battle_result(battle)
            break
        _advance_battle_to_next_actor(battle)


def _advance_battle_to_next_actor(battle):
    alive = [combatant for combatant in battle["participants"] if combatant["alive"]]
    if not alive:
        return
    while True:
        for combatant in alive:
            combatant["timeline_progress"] += max(1, int(combatant["combat_stats_snapshot"].get("speed", 10) or 1))
        ready = [combatant for combatant in alive if combatant["timeline_progress"] >= ATB_THRESHOLD]
        if not ready:
            continue
        actor = max(ready, key=lambda entry: (entry["timeline_progress"], entry["combat_stats_snapshot"].get("speed", 0)))
        actor["timeline_progress"] = 0
        _decrement_cooldowns(actor)
        actor["available_cards"] = _build_available_cards(battle, actor)
        battle["turn_state"]["current_actor_id"] = actor["combatant_id"]
        battle["turn_state"]["turn_count"] += 1
        battle["action_deadline_ts"] = time.time() + ACTION_TIMEOUT_SECONDS if actor["entity_type"] == "player" else None
        _emit_battle_event(
            battle,
            combat_turn_ready(
                {
                    "battle_id": battle["battle_id"],
                    "current_actor_id": actor["combatant_id"],
                    "current_actor_name": actor["name"],
                    "deadline_ts": battle["action_deadline_ts"],
                }
            ),
        )
        return


def _resolve_action(battle, actor, card_id, target_id=None, item_id=None, auto=False):
    before_snapshot = snapshot_battle_state(battle)
    actor["available_cards"] = _build_available_cards(battle, actor)
    cards = {card["card_id"]: card for card in actor["available_cards"]}
    card = cards.get(card_id)
    if not card:
        if card_id == "basic_attack":
            card = build_card_payload("basic_attack")
        else:
            return {"ok": False, "reason": "card_unavailable"}

    if card["card_type"] == "use_combat_item":
        result = _resolve_item_action(battle, actor, item_id)
    else:
        result = _resolve_card_action(battle, actor, card, target_id)

    _write_back_combatant_state(actor)
    _sync_battle_targets(battle)
    battle["log"].append(result["log"])
    after_snapshot = snapshot_battle_state(battle)
    battle["round_reports"].append(build_round_report(battle, actor, result["log"], before_snapshot, after_snapshot, auto=auto))
    battle["action_deadline_ts"] = None
    _emit_battle_event(battle, combat_action_resolved({"battle_id": battle["battle_id"], "entry": result["log"], "auto": auto}))
    return result


def _resolve_basic_attack(battle, actor, target_id=None):
    target = _resolve_target_for_actor(battle, actor, target_id)
    damage = max(1, int(actor["combat_stats_snapshot"].get("attack_power", 10) - target["combat_stats_snapshot"].get("defense", 0) / 2))
    applied = apply_damage(target, damage, attack_type="basic_attack")
    if actor["entity_type"] == "player":
        actor["stamina"] = max(0, actor["stamina"] - 3)
    return build_basic_attack_result(actor, target, damage, applied)


def _resolve_guard_action(battle, actor, card=None):
    return apply_guard_effect(actor, card=card)


def _resolve_shield_action(battle, actor, card=None):
    return apply_shield_effect(actor, card=card)


def _resolve_spell_damage_card(battle, actor, target_id=None, card=None):
    target = _resolve_target_for_actor(battle, actor, target_id)
    params = dict((card or {}).get("effect_params") or {})
    spend_card_costs(actor, card)
    damage = max(
        int(params.get("min_damage", 4) or 4),
        int(params.get("base_damage", 8) or 8)
        + int(actor["combat_stats_snapshot"].get("attack_power", 8) * float(params.get("attack_ratio", 0.5) or 0))
        + int(actor["combat_stats_snapshot"].get("spell_power", 0) * float(params.get("spell_ratio", 1.0) or 0)),
    )
    applied = apply_damage(target, damage)
    return build_spell_damage_result(actor, target, card, damage, applied)


def _resolve_recover_instinct(battle, actor, card=None):
    return apply_heal_effect(actor, card=card, default_cooldown=3)


def _resolve_item_action(battle, actor, item_id):
    caller = actor["entity_ref"]
    before = get_stats(caller)
    item = find_item(caller, item_id=item_id) if item_id else None
    if not item:
        item = _find_first_combat_item(caller)
    if not item:
        return build_item_result(actor, heal=0, text=None)
    result = use_item(caller, item)
    after = get_stats(caller)
    actor["hp"] = after["hp"]
    actor["mp"] = after["mp"]
    actor["stamina"] = after["stamina"]
    heal = max(0, after["hp"] - before["hp"])
    return build_item_result(actor, item=item, heal=heal, text=result.get("text"))


def _resolve_target_for_actor(battle, actor, target_id=None):
    opponents = [entry for entry in battle["participants"] if entry["alive"] and entry["side"] != actor["side"]]
    if not opponents:
        return actor
    if target_id:
        for target in opponents:
            if target["combatant_id"] == target_id:
                return target
    return opponents[0]


def _build_available_cards(battle, actor):
    cards = []
    for card_id in actor.get("battle_card_pool") or []:
        card = build_card_payload(card_id)
        if not card:
            continue
        if not _card_is_available(actor, card):
            continue
        cards.append(card)
    return cards


def _decrement_cooldowns(actor):
    actor["cooldowns"] = {
        key: max(0, int(value) - 1)
        for key, value in (actor.get("cooldowns") or {}).items()
        if int(value) - 1 > 0
    }


def _apply_damage(target, damage, attack_type=None):
    return apply_damage(target, damage, attack_type=attack_type)


def _sync_battle_targets(battle):
    for combatant in battle["participants"]:
        _write_back_combatant_state(combatant)


def _write_back_combatant_state(combatant):
    ref = combatant["entity_ref"]
    if combatant["entity_type"] == "player":
        ref.db.hp = combatant["hp"]
        ref.db.mp = combatant["mp"]
        ref.db.stamina = combatant["stamina"]
    else:
        ref.db.hp = combatant["hp"]
        ref.db.max_hp = combatant["max_hp"]
        ref.db.combat_stats = {**(getattr(ref.db, "combat_stats", {}) or {}), "hp": combatant["hp"], "max_hp": combatant["max_hp"]}
    ref.db.battle_id = ref.db.battle_id if combatant["alive"] else ref.db.battle_id


def _check_battle_finished(battle):
    player_alive = any(entry["alive"] for entry in battle["participants"] if entry["side"] == "player")
    enemy_alive = any(entry["alive"] for entry in battle["participants"] if entry["side"] == "enemy")
    if player_alive and enemy_alive:
        return False
    battle["status"] = "finished"
    battle["result"] = "victory" if player_alive else "defeat"
    battle["turn_state"]["current_actor_id"] = None
    battle["action_deadline_ts"] = None
    return True


def _resolve_battle_result(battle):
    if battle.get("_result_resolved"):
        return
    battle["_result_resolved"] = True
    if battle["result"] == "victory":
        _grant_victory_rewards(battle)
    else:
        _handle_defeat(battle)
    for combatant in battle["participants"]:
        ref = combatant["entity_ref"]
        if getattr(getattr(ref, "db", None), "battle_id", None) == battle["battle_id"]:
            ref.db.battle_id = None
    _emit_battle_event(battle, combat_finished(_serialize_battle(battle)))


def _grant_victory_rewards(battle):
    enemies = [entry for entry in battle["participants"] if entry["side"] == "enemy"]
    players = [entry for entry in battle["participants"] if entry["side"] == "player"]
    for enemy in enemies:
        killer = players[0] if players else None
        if not killer:
            continue
        caller = killer["entity_ref"]
        target = enemy["entity_ref"]
        reward_exp = int(getattr(target.db, "reward_exp", 0) or 0)
        old_realm, new_realm, exp = apply_exp(caller, reward_exp)
        mark_combat_kill(caller, target)
        drop = None
        drop_item_id = getattr(target.db, "drop_item_id", None)
        if drop_item_id:
            from .items import create_loot, get_item_definition_by_id, resolve_item_key

            drop_key = getattr(target.db, "drop_key", None) or resolve_item_key(item_id=drop_item_id)
            drop_desc = getattr(target.db, "drop_desc", None) or (get_item_definition_by_id(drop_item_id) or {}).get("desc")
            if drop_key:
                drop = create_loot(caller, key=drop_key, item_id=drop_item_id, desc=drop_desc)
        target.db.hp = getattr(target.db, "max_hp", enemy["max_hp"])
        if getattr(target.db, "combat_stats", None):
            target.db.combat_stats = {**target.db.combat_stats, "hp": target.db.hp}
        if reward_exp > 0:
            message = f"你在战斗中击败 {target.key}，获得修为 +{reward_exp}。"
        else:
            message = f"你在战斗中击败 {target.key}。"
        if drop:
            message += f" 掉落：{drop.key}。"
        if reward_exp > 0 and new_realm != old_realm:
            message += f" 境界提升至 {new_realm}。"
        notify_player(caller, message, code="combat_reward")


def _handle_defeat(battle):
    for combatant in [entry for entry in battle["participants"] if entry["side"] == "player"]:
        caller = combatant["entity_ref"]
        caller.db.hp = max(MIN_FAILURE_HP, int(caller.db.max_hp or combatant["max_hp"]))
        caller.db.stamina = max(MIN_FAILURE_STAMINA, min(int(caller.db.max_stamina or combatant["max_stamina"]), MIN_FAILURE_STAMINA))
        if hasattr(caller, "search"):
            home = caller.search("青云渡", global_search=True, quiet=True)
            if home:
                destination = home[0] if isinstance(home, list) else home
                if destination:
                    caller.move_to(destination, quiet=True)
        notify_player(caller, "你在战斗中落败，被送回青云渡调息。", code="combat_defeat")


def _serialize_battle(battle):
    current_actor = None if battle["status"] == "finished" else _get_current_actor(battle)
    available_cards = current_actor["available_cards"] if current_actor else []
    available_targets = _serialize_targets_for_actor(battle, current_actor) if current_actor else []
    return {
        "battle_id": battle["battle_id"],
        "status": battle["status"],
        "room_id": battle["room_id"],
        "turn_count": battle["turn_state"]["turn_count"],
        "current_actor_id": current_actor["combatant_id"] if current_actor else None,
        "current_actor_name": current_actor["name"] if current_actor else None,
        "action_deadline_ts": None if battle["status"] == "finished" else battle["action_deadline_ts"],
        "result": battle["result"],
        "participants": [_serialize_combatant(entry) for entry in battle["participants"]],
        "log": list(battle["log"][-10:]),
        "round_reports": list(battle.get("round_reports") or [])[-3:],
        "available_cards": available_cards,
        "available_targets": available_targets,
    }


def _serialize_combatant(combatant):
    return {
        "combatant_id": combatant["combatant_id"],
        "name": combatant["name"],
        "side": combatant["side"],
        "entity_type": combatant["entity_type"],
        "alive": combatant["alive"],
        "hp": combatant["hp"],
        "max_hp": combatant["max_hp"],
        "mp": combatant["mp"],
        "max_mp": combatant["max_mp"],
        "stamina": combatant["stamina"],
        "max_stamina": combatant["max_stamina"],
        "shield": combatant.get("shield", 0),
        "timeline_progress": combatant["timeline_progress"],
        "cooldowns": dict(combatant.get("cooldowns") or {}),
        "effects": list(combatant.get("effects") or []),
        "available_cards": list(combatant.get("available_cards") or []),
    }


def _serialize_targets_for_actor(battle, actor):
    return [
        {
            "combatant_id": target["combatant_id"],
            "name": target["name"],
            "side": target["side"],
            "alive": target["alive"],
            "hp": target["hp"],
            "max_hp": target["max_hp"],
        }
        for target in battle["participants"]
        if target["alive"] and (target["side"] != actor["side"] or actor["entity_type"] == "player")
    ]


def _get_current_actor(battle):
    actor_id = battle["turn_state"].get("current_actor_id")
    for combatant in battle["participants"]:
        if combatant["combatant_id"] == actor_id:
            return combatant
    return None


def _combatant_id_for_entity(battle, entity):
    for combatant in battle["participants"]:
        if combatant["entity_ref"] == entity:
            return combatant["combatant_id"]
    return None


def _entity_ref_id(entity):
    entity_id = getattr(entity, "id", None) or getattr(entity, "pk", None)
    if entity_id is not None:
        return f"obj_{entity_id}"
    return f"mem_{id(entity)}"


def _find_first_combat_item(caller):
    if not hasattr(caller, "contents_get"):
        return None
    for item in get_inventory_items(caller):
        if getattr(getattr(item, "db", None), "item_id", None):
            return item
    return None


def _emit_battle_event(battle, event):
    for combatant in battle["participants"]:
        ref = combatant["entity_ref"]
        account = getattr(ref, "account", None) or getattr(ref, "db", None) and getattr(ref.db, "account", None)
        if account:
            enqueue_account_event(account, event)


def _card_is_available(actor, card):
    if not card:
        return False
    card_id = card["card_id"]
    if actor["cooldowns"].get(card_id, 0) > 0:
        return False
    costs = card.get("costs") or {}
    if int(costs.get("mp", 0) or 0) > actor.get("mp", 0):
        return False
    if card["card_type"] == "use_combat_item" and actor["entity_type"] == "player" and not _find_first_combat_item(actor["entity_ref"]):
        return False
    return True


def _resolve_card_action(battle, actor, card, target_id=None):
    card_id = card["card_id"]
    if card_id == "basic_attack":
        return _resolve_basic_attack(battle, actor, target_id)
    if card_id == "guard":
        return _resolve_guard_action(battle, actor, card=card)
    if any(effect.get("type") == "heal" for effect in card.get("effects", [])):
        return _resolve_recover_instinct(battle, actor, card=card)
    if any(effect.get("type") == "shield" for effect in card.get("effects", [])):
        return _resolve_shield_action(battle, actor, card=card)
    if any(effect.get("type") in {"spell_damage", "damage"} for effect in card.get("effects", [])):
        return _resolve_spell_damage_card(battle, actor, target_id, card=card) if card["card_type"] == "skill_card" else _resolve_basic_attack(battle, actor, target_id)
    return _resolve_basic_attack(battle, actor, target_id)


def _prepare_enemy_for_battle(enemy):
    sheet = get_enemy_sheet(enemy)
    identity = sheet.get("identity", {})
    meta = sheet.get("enemy_meta", {})
    tags = set(identity.get("tags", []) or []) | set(meta.get("tags", []) or [])
    if "test_enemy" not in tags:
        return
    max_hp = int(sheet["combat_stats"]["max_hp"])
    enemy.db.hp = max_hp
    enemy.db.max_hp = max_hp
    if getattr(enemy.db, "combat_stats", None):
        enemy.db.combat_stats = {**enemy.db.combat_stats, "hp": max_hp, "max_hp": max_hp}

