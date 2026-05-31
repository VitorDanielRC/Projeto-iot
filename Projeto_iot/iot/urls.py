from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("entrega/criar/", views.criar_entrega, name="criar_entrega"),

    path("api/elevador/comando/", views.comando_arduino, name="comando_arduino"),
    path("api/elevador/status/", views.status_atual, name="status_atual"),
    path("api/elevador/voltar-baixo/", views.voltar_para_baixo, name="voltar_para_baixo"),
    path("api/elevador/finalizar/", views.finalizar_entrega, name="finalizar_entrega"),

    path(
        "api/elevador/status/<int:entrega_id>/<str:status>/",
        views.atualizar_status,
        name="atualizar_status"
    ),
]