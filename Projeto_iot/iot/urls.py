from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/elevador/chamar/<int:andar>/", views.chamar_elevador, name="chamar_elevador"),
    path("api/elevador/comando/", views.comando_arduino, name="comando_arduino"),
]