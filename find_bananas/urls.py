from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='bananas-home'),
    path('about/', views.about, name='bananas-about'),
]
