# simulator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("simulate/", views.simulate_access, name="simulate_access"),
]
