# -*- coding: utf-8 -*-
"""
Connection screen

Localized connection screen for the current MUD prototype.
"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
|g==============================================================|n
 欢迎来到 |w{}|n  |cver {}|n

 这是一个正在搭建中的中文群玩 MUD 原型服。

 已有账号请输入：
      |wconnect <账号> <密码>|n

 还没有账号请输入：
      |wcreate <账号> <密码>|n

 常用帮助：
      |whelp|n  查看帮助
      |wlook|n  重新显示本欢迎页

 小提示：
 - 账号名如果有空格，请用英文引号包住
 - 登录后可先输入 |wlook|n、|whelp|n、|wchannels|n 试试
 - 这是首版骨架，世界与玩法会继续逐步补全
|g==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
