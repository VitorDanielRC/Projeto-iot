from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Elevador

def home(request):
    ultimo = Elevador.objects.order_by("-criado_em").first()
    return render(request, "index.html", {"ultimo": ultimo})


@csrf_exempt
def chamar_elevador(request, andar):
    if andar not in [1, 2, 3]:
        return JsonResponse({"erro": "Andar inválido"}, status=400)

    comando = Elevador.objects.create(andar_destino=andar)

    return JsonResponse({
        "status": "ok",
        "mensagem": f"Elevador chamado para o andar {andar}",
        "andar": comando.andar_destino
    })


def comando_arduino(request):
    comando = Elevador.objects.filter(executado=False).order_by("criado_em").first()

    if comando:
        comando.executado = True
        comando.save()

        return JsonResponse({
            "tem_comando": True,
            "andar": comando.andar_destino
        })

    return JsonResponse({
        "tem_comando": False,
        "andar": None
    })