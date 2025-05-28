from django.test import TestCase, Client
from django.urls import reverse
from app.models import RefundRequest, User

class RefundRequestTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )
        cls.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )
    #TEST QUE VERIFICA QUE EL USUARIO ORGANIZADOR ACCEDA A SU VISTA DE REEMBOLSOS
    def test_refund_list_view_for_organizer(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("refund_requests"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refundRequest/refunds_organizer.html")
        self.assertIn("refunds", response.context)
    #TEST QUE VERIFICA QUE EL USUARIO REGULAR ACCEDA A SU VISTA DE REEMBOLSOS
    def test_refund_list_view_for_regular_user(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("refund_requests"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refundRequest/refunds.html")
        self.assertIn("refunds", response.context)
        self.assertEqual(response.context["user"], self.regular_user)
    #TEST QUE VALIDA QUE EL USUARIO CON REEMBOLSO PENDIENTE SEA REDIRECCIONADO A SU VISTA DE REEMBOLSOS
    def test_redirect_if_user_has_pending_refund(self):
        RefundRequest.objects.create(
            client=self.regular_user,
            ticket_code="ABC123",
            reason="No pude asistir",
            approved=None,
        )
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("refund_form"))
        self.assertRedirects(response, reverse("refund_requests"))
    #TEST QUE VERIFICA QUE EL USUARIO REGULAR PUEDA ACCEDER AL FORMULARIO DE REEMBOLSO SI NO TIENE PENDIENTE
    def test_user_can_access_refund_form_if_no_pending(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("refund_form"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refundRequest/refund_form.html")