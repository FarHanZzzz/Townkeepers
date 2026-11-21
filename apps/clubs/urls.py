from django.urls import path

from . import views

app_name = "clubs"

urlpatterns = [
    path("", views.club_list, name="list"),
    path("new/", views.club_register, name="register"),
    path("archive/", views.archive, name="archive"),
    path("archive/<str:object_type>/<int:object_pk>/correct/", views.correction, name="correct"),
    path("<int:pk>/", views.club_detail, name="detail"),
    path("<int:pk>/handover/", views.club_handover, name="handover"),
    path("<int:pk>/identity/", views.club_edit_identity, name="edit_identity"),
    path("<int:pk>/archive", views.club_archive, name="archive_club"),
    path("<int:pk>/profile/", views.club_internal_profile, name="internal_profile"),
    path("<int:pk>/terms/new/", views.term_new, name="term_new"),
    path("<int:pk>/advisors/new/", views.advisor_new, name="advisor_new"),
    path("terms/<int:term_pk>/activate", views.term_activate, name="term_activate"),
    path("terms/<int:term_pk>/close", views.term_close, name="term_close"),
    path("terms/<int:term_pk>/appoint/", views.appoint, name="appoint"),
    path("assignments/<int:assignment_pk>/end/", views.assignment_end, name="assignment_end"),
]
