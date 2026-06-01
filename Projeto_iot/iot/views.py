from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Entrega


def home(request):
    ultima_entrega = Entrega.objects.order_by("-criado_em").first()
    historico = Entrega.objects.order_by("-criado_em")[:6]

    return render(request, "index.html", {
        "ultima_entrega": ultima_entrega,
        "historico": historico
    })


@csrf_exempt
def criar_entrega(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    entrega_em_andamento = Entrega.objects.filter(
        status__in=[
            "aguardando",
            "subindo",
            "aguardando_retirada",
            "retornando"
        ]
    ).first()

    if entrega_em_andamento:
        return JsonResponse({
            "status": "bloqueado",
            "mensagem": "O elevador já possui uma comida em andamento. Finalize ou retire a entrega atual antes de enviar outra.",
            "pedido_atual": entrega_em_andamento.numero_pedido,
            "morador_atual": entrega_em_andamento.nome_morador,
            "andar_atual": entrega_em_andamento.andar_destino,
            "status_atual": entrega_em_andamento.status
        }, status=409)

    nome_morador = request.POST.get("nome_morador")
    numero_pedido = request.POST.get("numero_pedido")
    andar_destino = request.POST.get("andar_destino")

    if not nome_morador or not numero_pedido or not andar_destino:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Preencha todos os campos."
        }, status=400)

    try:
        andar_destino = int(andar_destino)
    except ValueError:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Andar inválido."
        }, status=400)

    if andar_destino not in [1, 2, 3]:
        return JsonResponse({
            "status": "erro",
            "mensagem": "O andar precisa ser 1, 2 ou 3."
        }, status=400)

    entrega = Entrega.objects.create(
        nome_morador=nome_morador,
        numero_pedido=numero_pedido,
        andar_destino=andar_destino,
        status="aguardando"
    )

    return JsonResponse({
        "status": "ok",
        "mensagem": "Entrega registrada com sucesso.",
        "id": entrega.id,
        "nome_morador": entrega.nome_morador,
        "numero_pedido": entrega.numero_pedido,
        "andar_destino": entrega.andar_destino,
        "status_entrega": entrega.status
    })

def comando_arduino(request):
    entrega = Entrega.objects.filter(executado=False).order_by("criado_em").first()

    if entrega:
        entrega.executado = True
        entrega.status = "subindo"
        entrega.save()

        return JsonResponse({
            "tem_comando": True,
            "id": entrega.id,
            "tipo": "ENTREGA",
            "andar_destino": entrega.andar_destino,
            "numero_pedido": entrega.numero_pedido,
            "nome_morador": entrega.nome_morador
        })

    return JsonResponse({
        "tem_comando": False,
        "mensagem": "Nenhuma entrega pendente."
    })


@csrf_exempt
def atualizar_status(request, entrega_id, status):
    status_validos = [
        "aguardando",
        "subindo",
        "aguardando_retirada",
        "retornando",
        "finalizado"
    ]

    if status not in status_validos:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Status inválido."
        }, status=400)

    try:
        entrega = Entrega.objects.get(id=entrega_id)
    except Entrega.DoesNotExist:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Entrega não encontrada."
        }, status=404)

    entrega.status = status
    entrega.save()

    return JsonResponse({
        "status": "ok",
        "mensagem": "Status atualizado com sucesso.",
        "entrega_id": entrega.id,
        "novo_status": entrega.status
    })


def status_atual(request):
    entrega = Entrega.objects.order_by("-criado_em").first()

    if not entrega:
        return JsonResponse({
            "tem_entrega": False,
            "mensagem": "Nenhuma entrega registrada."
        })

    return JsonResponse({
        "tem_entrega": True,
        "id": entrega.id,
        "nome_morador": entrega.nome_morador,
        "numero_pedido": entrega.numero_pedido,
        "andar_destino": entrega.andar_destino,
        "status_entrega": entrega.status,
        "executado": entrega.executado,
        "criado_em": entrega.criado_em.strftime("%d/%m/%Y %H:%M:%S")
    })


@csrf_exempt
def retornar_terreo(request):
    entrega = Entrega.objects.order_by("-criado_em").first()

    if entrega:
        entrega.status = "retornando"
        entrega.save()

    return JsonResponse({
        "status": "ok",
        "mensagem": "Elevador retornando para o térreo.",
        "andar_destino": 1
    })

@csrf_exempt
def finalizar_entrega(request):
    entrega = Entrega.objects.exclude(status="finalizado").order_by("-criado_em").first()

    if not entrega:
        return JsonResponse({
            "status": "erro",
            "mensagem": "Não existe entrega em andamento."
        }, status=404)

    entrega.status = "finalizado"
    entrega.save()

    return JsonResponse({
        "status": "ok",
        "mensagem": "Entrega finalizada. O elevador está liberado para uma nova comida.",
        "entrega_id": entrega.id
    })
    
@csrf_exempt
def voltar_para_baixo(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    entrega = Entrega.objects.exclude(status="finalizado").order_by("-criado_em").first()

    if entrega:
        entrega.andar_destino = 1
        entrega.status = "retornando"
        entrega.executado = False
        entrega.save()

        return JsonResponse({
            "status": "ok",
            "mensagem": "Comando enviado: elevador descendo para o 1º andar.",
            "andar_destino": 1,
            "entrega_id": entrega.id
        })

    entrega = Entrega.objects.create(
        nome_morador="Sistema",
        numero_pedido="RETORNO",
        andar_destino=1,
        status="retornando",
        executado=False
    )

    return JsonResponse({
        "status": "ok",
        "mensagem": "Comando enviado: elevador descendo para o 1º andar.",
        "andar_destino": 1,
        "entrega_id": entrega.id
    })