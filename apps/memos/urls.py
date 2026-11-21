from django.urls import path

from . import views

app_name = "memos"

urlpatterns = [
    path("", views.memo_list, name="list"),
    path("queue/<int:memo_id>/override/", views.queue_override, name="queue_override"),
    path("new/", views.memo_new, name="new"),
    path("templates/", views.template_list, name="templates"),
    path("templates/new/", views.template_new, name="template_new"),
    path("templates/<int:pk>/", views.template_detail, name="template_detail"),
    path("templates/<int:pk>/<str:action>", views.template_active, name="template_active"),
    path("<int:pk>/", views.memo_detail, name="detail"),
    path("<int:pk>/edit/", views.memo_edit, name="edit"),
    path("<int:pk>/attachments", views.memo_attach, name="attach"),
    path("<int:pk>/send", views.memo_send, name="send"),
    path("<int:pk>/review/", views.memo_review, name="review"),
    path("<int:pk>/decisions", views.memo_decisions, name="decisions"),
    path("<int:pk>/revise", views.memo_revise, name="revise"),
    path("<int:pk>/withdraw", views.memo_withdraw, name="withdraw"),
    path("<int:pk>/amend", views.memo_amend, name="amend"),
    path("<int:pk>/deadline", views.memo_deadline, name="deadline"),
    path("<int:pk>/preview/", views.memo_preview, name="preview"),
    path("<int:pk>/export", views.memo_export, name="export"),
]
