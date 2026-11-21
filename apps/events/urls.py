from django.urls import path

from . import desk, views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("new/", views.event_new, name="new"),
    path("<int:pk>/", views.event_detail, name="detail"),
    path("<int:pk>/edit/", views.event_edit, name="edit"),
    path("venues/", views.venue_list, name="venues"),
    path("venues/restrict/", desk.venue_restrict, name="venue_restrict"),
    path("availability/", desk.availability_search, name="availability"),
    path("calendar/", desk.calendar, name="calendar"),
    path("suggestions/", desk.slot_suggestions, name="suggestions"),
    path("<int:pk>/book/", views.booking_new, name="book"),
    path("bookings/<int:booking_id>/decide/", views.booking_decide, name="booking_decide"),
    path("bookings/<int:booking_id>/move/", desk.booking_move, name="booking_move"),
    path("<int:pk>/publish/", desk.event_publish, name="publish"),
    path("<int:pk>/preview/", desk.event_preview, name="preview"),
    path("<int:pk>/complete/", desk.event_complete, name="complete"),
    path("<int:pk>/outcome/", desk.event_outcome, name="outcome"),
]
