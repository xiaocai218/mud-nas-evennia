"""Project web URL configuration."""

from django.urls import include, path

from evennia.web.urls import urlpatterns as evennia_default_urlpatterns


urlpatterns = [
    path("api/h5/", include("web.api.urls")),
]

urlpatterns += evennia_default_urlpatterns
