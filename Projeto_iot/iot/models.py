from django.db import models

class Elevador(models.Model):
    ANDARES = [
        (1, "1º Andar"),
        (2, "2º Andar"),
        (3, "3º Andar"),
    ]

    andar_destino = models.IntegerField(choices=ANDARES)
    andar_atual = models.IntegerField(default=1)
    executado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Elevador para o andar {self.andar_destino}"