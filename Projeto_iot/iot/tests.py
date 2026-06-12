from django.contrib.auth.models import User
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

    def test_painel_renderiza_interface_principal(self):
        response = self.client.get(reverse("painel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Painel FoodLift IoT")
        self.assertContains(response, "Nova entrega")

    def test_tela_de_cadastro_renderiza_formulario(self):
        self.client.logout()

        response = self.client.get(reverse("cadastro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro")
        self.assertContains(response, "Criar cadastro")

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

    def test_status_painel_retorna_entrega_e_historico_para_interface(self):
        Entrega.objects.create(
            nome_morador="Maria",
            numero_pedido="PED-99",
            andar_destino=3,
            status="aguardando_retirada",
            executado=True,
        )

        response = self.client.get(reverse("status_painel"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["tem_entrega"])
        self.assertEqual(data["entrega"]["numero_pedido"], "PED-99")
        self.assertEqual(data["entrega"]["andar_destino_display"], "3º Andar - Apartamento 301")
        self.assertEqual(data["entrega"]["andar_cabine"], 3)
        self.assertEqual(len(data["historico"]), 1)

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
