from django.db import models


class Entrega(models.Model):
    STATUS_CHOICES = [
        ("aguardando", "Aguardando envio"),
        ("subindo", "Subindo para o andar"),
        ("aguardando_retirada", "Aguardando retirada"),
        ("retornando", "Retornando ao térreo"),
        ("finalizado", "Finalizado"),
    ]

    ANDARES = [
        (1, "1º Andar - Recepção"),
        (2, "2º Andar - Apartamento 201"),
        (3, "3º Andar - Apartamento 301"),
    ]

    nome_morador = models.CharField(max_length=100)
    numero_pedido = models.CharField(max_length=50)
    andar_destino = models.IntegerField(choices=ANDARES)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="aguardando"
    )
    executado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.nome_morador} - Andar {self.andar_destino}"