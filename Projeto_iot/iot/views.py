from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Entrega


STATUS_EM_ANDAMENTO = [
    "aguardando",
    "subindo",
    "aguardando_retirada",
    "retornando",
]

STATUS_VALIDOS = [
    "aguardando",
    "subindo",
    "aguardando_retirada",
    "retornando",
    "finalizado",
]


def resposta_erro(mensagem, status=400):
    return JsonResponse({"status": "erro", "erro": mensagem, "mensagem": mensagem}, status=status)


def andar_cabine(entrega):
    if not entrega or entrega.status in {"aguardando", "retornando", "finalizado"}:
        return 0

    return entrega.andar_destino


def formatar_andar(andar):
    if andar == 0:
        return "Térreo"

    return f"{andar}º andar"


def entrega_para_json(entrega):
    criado_em = timezone.localtime(entrega.criado_em)
    cabine = andar_cabine(entrega)

    return {
        "id": entrega.id,
        "nome_morador": entrega.nome_morador,
        "numero_pedido": entrega.numero_pedido,
        "andar_destino": entrega.andar_destino,
        "andar_destino_label": formatar_andar(entrega.andar_destino),
        "andar_destino_display": entrega.get_andar_destino_display(),
        "andar_cabine": cabine,
        "andar_cabine_label": formatar_andar(cabine),
        "status_entrega": entrega.status,
        "status_display": entrega.get_status_display(),
        "executado": entrega.executado,
        "criado_em": criado_em.isoformat(),
        "criado_em_formatado": criado_em.strftime("%d/%m/%Y %H:%M"),
    }


def token_dispositivo(request):
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return request.headers.get("X-Iot-Token") or request.headers.get("X-Device-Token")


def dispositivo_autenticado(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token_configurado = getattr(settings, "IOT_DEVICE_TOKEN", "")
        token_recebido = token_dispositivo(request)

        if not token_configurado or token_recebido != token_configurado:
            return resposta_erro("Token do dispositivo invalido.", status=403)

        return view_func(request, *args, **kwargs)

    return wrapper


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

        messages.error(request, "Usuario ou senha invalidos.")

    return render(request, "login.html")


@login_required
def painel(request):
    ultima_entrega = Entrega.objects.order_by("-criado_em").first()
    historico = Entrega.objects.order_by("-criado_em")[:6]

    return render(
        request,
        "index.html",
        {
            "ultima_entrega": ultima_entrega,
            "entrega_atual": ultima_entrega,
            "historico": historico,
            "andar_cabine": andar_cabine(ultima_entrega),
            "andar_cabine_label": formatar_andar(andar_cabine(ultima_entrega)),
        },
    )


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def status_painel(request):
    if request.method != "GET":
        return resposta_erro("Metodo nao permitido.", status=405)

    ultima_entrega = Entrega.objects.order_by("-criado_em").first()
    historico = Entrega.objects.order_by("-criado_em")[:6]

    return JsonResponse(
        {
            "status": "ok",
            "tem_entrega": ultima_entrega is not None,
            "entrega": entrega_para_json(ultima_entrega) if ultima_entrega else None,
            "historico": [entrega_para_json(entrega) for entrega in historico],
        }
    )


@login_required
def criar_entrega(request):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    nome_morador = request.POST.get("nome_morador", "").strip()
    numero_pedido = request.POST.get("numero_pedido", "").strip()
    andar_destino = request.POST.get("andar_destino", "").strip()

    if not nome_morador or not numero_pedido or not andar_destino:
        return resposta_erro("Preencha todos os campos.", status=400)

    try:
        andar_destino = int(andar_destino)
    except ValueError:
        return resposta_erro("Andar de destino invalido.", status=400)

    andares_validos = {andar for andar, _ in Entrega.ANDARES}
    if andar_destino not in andares_validos:
        return resposta_erro("Andar de destino invalido.", status=400)

    entrega_em_andamento = Entrega.objects.filter(status__in=STATUS_EM_ANDAMENTO).first()

    if entrega_em_andamento:
        return JsonResponse(
            {
                "status": "bloqueado",
                "erro": "Ja existe uma entrega em andamento.",
                "mensagem": "Ja existe uma entrega em andamento.",
                "pedido_atual": entrega_em_andamento.numero_pedido,
                **entrega_para_json(entrega_em_andamento),
            },
            status=409,
        )

    entrega = Entrega.objects.create(
        nome_morador=nome_morador,
        numero_pedido=numero_pedido,
        andar_destino=andar_destino,
        status="aguardando",
        executado=False,
    )

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Entrega criada com sucesso.",
            **entrega_para_json(entrega),
        }
    )


def _buscar_entrega_para_retorno():
    return (
        Entrega.objects.filter(status__in=["subindo", "aguardando_retirada"])
        .order_by("-criado_em")
        .first()
    )


def _buscar_entrega_em_andamento():
    return Entrega.objects.filter(status__in=STATUS_EM_ANDAMENTO).order_by("-criado_em").first()


def _marcar_retorno():
    entrega = _buscar_entrega_para_retorno()

    if not entrega:
        return None

    entrega.status = "retornando"
    entrega.save(update_fields=["status"])
    return entrega


def _finalizar_entrega():
    entrega = _buscar_entrega_em_andamento()

    if not entrega:
        return None

    entrega.status = "finalizado"
    entrega.save(update_fields=["status"])
    return entrega


@login_required
def voltar_para_baixo_site(request):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    entrega = _marcar_retorno()
    if not entrega:
        return resposta_erro("Nenhuma entrega para retornar.", status=404)

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Elevador retornando para o terreo.",
            **entrega_para_json(entrega),
        }
    )


@login_required
def finalizar_entrega_site(request):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    entrega = _finalizar_entrega()
    if not entrega:
        return resposta_erro("Nenhuma entrega em andamento.", status=404)

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Entrega finalizada com sucesso.",
            **entrega_para_json(entrega),
        }
    )


@csrf_exempt
@dispositivo_autenticado
def comando_elevador(request):
    if request.method != "GET":
        return resposta_erro("Metodo nao permitido.", status=405)

    with transaction.atomic():
        entrega = (
            Entrega.objects.select_for_update()
            .filter(executado=False, status="aguardando")
            .order_by("criado_em")
            .first()
        )

        if entrega:
            entrega.executado = True
            entrega.status = "subindo"
            entrega.save(update_fields=["executado", "status"])

            return JsonResponse(
                {
                    "status": "ok",
                    "tem_comando": True,
                    "tipo": "ENTREGA",
                    **entrega_para_json(entrega),
                }
            )

    return JsonResponse(
        {
            "status": "ok",
            "tem_comando": False,
            "mensagem": "Nenhum comando pendente.",
        }
    )


@csrf_exempt
@dispositivo_autenticado
def status_elevador(request):
    if request.method != "GET":
        return resposta_erro("Metodo nao permitido.", status=405)

    entrega = Entrega.objects.order_by("-criado_em").first()

    if not entrega:
        return JsonResponse(
            {
                "status": "ok",
                "tem_entrega": False,
                "mensagem": "Nenhuma entrega encontrada.",
            }
        )

    return JsonResponse(
        {
            "status": "ok",
            "tem_entrega": True,
            **entrega_para_json(entrega),
        }
    )


@csrf_exempt
@dispositivo_autenticado
def voltar_para_baixo_api(request):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    entrega = _marcar_retorno()
    if not entrega:
        return resposta_erro("Nenhuma entrega para retornar.", status=404)

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Elevador retornando para o terreo.",
            **entrega_para_json(entrega),
        }
    )


@csrf_exempt
@dispositivo_autenticado
def finalizar_entrega_api(request):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    entrega = _finalizar_entrega()
    if not entrega:
        return resposta_erro("Nenhuma entrega em andamento.", status=404)

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Entrega finalizada com sucesso.",
            **entrega_para_json(entrega),
        }
    )


@csrf_exempt
@dispositivo_autenticado
def atualizar_status(request, entrega_id, novo_status):
    if request.method != "POST":
        return resposta_erro("Metodo nao permitido.", status=405)

    if novo_status not in STATUS_VALIDOS:
        return resposta_erro("Status invalido.", status=400)

    try:
        entrega = Entrega.objects.get(id=entrega_id)
    except Entrega.DoesNotExist:
        return resposta_erro("Entrega nao encontrada.", status=404)

    entrega.status = novo_status
    entrega.save(update_fields=["status"])

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Status atualizado com sucesso.",
            **entrega_para_json(entrega),
        }
    )
def criar_admin(request):
    if User.objects.filter(username="admin").exists():
        return HttpResponse("Admin já existe.")

    User.objects.create_superuser(
        username="admin",
        email="admin@email.com",
        password="admin123456"
    )

    return HttpResponse("Admin criado com sucesso.")
