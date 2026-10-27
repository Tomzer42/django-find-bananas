from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("privacy/", views.privacy, name="privacy"),
    path("api/editions/<int:number>/start", views.api_start, name="api-start"),
    path("api/editions/<int:number>/state", views.api_state, name="api-state"),
    path("api/editions/<int:number>/rounds/<int:index>/image", views.api_round_image, name="api-round-image"),
    path("api/editions/<int:number>/rounds/<int:index>/answer", views.api_answer, name="api-answer"),
]
