from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import RefundRequest
from django.utils import timezone

User = get_user_model()

class RefundRequestModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_user = User.objects.create_user(
            username="cliente_test",
            email="cliente@example.com",
            password="password123",
            is_organizer=False,
        )
        cls.valid_ticket_code = "TICKET123"
        cls.valid_reason = "No puedo asistir al evento"
        cls.error_msg_ticket = "Por favor ingrese el codigo del ticket a reembolsar"
        cls.error_msg_reason = "Por favor ingrese la razon del reembolso"
    #TEST QUE CREA UNA SOLICITUD DE REEMBOLSO VALIDA
    def test_create_refund_valid(self):
        """Debe crear una solicitud de reembolso válida correctamente."""
        refund = RefundRequest.create_refund(
            self.client_user, self.valid_ticket_code, self.valid_reason
        )

        self.assertIsInstance(refund, RefundRequest)
        self.assertEqual(refund.client, self.client_user)
        self.assertEqual(refund.ticket_code, self.valid_ticket_code)
        self.assertEqual(refund.reason, self.valid_reason)
        self.assertIsNone(refund.approved)
        self.assertIsNotNone(refund.created_at)
        self.assertIsNone(refund.approval_date)
    #TEST QUE CREA UN REEMBOLSO INVÁLIDO Y VERIFICA QUE RETORNE ERRORES
    def test_create_refund_invalid(self):
        ticket_code = ""
        reason = ""

        success, errors = RefundRequest.create_refund(self.client_user, ticket_code, reason)

        self.assertFalse(success)
        self.assertIsInstance(errors, dict)
        self.assertIn("ticket_code", errors)
        self.assertIn("reason", errors)
        self.assertEqual(errors["ticket_code"], self.error_msg_ticket)
        self.assertEqual(errors["reason"], self.error_msg_reason)
    #TEST QUE VERIFICA QUE UN USUARIO TENGA ALGUN REEMBOLSO PENDIENTE
    def test_is_pending_returns_true(self):
        """Debe retornar True si el usuario tiene una solicitud pendiente."""
        RefundRequest.objects.create(
            client=self.client_user,
            ticket_code="ABC123",
            reason="No pude asistir",
            approved=None
        )

        self.assertTrue(RefundRequest.is_pending(self.client_user.pk))
    #TEST QUE VERIFICA QUE UN USUARIO NO TENGA REEMBOLSO PENDIENTE
    def test_is_pending_returns_false(self):
        """Debe retornar False si el usuario no tiene solicitudes pendientes."""
        RefundRequest.objects.create(
            client=self.client_user,
            ticket_code="XYZ789",
            reason="Me equivoqué al comprar",
            approved=True,
            approval_date=timezone.now()
        )
        RefundRequest.objects.create(
            client=self.client_user,
            ticket_code="LMN456",
            reason="Cambio de planes",
            approved=False
        )

        self.assertFalse(RefundRequest.is_pending(self.client_user.pk))
