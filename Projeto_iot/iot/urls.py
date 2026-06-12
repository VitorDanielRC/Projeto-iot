from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("painel/", views.painel, name="painel"),
    path("logout/", views.logout_view, name="logout"),

    path("entrega/status-atual/", views.status_painel, name="status_painel"),
    path("entrega/criar/", views.criar_entrega, name="criar_entrega"),
    path("entrega/voltar-baixo/", views.voltar_para_baixo_site, name="voltar_para_baixo_site"),
    path("entrega/finalizar/", views.finalizar_entrega_site, name="finalizar_entrega_site"),

    path("api/elevador/comando/", views.comando_elevador, name="comando_elevador"),
    path("api/elevador/status/", views.status_elevador, name="status_elevador"),
    path("api/elevador/voltar-baixo/", views.voltar_para_baixo_api, name="voltar_para_baixo_api"),
    path("api/elevador/finalizar/", views.finalizar_entrega_api, name="finalizar_entrega_api"),
    path("api/elevador/status/<int:entrega_id>/<str:novo_status>/", views.atualizar_status, name="atualizar_status"),
]
