"""HTTP endpoints for the H5 client skeleton."""

from django.urls import path

from . import views


app_name = "h5_api"

urlpatterns = [
    path("", views.protocol_overview_view, name="protocol-overview"),
    path("bootstrap/", views.bootstrap_view, name="bootstrap"),
    path("quests/", views.quest_log_view, name="quest-log"),
    path("shops/<str:shop_id>/", views.shop_detail_view, name="shop-detail"),
    path("action/", views.action_view, name="action"),
    path("ws-meta/", views.ws_meta_view, name="ws-meta"),
]
