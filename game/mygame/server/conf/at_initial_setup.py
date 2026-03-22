"""
Initial world customization.

This runs only once on the first successful server startup.
"""

from evennia import search_object


START_ROOM_KEY = "青云渡"
START_ROOM_DESC = (
    "晨雾沿着石阶缓缓流下，古渡口边立着一块半旧的青碑，上书'青云渡'三字。\\n"
    "这里是初入九州的修行者暂歇之地，向前可问道，向后可回望凡尘。\\n"
    "你隐约听见远处钟声回荡，像是在提醒你，一段新的旅程已经开始。"
)


def at_initial_setup():
    room = search_object("#2")
    if not room:
        return

    room = room[0]
    room.key = START_ROOM_KEY
    room.db.desc = START_ROOM_DESC
    room.save()
