from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("painel/", views.painel, name="painel"),
    path("logout/", views.logout_view, name="logout"),

    path("entrega/criar/", views.criar_entrega, name="criar_entrega"),

    path("api/elevador/comando/", views.comando_elevador, name="comando_elevador"),
    path("api/elevador/status/", views.status_elevador, name="status_elevador"),
    path("api/elevador/voltar-baixo/", views.voltar_para_baixo, name="voltar_para_baixo"),
    path("api/elevador/finalizar/", views.finalizar_entrega, name="finalizar_entrega"),
    path("api/elevador/status/<int:entrega_id>/<str:novo_status>/", views.atualizar_status, name="atualizar_status"),
]