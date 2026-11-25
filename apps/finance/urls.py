from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("record/", views.record, name="record"),
    path("expenses/<int:expense_id>/receipt/", views.attach_receipt, name="receipt"),
    path("expenses/<int:expense_id>/decide/", views.decide_expense, name="decide_expense"),
    path("events/<int:event_id>/budget/", views.event_budget, name="event_budget"),
    path("reconciliation/", views.reconciliation, name="reconciliation"),
    path("budget-versions/<int:version_id>/review", views.review_budget, name="review_budget"),
]
