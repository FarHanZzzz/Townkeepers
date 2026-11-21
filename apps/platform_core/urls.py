from django.urls import path

from . import views

app_name = "platform_core"

urlpatterns = [
    path("health/live", views.health_live, name="health_live"),
    path("health/ready", views.health_ready, name="health_ready"),
    path("files/<uuid:key>/", views.file_download, name="file"),
    path("exports/<int:pk>/", views.export_download, name="export"),
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/open", views.notification_open, name="notification_open"),
    path("deliveries/", views.deliveries, name="deliveries"),
    path("deliveries/<int:pk>/retry", views.delivery_retry, name="delivery_retry"),
    path("settings/policy/", views.policy_settings, name="policy"),
]
