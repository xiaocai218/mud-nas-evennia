"""Area metadata and area-exit helpers."""

from .content_loader import load_content


AREA_DEFINITIONS = load_content("areas")
AREA_EXIT_DEFINITIONS = load_content("area_exits")
ROOM_DEFINITIONS = load_content("rooms").get("rooms", {})


def get_area(area_key):
    return AREA_DEFINITIONS.get(area_key)


def get_area_for_room(room):
    if not room:
        return None
    area_key = getattr(room.db, "area_id", None)
    if area_key and area_key in AREA_DEFINITIONS:
        return AREA_DEFINITIONS[area_key]

    room_content_id = getattr(room.db, "content_id", None)
    for room_key, room_data in ROOM_DEFINITIONS.items():
        if room_data.get("content_id") == room_content_id or room.key == room_data.get("key"):
            area_id = room_data.get("area_id")
            return AREA_DEFINITIONS.get(area_id)
    return None


def get_area_key_for_room(room):
    if not room:
        return None
    area_key = getattr(room.db, "area_id", None)
    if area_key:
        return area_key
    area = get_area_for_room(room)
    if not area:
        return None
    for key, data in AREA_DEFINITIONS.items():
        if data.get("id") == area.get("id"):
            return key
    return None


def get_area_exits_for_area(area_key):
    return [
        {**exit_data, "exit_key": exit_key}
        for exit_key, exit_data in AREA_EXIT_DEFINITIONS.items()
        if exit_data.get("from_area") == area_key
    ]


def format_area_text(room):
    area_key = get_area_key_for_room(room)
    area = get_area_for_room(room)
    if not area_key or not area:
        return "你当前所在地点还没有归属到正式区域。"

    lines = [
        f"|g当前区域|n: {area['key']}",
        f"定位: {area.get('region_type', 'unknown')}",
    ]
    if area.get("recommended_realm"):
        lines.append(f"推荐境界: {area['recommended_realm']}")
    if area.get("desc"):
        lines.append("")
        lines.append(area["desc"])

    facilities = area.get("facilities", [])
    if facilities:
        lines.append("")
        lines.append("基础设施:")
        lines.extend([f"- {entry}" for entry in facilities])

    exits = get_area_exits_for_area(area_key)
    if exits:
        lines.append("")
        lines.append("区域出口:")
        for exit_data in exits:
            target = AREA_DEFINITIONS.get(exit_data["to_area"])
            target_name = target["key"] if target else exit_data["to_area"]
            trigger_room = ROOM_DEFINITIONS.get(exit_data.get("trigger_room"), {}).get("key", exit_data.get("trigger_room", "未知地点"))
            lines.append(f"- 前往 {target_name}：触发地点 {trigger_room}")

    return "\n".join(lines)
