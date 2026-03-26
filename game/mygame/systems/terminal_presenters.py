"""Terminal-facing text presenters.

These helpers convert structured serializer DTOs into human-readable
terminal text. They deliberately sit outside command handlers so command
modules can stay focused on target lookup and permission checks.
"""


def render_person_detail(detail):
    lines = [
        f"|w{detail['key']}|n",
        f"类型: {detail.get('tag') or '人物'}",
        f"身份: {detail.get('realm_title') or detail.get('title') or '未知'}",
        f"性别: {detail.get('gender_label') or '未知'}",
        f"境界: {detail.get('realm_display') or detail.get('realm') or '未定'}",
    ]
    if detail.get("desc"):
        lines.append(f"描述: {detail['desc']}")
    stats = detail.get("stats") or []
    if stats:
        lines.append("属性:")
        for stat in stats:
            lines.append(f"- {stat['label']}：{stat['value']}")
    actions = detail.get("actions") or []
    if actions:
        lines.append(f"可交互: {' / '.join(actions)}")
    relationship = detail.get("relationship")
    if relationship:
        lines.append("关系摘要:")
        for stat in relationship.get("stats", [])[:3]:
            lines.append(f"- {stat['label']}：{stat['value']}")
    return "\n".join(lines)


def render_npc_relationship_detail(detail):
    lines = [
        f"|w{detail['target']}|n",
        "类型: NPC关系",
    ]
    for stat in detail.get("stats") or []:
        lines.append(f"- {stat['label']}：{stat['value']}")
    return "\n".join(lines)
