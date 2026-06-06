from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .forms import CadastroForm
from .models import Entrega


def login_view(request):
    if request.user.is_authenticated:
        return redirect("painel")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        usuario = authenticate(request, username=username, password=password)

        if usuario is not None:
            login(request, usuario)
            return redirect("painel")
        else:
            messages.error(request, "Usuário ou senha inválidos.")

    return render(request, "login.html")


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect("painel")

    if request.method == "POST":
        form = CadastroForm(request.POST)

        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect("painel")
        else:
            messages.error(request, "Verifique os dados do cadastro.")
    else:
        form = CadastroForm()

    return render(request, "cadastro.html", {"form": form})


@login_required
def painel(request):
    entrega_atual = Entrega.objects.order_by("-criado_em").first()
    historico = Entrega.objects.order_by("-criado_em")[:6]

    return render(request, "painel.html", {
        "entrega_atual": entrega_atual,
        "historico": historico,
    })


def logout_view(request):
    logout(request)
    return redirect("login")


@csrf_exempt
@login_required
def criar_entrega(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    nome_morador = request.POST.get("nome_morador")
    numero_pedido = request.POST.get("numero_pedido")
    andar_destino = request.POST.get("andar_destino")

    if not nome_morador or not numero_pedido or not andar_destino:
        return JsonResponse({"erro": "Preencha todos os campos."}, status=400)

    entrega_em_andamento = Entrega.objects.filter(
        status__in=["aguardando", "subindo", "aguardando_retirada", "retornando"]
    ).exists()

    if entrega_em_andamento:
        return JsonResponse({
            "erro": "Já existe uma entrega em andamento."
        }, status=409)

    entrega = Entrega.objects.create(
        nome_morador=nome_morador,
        numero_pedido=numero_pedido,
        andar_destino=andar_destino,
        status="aguardando",
        executado=False
    )

    return JsonResponse({
        "mensagem": "Entrega criada com sucesso.",
        "id": entrega.id,
        "nome_morador": entrega.nome_morador,
        "numero_pedido": entrega.numero_pedido,
        "andar_destino": entrega.andar_destino,
        "status": entrega.status,
    })


def comando_elevador(request):
    entrega = Entrega.objects.filter(
        executado=False,
        status="aguardando"
    ).order_by("criado_em").first()

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
            "nome_morador": entrega.nome_morador,
        })

    return JsonResponse({
        "tem_comando": False,
        "mensagem": "Nenhum comando pendente."
    })


def status_elevador(request):
    entrega = Entrega.objects.order_by("-criado_em").first()

    if not entrega:
        return JsonResponse({
            "tem_entrega": False,
            "mensagem": "Nenhuma entrega encontrada."
        })

    return JsonResponse({
        "tem_entrega": True,
        "id": entrega.id,
        "nome_morador": entrega.nome_morador,
        "numero_pedido": entrega.numero_pedido,
        "andar_destino": entrega.andar_destino,
        "status": entrega.status,
        "executado": entrega.executado,
    })


@csrf_exempt
def voltar_para_baixo(request):
    entrega = Entrega.objects.filter(
        status__in=["subindo", "aguardando_retirada"]
    ).order_by("-criado_em").first()

    if not entrega:
        return JsonResponse({
            "erro": "Nenhuma entrega para retornar."
        }, status=404)

    entrega.status = "retornando"
    entrega.save()

    return JsonResponse({
        "mensagem": "Elevador retornando para o térreo.",
        "id": entrega.id,
        "status": entrega.status,
    })


@csrf_exempt
def finalizar_entrega(request):
    entrega = Entrega.objects.filter(
        status__in=["aguardando", "subindo", "aguardando_retirada", "retornando"]
    ).order_by("-criado_em").first()

    if not entrega:
        return JsonResponse({
            "erro": "Nenhuma entrega em andamento."
        }, status=404)

    entrega.status = "finalizado"
    entrega.save()

    return JsonResponse({
        "mensagem": "Entrega finalizada com sucesso.",
        "id": entrega.id,
        "status": entrega.status,
    })


@csrf_exempt
def atualizar_status(request, entrega_id, novo_status):
    status_validos = [
        "aguardando",
        "subindo",
        "aguardando_retirada",
        "retornando",
        "finalizado"
    ]

    if novo_status not in status_validos:
        return JsonResponse({
            "erro": "Status inválido."
        }, status=400)

    try:
        entrega = Entrega.objects.get(id=entrega_id)
    except Entrega.DoesNotExist:
        return JsonResponse({
            "erro": "Entrega não encontrada."
        }, status=404)

    entrega.status = novo_status
    entrega.save()

    return JsonResponse({
        "mensagem": "Status atualizado com sucesso.",
        "id": entrega.id,
        "status": entrega.status,
    })