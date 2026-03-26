"""HTTP endpoints for the H5 client skeleton."""

from django.urls import path

from . import views


app_name = "h5_api"

urlpatterns = [
    path("", views.protocol_overview_view, name="protocol-overview"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("account/characters/", views.character_list_view, name="character-list"),
    path("account/characters/select/", views.character_select_view, name="character-select"),
    path("bootstrap/", views.bootstrap_view, name="bootstrap"),
    path("battle-status/", views.battle_status_view, name="battle-status"),
    path("chat-status/", views.chat_status_view, name="chat-status"),
    path("ui/preferences/", views.ui_preferences_view, name="ui-preferences"),
    path("quests/", views.quest_log_view, name="quest-log"),
    path("shops/<str:shop_id>/", views.shop_detail_view, name="shop-detail"),
    path("markets/<str:market_id>/", views.market_detail_view, name="market-detail"),
    path("action/", views.action_view, name="action"),
    path("ws-meta/", views.ws_meta_view, name="ws-meta"),
    path("events/poll/", views.event_poll_view, name="event-poll"),
]
