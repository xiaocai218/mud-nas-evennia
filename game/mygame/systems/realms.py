"""Realm and cultivation progression helpers."""

import re
from copy import deepcopy

from .content_loader import load_content


AWAKENED_REALM = "启灵"
MORTAL_REALM = "凡人"
BEAST_REALM = "妖兽"
FORMAL_REALM_STAGE_PLACEHOLDER = "小阶待开放"

REALM_DATA = load_content("realms")
DEFAULT_REALM = REALM_DATA["default_realm"]
DEFAULT_REALM_KEY = REALM_DATA.get("default_realm_key", "qi_refining")
MORTAL_REALM_DATA = REALM_DATA.get("mortal_realm", {"realm_key": "mortal", "realm_name": MORTAL_REALM, "display_name": MORTAL_REALM})
STAGE_BUCKETS = list(REALM_DATA.get("stage_buckets", []))
REALM_DEFINITIONS = dict(REALM_DATA.get("realms", {}))
REALM_NAME_INDEX = {definition.get("realm_name"): key for key, definition in REALM_DEFINITIONS.items()}
NON_FORMAL_REALM_NAMES = {MORTAL_REALM, AWAKENED_REALM, BEAST_REALM}
BREAKTHROUGH_REQUIREMENT_LABELS = {
    "quest": "任务",
    "pill": "丹药",
    "trial": "考验",
    "item": "物品",
    "manual": "手动突破",
}


def get_default_realm():
    return DEFAULT_REALM


def get_default_realm_key():
    return DEFAULT_REALM_KEY


def get_realm_definition(realm_key):
    definition = REALM_DEFINITIONS.get(realm_key)
    return deepcopy(definition) if definition else None


def get_realm_definition_by_name(realm_name):
    realm_name = normalize_realm_display(realm_name)
    if realm_name in (None, "", MORTAL_REALM, AWAKENED_REALM, BEAST_REALM):
        return None
    if "妖阶" in realm_name:
        realm_name = realm_name.replace("妖阶", "")
    if realm_name.endswith("层"):
        realm_name = realm_name[:-1] + "阶"
    if "阶" in realm_name:
        base_name = realm_name.split("阶", 1)[0]
    else:
        base_name = realm_name
    return get_realm_definition(REALM_NAME_INDEX.get(base_name))


def get_realm_stage_bucket(minor_stage):
    if minor_stage is None:
        return None
    for bucket in STAGE_BUCKETS:
        if bucket["min_stage"] <= minor_stage <= bucket["max_stage"]:
            return deepcopy(bucket)
    return None


def normalize_realm_display(realm_name):
    if realm_name in (None, ""):
        return None
    realm_name = str(realm_name).strip()
    mapping = {
        "炼气一层": "炼气1阶",
        "炼气二层": "炼气2阶",
        "炼气三层": "炼气3阶",
        "炼气四层": "炼气4阶",
        "炼气五层": "炼气5阶",
        "炼气六层": "炼气6阶",
        "炼气七层": "炼气7阶",
        "炼气八层": "炼气8阶",
        "炼气九层": "炼气9阶",
        "炼气十层": "炼气10阶",
    }
    return mapping.get(realm_name, realm_name)


def get_realm_from_exp(exp):
    progression = resolve_realm_progression(exp)
    return progression["display_name"]


def resolve_realm_progression(exp, *, current_realm=None, realm_key=None):
    exp = int(exp or 0)
    current_realm = normalize_realm_display(current_realm)
    if current_realm == AWAKENED_REALM:
        return build_awakened_progression(exp)
    if current_realm == MORTAL_REALM:
        return build_mortal_progression(exp)

    realm_key = realm_key or _infer_realm_key(current_realm) or DEFAULT_REALM_KEY
    realm_definition = get_realm_definition(realm_key)
    if not realm_definition or not realm_definition.get("minor_stages"):
        realm_name = (realm_definition or {}).get("realm_name") or current_realm or DEFAULT_REALM
        return {
            "realm": realm_name,
            "realm_key": realm_key,
            "realm_name": realm_name,
            "minor_stage": None,
            "stage_bucket": None,
            "display_name": realm_name,
            "is_peak": False,
            "can_breakthrough": False,
            "breakthrough_state": "unavailable",
            "cultivation_exp": exp,
            "cultivation_exp_total": exp,
            "cultivation_exp_in_stage": 0,
            "cultivation_exp_required": 0,
            "next_realm_key": None,
            "next_minor_stage": None,
            "realm_band": realm_definition.get("realm_band") if realm_definition else None,
        }

    stages = sorted(realm_definition["minor_stages"], key=lambda item: item["stage"])
    current_stage = stages[0]
    for stage in stages:
        if exp >= int(stage.get("exp_threshold", 0) or 0):
            current_stage = stage

    threshold = int(current_stage.get("exp_threshold", 0) or 0)
    next_stage = next((stage for stage in stages if stage["stage"] == current_stage["stage"] + 1), None)
    breakthrough = dict(realm_definition.get("breakthrough") or {})
    if next_stage:
        next_threshold = int(next_stage.get("exp_threshold", threshold) or threshold)
        cultivation_exp_required = max(0, next_threshold - threshold)
        next_realm_key = realm_key
        next_minor_stage = next_stage["stage"]
        can_breakthrough = False
        breakthrough_state = "progressing"
    else:
        next_threshold = int(breakthrough.get("exp_threshold", threshold) or threshold)
        cultivation_exp_required = max(0, next_threshold - threshold)
        next_realm_key = breakthrough.get("target_realm_key")
        next_minor_stage = 1 if next_realm_key else None
        can_breakthrough = exp >= next_threshold and next_realm_key is not None
        breakthrough_state = "available" if can_breakthrough else "locked"

    bucket = get_realm_stage_bucket(current_stage["stage"])
    return {
        "realm": current_stage["display_name"],
        "realm_key": realm_key,
        "realm_name": realm_definition["realm_name"],
        "minor_stage": current_stage["stage"],
        "stage_bucket": bucket["label"] if bucket else None,
        "display_name": current_stage["display_name"],
        "is_peak": current_stage["stage"] == int(realm_definition.get("max_minor_stage", 10) or 10),
        "can_breakthrough": can_breakthrough,
        "breakthrough_state": breakthrough_state,
        "cultivation_exp": exp,
        "cultivation_exp_total": exp,
        "cultivation_exp_in_stage": max(0, exp - threshold),
        "cultivation_exp_required": cultivation_exp_required,
        "next_realm_key": next_realm_key,
        "next_minor_stage": next_minor_stage,
        "realm_band": realm_definition.get("realm_band"),
    }


def build_mortal_progression(exp=0):
    exp = int(exp or 0)
    return {
        "realm": MORTAL_REALM,
        "realm_key": MORTAL_REALM_DATA.get("realm_key", "mortal"),
        "realm_name": MORTAL_REALM_DATA.get("realm_name", MORTAL_REALM),
        "minor_stage": None,
        "stage_bucket": None,
        "display_name": MORTAL_REALM_DATA.get("display_name", MORTAL_REALM),
        "is_peak": False,
        "can_breakthrough": False,
        "breakthrough_state": "unavailable",
        "cultivation_exp": exp,
        "cultivation_exp_total": exp,
        "cultivation_exp_in_stage": 0,
        "cultivation_exp_required": 0,
        "next_realm_key": DEFAULT_REALM_KEY,
        "next_minor_stage": 1,
        "realm_band": None,
    }


def build_awakened_progression(exp=0):
    exp = int(exp or 0)
    return {
        "realm": AWAKENED_REALM,
        "realm_key": None,
        "realm_name": AWAKENED_REALM,
        "minor_stage": None,
        "stage_bucket": None,
        "display_name": AWAKENED_REALM,
        "is_peak": False,
        "can_breakthrough": False,
        "breakthrough_state": "quest_pending",
        "cultivation_exp": exp,
        "cultivation_exp_total": exp,
        "cultivation_exp_in_stage": 0,
        "cultivation_exp_required": 0,
        "next_realm_key": DEFAULT_REALM_KEY,
        "next_minor_stage": 1,
        "realm_band": None,
    }


def get_realm_attribute_growth(realm_key):
    definition = get_realm_definition(realm_key)
    return dict((definition or {}).get("attribute_growth") or {})


def normalize_breakthrough_requirement(requirement, *, index=0):
    raw = dict(requirement or {})
    requirement_type = str(raw.get("type") or "custom").strip() or "custom"
    requirement_id = str(raw.get("id") or f"{requirement_type}_{index + 1}").strip()
    label = str(raw.get("label") or BREAKTHROUGH_REQUIREMENT_LABELS.get(requirement_type) or requirement_type).strip()
    description = str(raw.get("description") or label).strip()
    return {
        "id": requirement_id,
        "type": requirement_type,
        "label": label,
        "description": description,
        "optional": bool(raw.get("optional", False)),
        "status": str(raw.get("status") or "ready").strip(),
        "metadata": dict(raw.get("metadata") or {}),
    }


def get_breakthrough_requirements(realm_key):
    definition = get_realm_definition(realm_key) or {}
    breakthrough = dict(definition.get("breakthrough") or {})
    requirements = breakthrough.get("requirements") or []
    return [normalize_breakthrough_requirement(entry, index=index) for index, entry in enumerate(requirements)]


def format_breakthrough_requirements(requirements):
    formatted = []
    for requirement in requirements or []:
        normalized = normalize_breakthrough_requirement(requirement)
        prefix = "可选" if normalized["optional"] else "需要"
        formatted.append(f"{prefix}{normalized['label']}：{normalized['description']}")
    return formatted


def evaluate_breakthrough_requirements(entity, target_realm_key):
    requirements = get_breakthrough_requirements(target_realm_key)
    missing_requirements = [item for item in requirements if item["status"] not in {"ready", "completed"} and not item["optional"]]
    return {
        "ok": True,
        "target_realm_key": target_realm_key,
        "requirements": requirements,
        "missing_requirements": missing_requirements,
        "can_breakthrough": not missing_requirements,
    }


def can_breakthrough_realm(exp, realm_key):
    progression = resolve_realm_progression(exp, realm_key=realm_key)
    return progression["can_breakthrough"]


def describe_recommended_realm(recommended):
    if not recommended:
        return None
    if isinstance(recommended, str):
        return {
            "mode": "legacy",
            "label": normalize_realm_display(recommended),
            "start": {"display_name": normalize_realm_display(recommended)},
            "end": {"display_name": normalize_realm_display(recommended)},
        }
    payload = deepcopy(recommended)
    payload.setdefault("mode", "point")
    payload.setdefault("label", "")
    payload.setdefault("start", {})
    payload.setdefault("end", payload["start"])
    return payload


def get_recommended_realm_label(recommended):
    payload = describe_recommended_realm(recommended)
    return payload.get("label") if payload else None


def get_recommended_realm_target(recommended):
    payload = describe_recommended_realm(recommended)
    if not payload:
        return None
    end = payload.get("end") or {}
    return end.get("display_name") or payload.get("label")


def format_realm_title(display_name, suffix=None):
    display_name = normalize_realm_display(display_name) or MORTAL_REALM
    suffix = str(suffix or "").strip()
    if not suffix:
        return display_name
    return f"{display_name}·{suffix}"


def format_entity_realm_display(progression, *, entity_kind="player", enemy_type=None):
    display_name = normalize_realm_display((progression or {}).get("display_name") or (progression or {}).get("realm") or MORTAL_REALM)
    if entity_kind == "enemy" and enemy_type and display_name not in NON_FORMAL_REALM_NAMES and "阶" in display_name:
        return re.sub(r"(\d+)阶$", r"妖阶\1阶", display_name)
    if entity_kind == "enemy" and display_name == BEAST_REALM:
        return BEAST_REALM
    return display_name


def build_entity_realm_payload(progression, *, entity_kind="player", suffix=None, enemy_type=None, include_realm_info=False):
    progression = dict(progression or {})
    realm = normalize_realm_display(progression.get("realm") or progression.get("display_name")) or MORTAL_REALM
    realm_display = format_entity_realm_display(progression, entity_kind=entity_kind, enemy_type=enemy_type)
    payload = {
        "realm": realm,
        "realm_display": realm_display,
        "realm_title": format_realm_title(realm_display, suffix),
        "stage_bucket": None if get_stage_bucket_display(progression) == "无" else get_stage_bucket_display(progression),
    }
    if include_realm_info:
        payload["realm_info"] = progression
    return payload


def get_stage_bucket_label(minor_stage):
    bucket = get_realm_stage_bucket(minor_stage)
    return bucket["label"] if bucket else None


def is_formal_realm_without_minor_stage(progression):
    progression = dict(progression or {})
    display_name = progression.get("display_name") or progression.get("realm") or MORTAL_REALM
    return bool(progression.get("realm_key")) and progression.get("minor_stage") is None and display_name not in NON_FORMAL_REALM_NAMES


def get_stage_bucket_display(progression, *, default="无"):
    progression = dict(progression or {})
    if progression.get("stage_bucket"):
        return progression["stage_bucket"]
    if is_formal_realm_without_minor_stage(progression):
        return FORMAL_REALM_STAGE_PLACEHOLDER
    return default


def get_progression_hint(progression):
    progression = dict(progression or {})
    display_name = progression.get("display_name") or progression.get("realm") or MORTAL_REALM
    if is_formal_realm_without_minor_stage(progression):
        return f"{display_name} 已达成，后续小阶内容暂未开放"
    if progression.get("can_breakthrough"):
        target_realm_key = progression.get("next_realm_key")
        target_definition = get_realm_definition(target_realm_key) if target_realm_key else None
        target_name = (target_definition or {}).get("realm_name") or "下一境界"
        return f"已达巅峰，可突破至 {target_name}"
    if progression.get("minor_stage") is not None:
        remaining = max(
            0,
            int(progression.get("cultivation_exp_required", 0) or 0) - int(progression.get("cultivation_exp_in_stage", 0) or 0),
        )
        next_minor_stage = progression.get("next_minor_stage")
        if progression.get("next_realm_key") == progression.get("realm_key") and next_minor_stage:
            return f"距离 {display_name} 下一阶还差 {remaining} 修为"
        if progression.get("next_realm_key"):
            target_definition = get_realm_definition(progression["next_realm_key"]) or {}
            target_name = target_definition.get("realm_name") or "下一境界"
            return f"距离突破 {target_name} 还差 {remaining} 修为"
    return f"当前境界：{display_name}"


def get_progression_status_rows(progression):
    progression = dict(progression or {})
    rows = []
    if progression.get("minor_stage") is not None:
        rows.extend(
            [
                ("当前阶修为", f"{progression.get('cultivation_exp_in_stage', 0)}/{progression.get('cultivation_exp_required', 0)}"),
                ("突破状态", "可突破" if progression.get("can_breakthrough") else "未满足"),
                ("下一步", get_progression_hint(progression)),
            ]
        )
    elif is_formal_realm_without_minor_stage(progression):
        rows.append(("下一步", get_progression_hint(progression)))
    return rows


def get_cultivation_progress_messages(progression):
    progression = dict(progression or {})
    display_name = progression.get("display_name") or progression.get("realm") or MORTAL_REALM
    messages = []
    if progression.get("minor_stage") is not None:
        messages.append(
            f"|g当前小阶|n: {display_name} ({get_stage_bucket_display(progression, default='无阶段')})，"
            f"本阶修为 {progression.get('cultivation_exp_in_stage', 0)}/{progression.get('cultivation_exp_required', 0)}"
        )
        messages.append(f"|g下一步|n: {get_progression_hint(progression)}")
    elif is_formal_realm_without_minor_stage(progression):
        messages.append(f"|g当前境界|n: {display_name}（小阶暂未开放）")
        messages.append(f"|g下一步|n: {get_progression_hint(progression)}")
    if progression.get("can_breakthrough"):
        messages.append("|y你已抵达当前境界巅峰，可尝试使用 `突破` 冲击下一境界。|n")
    return messages


def _infer_realm_key(current_realm):
    current_realm = normalize_realm_display(current_realm)
    if not current_realm or current_realm in (MORTAL_REALM, AWAKENED_REALM, BEAST_REALM):
        return None
    if current_realm.endswith("阶"):
        current_realm = current_realm.split("阶", 1)[0]
    if "妖阶" in current_realm:
        current_realm = current_realm.replace("妖阶", "")
    return REALM_NAME_INDEX.get(current_realm)
