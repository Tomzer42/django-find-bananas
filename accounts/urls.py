from django.contrib.auth import views as auth_views
from django.urls import path

from . import google, views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("google/", google.start, name="google_login"),
    path("google/callback/", google.callback, name="google_callback"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("username/", views.choose_username, name="choose_username"),
    path("delete/", views.delete_account, name="delete_account"),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
