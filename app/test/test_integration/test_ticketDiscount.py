from django.test import TestCase, Client
from django.urls import reverse
import datetime
from app.models import TicketDiscount, User, Event
from django.utils import timezone

from app.forms import TicketDiscountForm





class BaseTicketDiscountTestCase(TestCase):
    """Clase base con la configuración común para todos los tests de descuentos de entradas"""

    def setUp(self):
        # Crear un usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )

        # Crear un usuario regular
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )


        # Cliente para hacer peticiones
        self.client = Client()


class TicketDiscountListViewTest(BaseTicketDiscountTestCase):
    """Tests para la vista de listado de descuentos de entradas"""

    def test_ticket_discount_view_with_login(self):
        """Test que verifica que la vista ticket discount no funciona cuando el usuario está logueado e intenta acceder a la lista de descuentos de entradas"""
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista ticket discount
        response = self.client.get(reverse("ticketdiscount_list"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response["Location"])


    def test_ticket_discount_view_with_organizer_login(self):
        """Test que verifica que la vista ticket discount funciona cuando el usuario es organizador"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Hacer petición a la vista ticket discount
        response = self.client.get(reverse("ticketdiscount_list"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_is_organizer"])
