"""统一敌人模型入口。

负责内容：
- 把结构化敌人定义、旧式散字段敌人和运行态 live object 归一到统一 enemy sheet。
- 维护 identity / progression / combat_stats / enemy_meta 等正式字段。
- 把统一敌人模型写回旧系统仍在使用的兼容字段。

不负责内容：
- 不负责实际战斗结算；那部分在 `battle.py` / `battle_effects.py`。
- 不负责刷新策略执行；这里只保存 respawn_policy 等元数据。

主要输入 / 输出：
- 输入：enemy 定义 id、live enemy object、可能存在的旧字段。
- 输出：统一 enemy definition / enemy sheet / runtime enemy object。

上游调用者：
- `battle.py`
- `serializers.py`
- `quests.py`
- 内容铺设和测试刷怪逻辑

排错优先入口：
- `get_enemy_definition`
- `ensure_enemy_model`
- `get_enemy_sheet`
- `_resolve_definition_for_target`
- `_normalize_structured_enemy`
- `_write_compatibility_fields`
"""

import uuid
from copy import deepcopy

from .content_loader import load_content
from .entity_gender import GENDER_UNKNOWN, normalize_gender
from .realms import format_entity_realm_display, normalize_realm_display


MORTAL_ENEMY = "mortal_enemy"
BEAST_ENEMY = "beast_enemy"
CULTIVATOR_ENEMY = "cultivator_enemy"

PRIMARY_STATS = ("physique", "aether", "spirit", "agility", "bone")
DEFAULT_PRIMARY_STATS = {
    "physique": 5,
    "aether": 3,
    "spirit": 3,
    "agility": 4,
    "bone": 4,
}
DEFAULT_COMBAT_STATS = {
    "hp": 30,
    "max_hp": 30,
    "mp": 0,
    "max_mp": 0,
    "stamina": 50,
    "max_stamina": 50,
    "attack_power": 10,
    "spell_power": 0,
    "defense": 5,
    "speed": 10,
    "crit_rate": 0,
    "crit_damage": 150,
    "healing_power": 0,
    "shield_power": 0,
    "control_power": 0,
    "control_resist": 0,
    "threat_modifier": 100,
}
DEFAULT_RESPAWN_POLICY = {"mode": "reset_on_kill"}
DEFAULT_BOSS_MODIFIERS = {
    "damage_reduction_pct": 0,
    "penetration_pct": 0,
    "bonus_max_hp_pct": 0,
    "bonus_defense_pct": 0,
    "control_resist_bonus": 0,
    "phase_shield": 0,
    "pressure_tags": [],
}
ENEMY_DEFINITIONS = load_content("enemies")


def get_enemy_definition(enemy_id):
    raw = ENEMY_DEFINITIONS.get(enemy_id)
    if not raw:
        return None
    return _normalize_enemy_definition(enemy_id, raw)


def is_enemy(target):
    if not target:
        return False
    if getattr(target.db, "combat_target", False):
        return True
    identity = getattr(target.db, "identity", None) or {}
    if identity.get("kind") == "enemy":
        return True
    if any(
        getattr(target.db, attr_name, None) is not None
        for attr_name in ("reward_exp", "damage_taken", "counter_damage", "quest_flag", "drop_item_id")
    ):
        return True
    return bool(getattr(target.db, "enemy_id", None) or getattr(target.db, "template_id", None))


def ensure_enemy_model(target):
    definition = _resolve_definition_for_target(target)
    sheet = _build_enemy_sheet(target, definition)

    target.db.identity = sheet["identity"]
    target.db.progression = sheet["progression"]
    target.db.primary_stats = sheet["primary_stats"]
    target.db.combat_stats = sheet["combat_stats"]
    target.db.affinities = sheet["affinities"]
    target.db.reserves = sheet["reserves"]
    target.db.enemy_meta = sheet["enemy_meta"]

    # 统一模型写回后，再同步旧字段，保证 battle / serializer / 旧命令层看到的是同一份运行态。
    _write_compatibility_fields(target, sheet)
    return {
        "identity": deepcopy(sheet["identity"]),
        "progression": deepcopy(sheet["progression"]),
        "primary_stats": deepcopy(sheet["primary_stats"]),
        "combat_stats": deepcopy(sheet["combat_stats"]),
        "affinities": deepcopy(sheet["affinities"]),
        "reserves": deepcopy(sheet["reserves"]),
        "enemy_meta": deepcopy(sheet["enemy_meta"]),
    }


def get_enemy_sheet(target):
    ensure_enemy_model(target)
    return {
        "identity": deepcopy(getattr(target.db, "identity", {}) or {}),
        "progression": deepcopy(getattr(target.db, "progression", {}) or {}),
        "primary_stats": deepcopy(getattr(target.db, "primary_stats", {}) or {}),
        "combat_stats": deepcopy(getattr(target.db, "combat_stats", {}) or {}),
        "affinities": deepcopy(getattr(target.db, "affinities", {}) or {}),
        "reserves": deepcopy(getattr(target.db, "reserves", {}) or {}),
        "enemy_meta": deepcopy(getattr(target.db, "enemy_meta", {}) or {}),
    }


def get_loot_table(target):
    sheet = get_enemy_sheet(target)
    meta = sheet["enemy_meta"]
    return {
        "loot_table_id": meta.get("loot_table_id"),
        "drop_item_id": meta.get("drop_item_id"),
        "drop_key": meta.get("drop_key"),
        "drop_desc": meta.get("drop_desc"),
    }


def get_enemy_quest_flag(target):
    meta = get_enemy_sheet(target)["enemy_meta"]
    return ((meta.get("quest_hooks") or {}).get("quest_flag")) or getattr(target.db, "quest_flag", None)


def spawn_enemy_instance(enemy_id, location, *, content_id=None, key=None):
    definition = get_enemy_definition(enemy_id)
    if not definition or not location:
        return None

    from evennia.utils.create import create_object

    identity = deepcopy(definition["identity"])
    runtime_content_id = content_id or f"{identity['content_id']}__spawn_{uuid.uuid4().hex[:8]}"
    identity["content_id"] = runtime_content_id
    if key:
        identity["name"] = key

    enemy_obj = create_object("typeclasses.objects.Object", key=identity["name"], location=location)
    enemy_obj.key = identity["name"]
    enemy_obj.location = location
    enemy_obj.db.desc = (
        definition["enemy_meta"].get("presentation", {}).get("desc")
        or definition["enemy_meta"].get("presentation", {}).get("description")
        or ""
    )
    enemy_obj.db.identity = identity
    enemy_obj.db.progression = deepcopy(definition["progression"])
    enemy_obj.db.primary_stats = deepcopy(definition["primary_stats"])
    enemy_obj.db.combat_stats = deepcopy(definition["combat_stats"])
    enemy_obj.db.affinities = deepcopy(definition["affinities"])
    enemy_obj.db.reserves = deepcopy(definition["reserves"])
    enemy_obj.db.enemy_meta = deepcopy(definition["enemy_meta"])
    ensure_enemy_model(enemy_obj)
    return enemy_obj


def _resolve_definition_for_target(target):
    enemy_id = getattr(target.db, "enemy_id", None) or getattr(target.db, "template_id", None)
    runtime_identity = getattr(target.db, "identity", None) or {}
    runtime_combat = getattr(target.db, "combat_stats", None) or {}
    runtime_meta = getattr(target.db, "enemy_meta", None) or {}
    if runtime_identity.get("kind") == "enemy" and runtime_combat:
        # 如果 live object 已经带有结构化 enemy 字段，优先信运行态对象而不是静态模板。
        # 这样战斗中的 hp、动态 spawn content_id、临时改过的 meta 不会被模板回刷覆盖。
        return _normalize_structured_enemy(
            enemy_id or runtime_identity.get("template_id") or runtime_identity.get("content_id") or getattr(target, "key", "enemy"),
            {
                "id": runtime_identity.get("content_id"),
                "identity": runtime_identity,
                "progression": getattr(target.db, "progression", None) or {},
                "primary_stats": getattr(target.db, "primary_stats", None) or {},
                "combat_stats": runtime_combat,
                "affinities": getattr(target.db, "affinities", None) or {},
                "reserves": getattr(target.db, "reserves", None) or {},
                "enemy_meta": runtime_meta,
            },
        )
    if enemy_id:
        definition = get_enemy_definition(enemy_id)
        if definition:
            return definition
    return _normalize_enemy_definition(enemy_id or getattr(target.db, "content_id", None) or getattr(target, "key", "enemy"), None, target=target)


def _normalize_enemy_definition(enemy_id, raw, target=None):
    raw = dict(raw or {})
    if raw.get("identity"):
        return _normalize_structured_enemy(enemy_id, raw)
    # 老 enemy 配置和早期 live object 仍可能只有散字段。
    # 统一先桥接成 structured enemy，再让后续系统只面对一种数据形状。
    return _normalize_legacy_enemy(enemy_id, raw, target=target)


def _normalize_structured_enemy(enemy_id, raw):
    identity = dict(raw.get("identity", {}))
    progression = dict(raw.get("progression", {}))
    primary_stats = dict(raw.get("primary_stats", {}))
    combat_stats = dict(raw.get("combat_stats", {}))
    affinities = dict(raw.get("affinities", {}))
    reserves = dict(raw.get("reserves", {}))
    enemy_meta = dict(raw.get("enemy_meta", {}))

    enemy_type = identity.get("enemy_type") or raw.get("enemy_type") or MORTAL_ENEMY
    identity.setdefault("kind", "enemy")
    identity.setdefault("enemy_type", enemy_type)
    identity.setdefault("name", raw.get("key") or enemy_id)
    identity.setdefault("template_id", enemy_id)
    identity.setdefault("content_id", raw.get("id", enemy_id))
    identity.setdefault("faction", "wild")
    identity["gender"] = normalize_gender(identity.get("gender"), default=GENDER_UNKNOWN)
    identity["is_boss"] = bool(identity.get("is_boss"))
    identity["tags"] = list(identity.get("tags", []))

    progression.setdefault("stage", _default_stage_for_enemy_type(enemy_type))
    progression.setdefault("realm", normalize_realm_display(raw.get("realm") or _default_realm_for_enemy_type(enemy_type)))
    progression.setdefault(
        "realm_info",
        {"display_name": format_entity_realm_display({"realm": progression.get("realm")}, entity_kind="enemy", enemy_type=enemy_type)},
    )
    progression.setdefault("rank_tier", raw.get("rank_tier", "common"))
    progression.setdefault("spawn_profile", {"room_id": raw.get("room_id")})
    progression.setdefault("kill_credit_flags", [])

    normalized_primary = {key: int(primary_stats.get(key, DEFAULT_PRIMARY_STATS[key]) or DEFAULT_PRIMARY_STATS[key]) for key in PRIMARY_STATS}
    normalized_combat = {key: int(combat_stats.get(key, DEFAULT_COMBAT_STATS[key]) or DEFAULT_COMBAT_STATS[key]) for key in DEFAULT_COMBAT_STATS}
    normalized_combat["max_hp"] = max(1, normalized_combat["max_hp"])
    normalized_combat["hp"] = max(0, min(normalized_combat["hp"], normalized_combat["max_hp"]))
    normalized_combat["max_mp"] = max(0, normalized_combat["max_mp"])
    normalized_combat["mp"] = max(0, min(normalized_combat["mp"], normalized_combat["max_mp"]))
    normalized_combat["max_stamina"] = max(0, normalized_combat["max_stamina"])
    normalized_combat["stamina"] = max(0, min(normalized_combat["stamina"], normalized_combat["max_stamina"]))

    affinities.setdefault("element", None)
    affinities["damage_tags"] = list(affinities.get("damage_tags", []))
    affinities["resist_tags"] = list(affinities.get("resist_tags", []))
    affinities["drop_theme"] = list(affinities.get("drop_theme", []))

    reserves.setdefault("resources", {})

    enemy_meta.setdefault("loot_table_id", enemy_meta.get("drop_item_id"))
    enemy_meta.setdefault("respawn_policy", DEFAULT_RESPAWN_POLICY.copy())
    enemy_meta.setdefault("unique_policy", None)
    enemy_meta.setdefault("engage_rules", {})
    enemy_meta.setdefault("ai_profile", {"mode": "passive"})
    enemy_meta.setdefault("quest_hooks", {})
    enemy_meta.setdefault("presentation", {})
    enemy_meta.setdefault("boss_modifiers", DEFAULT_BOSS_MODIFIERS.copy())
    enemy_meta.setdefault("core_type", None)
    enemy_meta.setdefault("battle_ai_profile", {"mode": "basic"})
    enemy_meta.setdefault("battle_card_pool", [])
    enemy_meta.setdefault("decision_rules", [])
    enemy_meta.setdefault("reward_exp", 0)
    enemy_meta.setdefault("damage_taken", 12)
    enemy_meta.setdefault("counter_damage", 6)
    enemy_meta.setdefault("stamina_cost", 8)
    enemy_meta.setdefault("drop_item_id", None)
    enemy_meta.setdefault("drop_key", None)
    enemy_meta.setdefault("drop_desc", None)
    enemy_meta["tags"] = list(enemy_meta.get("tags", []))
    _apply_boss_modifiers(normalized_combat, enemy_meta.get("boss_modifiers", {}))

    return {
        "id": raw.get("id", identity["content_id"]),
        "room_id": raw.get("room_id") or ((progression.get("spawn_profile") or {}).get("room_id")),
        "identity": identity,
        "progression": progression,
        "primary_stats": normalized_primary,
        "combat_stats": normalized_combat,
        "affinities": affinities,
        "reserves": reserves,
        "enemy_meta": enemy_meta,
    }


def _normalize_legacy_enemy(enemy_id, raw, target=None):
    key = raw.get("key") or getattr(target, "key", None) or enemy_id or "enemy"
    content_id = raw.get("id") or getattr(getattr(target, "db", None), "content_id", None) or enemy_id or key
    enemy_type = raw.get("enemy_type") or getattr(getattr(target, "db", None), "enemy_type", None) or _infer_enemy_type(enemy_id, raw, target)
    quest_flag = raw.get("quest_flag") or getattr(getattr(target, "db", None), "quest_flag", None)
    drop_item_id = raw.get("drop_item_id") or getattr(getattr(target, "db", None), "drop_item_id", None)
    drop_key = raw.get("drop_key") or getattr(getattr(target, "db", None), "drop_key", None)
    drop_desc = raw.get("drop_desc") or getattr(getattr(target, "db", None), "drop_desc", None)
    hp = _read_runtime_value(target, "hp", raw.get("hp", raw.get("max_hp", DEFAULT_COMBAT_STATS["hp"])))
    max_hp = _read_runtime_value(target, "max_hp", raw.get("max_hp", hp))

    affinities = {
        "element": raw.get("element"),
        "damage_tags": list(raw.get("damage_tags", [])),
        "resist_tags": list(raw.get("resist_tags", [])),
        "drop_theme": list(raw.get("drop_theme", [])),
    }
    enemy_meta = {
        "loot_table_id": raw.get("loot_table_id") or drop_item_id,
        "respawn_policy": deepcopy(raw.get("respawn_policy") or DEFAULT_RESPAWN_POLICY),
        "unique_policy": raw.get("unique_policy"),
        "engage_rules": deepcopy(raw.get("engage_rules") or {}),
        "ai_profile": deepcopy(raw.get("ai_profile") or {"mode": "passive"}),
        "quest_hooks": {"quest_flag": quest_flag} if quest_flag else {},
        "presentation": deepcopy(raw.get("presentation") or {}),
        "boss_modifiers": deepcopy(raw.get("boss_modifiers") or DEFAULT_BOSS_MODIFIERS),
        "core_type": raw.get("core_type"),
        "reward_exp": int(raw.get("reward_exp", getattr(getattr(target, "db", None), "reward_exp", 0)) or 0),
        "damage_taken": int(raw.get("damage_taken", getattr(getattr(target, "db", None), "damage_taken", 12)) or 12),
        "counter_damage": int(raw.get("counter_damage", getattr(getattr(target, "db", None), "counter_damage", 6)) or 6),
        "stamina_cost": int(raw.get("stamina_cost", getattr(getattr(target, "db", None), "stamina_cost", 8)) or 8),
        "drop_item_id": drop_item_id,
        "drop_key": drop_key,
        "drop_desc": drop_desc,
        "tags": list(raw.get("tags", [])),
    }

    structured = {
        "id": content_id,
        "room_id": raw.get("room_id") or raw.get("room"),
        "identity": {
            "kind": "enemy",
            "name": key,
            "gender": normalize_gender(raw.get("gender") or getattr(getattr(target, "db", None), "gender", None), default=GENDER_UNKNOWN),
            "enemy_type": enemy_type,
            "faction": raw.get("faction", "wild"),
            "is_boss": bool(raw.get("is_boss")),
            "content_id": content_id,
            "template_id": enemy_id or content_id,
            "tags": list(raw.get("tags", [])),
        },
        "progression": {
            "stage": raw.get("stage") or _default_stage_for_enemy_type(enemy_type),
            "realm": normalize_realm_display(raw.get("realm") or _default_realm_for_enemy_type(enemy_type)),
            "rank_tier": raw.get("rank_tier", "common"),
            "spawn_profile": {"room_id": raw.get("room_id") or raw.get("room")},
            "kill_credit_flags": [quest_flag] if quest_flag else [],
        },
        "primary_stats": deepcopy(raw.get("primary_stats") or DEFAULT_PRIMARY_STATS),
        "combat_stats": {
            **deepcopy(DEFAULT_COMBAT_STATS),
            "hp": int(hp or DEFAULT_COMBAT_STATS["hp"]),
            "max_hp": int(max_hp or DEFAULT_COMBAT_STATS["max_hp"]),
        },
        "affinities": affinities,
        "reserves": deepcopy(raw.get("reserves") or {"resources": {}}),
        "enemy_meta": enemy_meta,
    }
    if enemy_type == BEAST_ENEMY and not structured["affinities"]["element"]:
        structured["affinities"]["element"] = raw.get("element") or "wood"
    return _normalize_structured_enemy(enemy_id or content_id, structured)


def _build_enemy_sheet(target, definition):
    definition = deepcopy(definition)
    combat_stats = definition["combat_stats"]
    has_structured_runtime = bool((getattr(target.db, "identity", None) or {}).get("kind") == "enemy" and getattr(target.db, "combat_stats", None))
    runtime_hp = getattr(target.db, "hp", None)
    runtime_max_hp = getattr(target.db, "max_hp", None)
    # 对 structured runtime enemy，优先保留 combat_stats 自己维护的上限；
    # 对 legacy enemy，则继续兼容读取旧的 hp/max_hp 散字段。
    if runtime_max_hp is not None and not has_structured_runtime:
        combat_stats["max_hp"] = int(runtime_max_hp)
    if runtime_hp is not None:
        combat_stats["hp"] = max(0, min(int(runtime_hp), combat_stats["max_hp"]))
    else:
        combat_stats["hp"] = max(0, min(int(combat_stats["hp"]), combat_stats["max_hp"]))
    return definition


def _write_compatibility_fields(target, sheet):
    identity = sheet["identity"]
    progression = sheet["progression"]
    combat_stats = sheet["combat_stats"]
    meta = sheet["enemy_meta"]

    target.db.combat_target = True
    target.db.enemy_id = identity.get("template_id")
    target.db.template_id = identity.get("template_id")
    target.db.content_id = identity.get("content_id")
    target.db.enemy_type = identity.get("enemy_type")
    target.db.faction = identity.get("faction")
    target.db.gender = identity.get("gender")
    target.db.is_boss = identity.get("is_boss")
    target.db.tags = list(identity.get("tags", []))
    target.db.realm = progression.get("realm")
    target.db.hp = combat_stats.get("hp")
    target.db.max_hp = combat_stats.get("max_hp")
    target.db.reward_exp = meta.get("reward_exp")
    target.db.counter_damage = meta.get("counter_damage")
    target.db.damage_taken = meta.get("damage_taken")
    target.db.stamina_cost = meta.get("stamina_cost")
    target.db.drop_item_id = meta.get("drop_item_id")
    target.db.drop_key = meta.get("drop_key")
    target.db.drop_desc = meta.get("drop_desc")
    target.db.quest_flag = (meta.get("quest_hooks") or {}).get("quest_flag")


def _apply_boss_modifiers(combat_stats, modifiers):
    modifiers = modifiers or {}
    bonus_max_hp_pct = int(modifiers.get("bonus_max_hp_pct", 0) or 0)
    bonus_defense_pct = int(modifiers.get("bonus_defense_pct", 0) or 0)
    control_resist_bonus = int(modifiers.get("control_resist_bonus", 0) or 0)
    if bonus_max_hp_pct:
        combat_stats["max_hp"] = max(1, int(combat_stats["max_hp"] * (100 + bonus_max_hp_pct) / 100))
        combat_stats["hp"] = combat_stats["max_hp"]
    if bonus_defense_pct:
        combat_stats["defense"] = max(0, int(combat_stats["defense"] * (100 + bonus_defense_pct) / 100))
    if control_resist_bonus:
        combat_stats["control_resist"] = max(0, combat_stats["control_resist"] + control_resist_bonus)


def _default_stage_for_enemy_type(enemy_type):
    if enemy_type == CULTIVATOR_ENEMY:
        return "cultivator"
    return "mortal"


def _default_realm_for_enemy_type(enemy_type):
    if enemy_type == BEAST_ENEMY:
        return "妖兽"
    if enemy_type == CULTIVATOR_ENEMY:
        return "炼气1阶"
    return "凡人"


def _infer_enemy_type(enemy_id, raw, target):
    enemy_id = (enemy_id or raw.get("id") or getattr(target, "key", "") or "").lower()
    key = str(raw.get("key") or getattr(target, "key", "")).lower()
    if "ape" in enemy_id or "beast" in enemy_id or "妖" in key or "魈" in key or "兽" in key:
        return BEAST_ENEMY
    if "修士" in key or "弟子" in key or "cultivator" in enemy_id:
        return CULTIVATOR_ENEMY
    return MORTAL_ENEMY


def _read_runtime_value(target, attr_name, fallback):
    value = getattr(getattr(target, "db", None), attr_name, None)
    return fallback if value is None else value
