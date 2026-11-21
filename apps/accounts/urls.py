from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("auth/sign-in/", views.sign_in, name="sign_in"),
    path("auth/sign-out/", views.sign_out, name="sign_out"),
    path("dev/login/", views.dev_login, name="dev_login"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/requests/<str:field>/", views.profile_change, name="profile_change"),
    path("accounts/", views.directory, name="directory"),
    path("accounts/new/", views.provision, name="provision"),
    path("accounts/<int:pk>/", views.profile_detail, name="profile_detail"),
    path("accounts/<int:pk>/grants", views.profile_grants, name="profile_grants"),
    path("accounts/<int:pk>/<str:action>", views.profile_activation, name="profile_activation"),
    path("accounts/<int:pk>/invitation/retry", views.resend_invitation, name="resend_invitation"),
    path("accounts/profile-requests/", views.profile_requests, name="profile_requests"),
    path(
        "accounts/profile-requests/<int:pk>/", views.profile_request_detail, name="profile_request"
    ),
]
