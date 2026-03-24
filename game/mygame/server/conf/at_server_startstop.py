from evennia.game_template.server.conf.at_server_startstop import *

from systems.chat import cleanup_managed_channel_nicks, ensure_all_channels


def at_server_start():
    ensure_all_channels()
    cleanup_managed_channel_nicks()
