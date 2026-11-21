from django.urls import include, path

from apps.accounts import views as account_views

urlpatterns = [
    path("", account_views.dashboard, name="dashboard"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.platform_core.urls")),
    path("clubs/", include("apps.clubs.urls")),
    path("events/", include("apps.events.urls")),
    path("finance/", include("apps.finance.urls")),
    path("memos/", include("apps.memos.urls")),
    path("", include("apps.analytics.urls")),
]
