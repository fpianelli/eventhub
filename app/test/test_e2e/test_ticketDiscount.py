from django.utils import timezone
import datetime
import re

from playwright.sync_api import expect

from app.models import User, Event
from app.test.test_e2e.base import BaseE2ETest

class TicketDiscountBaseTest(BaseE2ETest):
    """Clase base específica para tests de descuento de tickets"""

    def setUp(self):
        super().setUp()

        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear usuario regular
        self.regular_user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )



class TicketDiscountAuthenticationTest(TicketDiscountBaseTest):
    """Tests relacionados con la autenticación y permisos de usuarios en descuento tickets"""

    def test_ticket_discount_page_requires_login(self):
        """Test que verifica que la página de descuento tickets requiere inicio de sesión"""
        # Cerrar sesión si hay alguna activa
        self.context.clear_cookies()

        # Intentar ir a la página de eventos sin iniciar sesión
        self.page.goto(f"{self.live_server_url}/ticketdiscounts/")


        # Verificar que redirige a la página de login
        expect(self.page).to_have_url(re.compile(r"/accounts/login/"))

class TicketDiscountPermissionsTest(TicketDiscountBaseTest):
    """Tests relacionados con los permisos de usuario para diferentes funcionalidades"""

    def test_buttons_visible_only_for_organizer(self):
        """Test que verifica que los botones de gestión solo son visibles para organizadores"""
        # Primero verificar como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/ticketdiscounts/")

        # Verificar que existe el botón de crear
        create_button = self.page.get_by_role("link", name="+ Crear nuevo")
        expect(create_button).to_be_visible()

        # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Verificar que NO existe el botón de crear
        create_button = self.page.get_by_role("link", name="Descuento Tickets")
        expect(create_button).to_have_count(0)
