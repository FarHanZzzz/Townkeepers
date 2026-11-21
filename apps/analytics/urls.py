from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("reports/", views.terms, name="terms"),
    path("reports/import/", views.import_history, name="import_history"),
]
