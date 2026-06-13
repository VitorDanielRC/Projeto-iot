from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Entrega


@override_settings(IOT_DEVICE_TOKEN="secret-token")
class EntregaApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="senha-forte")
        self.client.login(username="admin", password="senha-forte")

    def test_criar_entrega_retorna_json_compativel_com_frontend(self):
        response = self.client.post(
            reverse("criar_entrega"),
            {
                "nome_morador": "Joao Silva",
                "numero_pedido": "PED-1023",
                "andar_destino": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["numero_pedido"], "PED-1023")
        self.assertEqual(data["andar_destino"], 2)
        self.assertEqual(data["andar_destino_display"], "2º Andar - Apartamento 201")
        self.assertEqual(data["status_entrega"], "aguardando")
        self.assertEqual(data["criado_por_nome"], "admin")

        entrega = Entrega.objects.get(numero_pedido="PED-1023")
        self.assertEqual(entrega.criado_por, self.user)

    def test_criar_entrega_para_o_terreo(self):
        response = self.client.post(
            reverse("criar_entrega"),
            {
                "nome_morador": "Recepcao",
                "numero_pedido": "PED-TERREO",
                "andar_destino": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["andar_destino"], 0)
        self.assertEqual(data["andar_destino_label"], "Térreo")
        self.assertEqual(data["andar_cabine"], 0)
        self.assertEqual(data["criado_por_nome"], "admin")

    def test_painel_renderiza_interface_principal(self):
        response = self.client.get(reverse("painel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Painel FoodLift IoT")
        self.assertContains(response, "Vis&atilde;o do entregador")
        self.assertContains(response, "Vis&atilde;o do cliente")
        self.assertContains(response, "Aguardando chegada")

    def test_visao_entregador_abre_com_aba_entregador_ativa(self):
        response = self.client.get(reverse("visao_entregador"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="abaEntregador" class="role-panel active"')
        self.assertContains(response, 'href="/entregador/"')

    def test_visao_cliente_abre_com_aba_cliente_ativa(self):
        response = self.client.get(reverse("visao_cliente"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="abaCliente" class="role-panel active"')
        self.assertContains(response, 'href="/cliente/"')

    def test_tela_de_cadastro_renderiza_formulario(self):
        self.client.logout()

        response = self.client.get(reverse("cadastro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro")
        self.assertContains(response, "Criar cadastro")

    def test_login_nao_exibe_google_sem_credenciais(self):
        self.client.logout()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Entrar com Google")

    @override_settings(
        GOOGLE_LOGIN_ENABLED=True,
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APPS": [
                    {
                        "client_id": "client-id",
                        "secret": "client-secret",
                        "key": "",
                    }
                ],
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
            }
        },
    )
    def test_login_exibe_google_quando_configurado(self):
        self.client.logout()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar com Google")
        self.assertContains(response, "/accounts/google/login/")

    def test_cadastro_cria_usuario_e_redireciona_para_painel(self):
        self.client.logout()

        response = self.client.post(
            reverse("cadastro"),
            {
                "username": "novo_usuario",
                "email": "novo@email.com",
                "password1": "senha-forte",
                "password2": "senha-forte",
            },
        )

        self.assertRedirects(response, reverse("painel"))
        self.assertTrue(User.objects.filter(username="novo_usuario").exists())

    def test_cadastro_bloqueia_usuario_repetido(self):
        self.client.logout()

        response = self.client.post(
            reverse("cadastro"),
            {
                "username": "admin",
                "email": "admin2@email.com",
                "password1": "senha-forte",
                "password2": "senha-forte",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este usuario ja existe.")

    def test_bloqueia_entrega_quando_ja_existe_entrega_em_andamento(self):
        Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-1",
            andar_destino=3,
            status="aguardando",
        )

        response = self.client.post(
            reverse("criar_entrega"),
            {
                "nome_morador": "Joao",
                "numero_pedido": "PED-2",
                "andar_destino": "2",
            },
        )

        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["status"], "bloqueado")
        self.assertEqual(data["pedido_atual"], "PED-1")

    def test_api_do_dispositivo_exige_token(self):
        response = self.client.get(reverse("comando_elevador"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "erro")

    def test_comando_elevador_envia_primeira_entrega_aguardando(self):
        entrega = Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-55",
            andar_destino=3,
            status="aguardando",
        )

        response = self.client.get(reverse("comando_elevador"), HTTP_X_IOT_TOKEN="secret-token")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["tem_comando"])
        self.assertEqual(data["tipo"], "ENTREGA")
        self.assertEqual(data["andar_destino"], 3)

        entrega.refresh_from_db()
        self.assertTrue(entrega.executado)
        self.assertEqual(entrega.status, "subindo")

    def test_painel_pode_finalizar_entrega_sem_expor_token_do_dispositivo(self):
        entrega = Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-77",
            andar_destino=2,
            status="subindo",
            executado=True,
        )

        response = self.client.post(reverse("finalizar_entrega_site"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        entrega.refresh_from_db()
        self.assertEqual(entrega.status, "finalizado")

    def test_cliente_confirma_recebimento_quando_entrega_aguardando_retirada(self):
        entrega = Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-CLIENTE",
            andar_destino=2,
            status="aguardando_retirada",
            executado=True,
        )

        response = self.client.post(reverse("confirmar_recebimento_site"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["status_entrega"], "finalizado")
        self.assertEqual(data["numero_pedido"], "PED-CLIENTE")

        entrega.refresh_from_db()
        self.assertEqual(entrega.status, "finalizado")

    def test_cliente_nao_confirma_antes_do_elevador_chegar(self):
        entrega = Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-SUBINDO",
            andar_destino=2,
            status="subindo",
            executado=True,
        )

        response = self.client.post(reverse("confirmar_recebimento_site"))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "erro")

        entrega.refresh_from_db()
        self.assertEqual(entrega.status, "subindo")

    def test_status_painel_retorna_entrega_e_historico_para_interface(self):
        Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-99",
            andar_destino=3,
            status="aguardando_retirada",
            executado=True,
            criado_por=self.user,
        )

        response = self.client.get(reverse("status_painel"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["tem_entrega"])
        self.assertEqual(data["entrega"]["numero_pedido"], "PED-99")
        self.assertEqual(data["entrega"]["andar_destino_display"], "3º Andar - Apartamento 301")
        self.assertEqual(data["entrega"]["andar_cabine"], 3)
        self.assertEqual(data["entrega"]["criado_por_nome"], "admin")
        self.assertEqual(len(data["historico"]), 1)

    def test_entrega_criada_por_um_usuario_aparece_para_outro_no_painel(self):
        outro_usuario = User.objects.create_user(username="morador", password="senha-forte")

        self.client.post(
            reverse("criar_entrega"),
            {
                "nome_morador": "Maria",
                "numero_pedido": "PED-COMPARTILHADO",
                "andar_destino": "2",
            },
        )

        self.client.logout()
        self.client.login(username=outro_usuario.username, password="senha-forte")

        response = self.client.get(reverse("painel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PED-COMPARTILHADO")
        self.assertContains(response, "Maria")
        self.assertContains(response, "Criado por admin")

    def test_status_painel_retorna_entregas_globais_para_qualquer_usuario(self):
        outro_usuario = User.objects.create_user(username="porteiro", password="senha-forte")

        self.client.post(
            reverse("criar_entrega"),
            {
                "nome_morador": "Joao",
                "numero_pedido": "PED-GLOBAL",
                "andar_destino": "1",
            },
        )

        self.client.logout()
        self.client.login(username=outro_usuario.username, password="senha-forte")

        response = self.client.get(reverse("status_painel"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["entrega"]["numero_pedido"], "PED-GLOBAL")
        self.assertEqual(data["entrega"]["criado_por_nome"], "admin")
        self.assertEqual(data["historico"][0]["numero_pedido"], "PED-GLOBAL")
        self.assertEqual(data["historico"][0]["criado_por_nome"], "admin")

    def test_dispositivo_pode_atualizar_status_com_post_e_token(self):
        entrega = Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-88",
            andar_destino=2,
            status="subindo",
            executado=True,
        )

        response = self.client.post(
            reverse("atualizar_status", args=[entrega.id, "aguardando_retirada"]),
            HTTP_X_IOT_TOKEN="secret-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_entrega"], "aguardando_retirada")

        entrega.refresh_from_db()
        self.assertEqual(entrega.status, "aguardando_retirada")

    def test_create_admin_from_env_cria_superusuario(self):
        env = {
            "DJANGO_SUPERUSER_USERNAME": "admin_render",
            "DJANGO_SUPERUSER_EMAIL": "admin@render.com",
            "DJANGO_SUPERUSER_PASSWORD": "senha-super-forte",
        }
        output = StringIO()

        with patch.dict("os.environ", env, clear=False):
            call_command("create_admin_from_env", stdout=output)

        user = User.objects.get(username="admin_render")
        self.assertEqual(user.email, "admin@render.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("senha-super-forte"))
        self.assertIn("created", output.getvalue())

    def test_create_admin_from_env_atualiza_superusuario_existente(self):
        User.objects.create_user(username="admin_render", password="senha-antiga")
        env = {
            "DJANGO_SUPERUSER_USERNAME": "admin_render",
            "DJANGO_SUPERUSER_EMAIL": "novo@render.com",
            "DJANGO_SUPERUSER_PASSWORD": "senha-nova-forte",
        }
        output = StringIO()

        with patch.dict("os.environ", env, clear=False):
            call_command("create_admin_from_env", stdout=output)

        user = User.objects.get(username="admin_render")
        self.assertEqual(user.email, "novo@render.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("senha-nova-forte"))
        self.assertIn("updated", output.getvalue())
