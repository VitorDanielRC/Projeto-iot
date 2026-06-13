from django.contrib import admin

from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("numero_pedido", "nome_morador", "criado_por", "andar_destino", "status", "executado", "criado_em")
    list_filter = ("status", "andar_destino", "executado", "criado_por")
    search_fields = ("numero_pedido", "nome_morador", "criado_por__username")
    ordering = ("-criado_em",)
