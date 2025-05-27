from playwright.sync_api import expect
from app.models import RefundRequest, Ticket, Event, User
from app.test.test_e2e.base import BaseE2ETest
from datetime import datetime, timedelta
import re


class RefundRequestE2ETest(BaseE2ETest):

    def setUp(self):
        super().setUp()

        # Crear usuario organizador requerido por Event
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear evento asociado al organizador
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento",
            scheduled_at=datetime.now() + timedelta(days=10),
            organizer=self.organizer,
        )

        # Crear usuario cliente
        self.client_user = User.objects.create_user(
            username="cliente",
            email="cliente@example.com",
            password="password123",
            is_organizer=False,
        )

        # Crear ticket para el cliente
        self.ticket = Ticket.objects.create(
            user=self.client_user,
            event=self.event,
            type_ticket="GENERAL",
            quantity=1,
            ticket_code="TICKET123",
        )

        # Crear un reembolso pendiente para ese usuario
        self.pending_refund = RefundRequest.objects.create(
            client=self.client_user,
            ticket_code=self.ticket.ticket_code,
            reason="Razón inicial",
            approved=None,
        )
    #TEST QUE VERIFICA QUE UN USUARIO CON REEMBOLSO PENDIENTE NO PUEDE CREAR UNO NUEVO
    def test_cannot_create_new_refund_if_pending(self):
        """Usuario con reembolso pendiente no puede crear uno nuevo"""

        self.login_user("cliente", "password123")

        # Intentar ir a la página de crear reembolso
        self.page.goto(f"{self.live_server_url}/refunds/create/")

        # Como hay reembolso pendiente, se debería redirigir a la lista
        expect(self.page).to_have_url(f"{self.live_server_url}/refunds/")

        # Verificar que no hay botón para crear nuevo reembolso (opcional)
        create_button = self.page.get_by_role("link", name="Crear Reembolso")
        expect(create_button).to_have_count(0)
    
    #TEST QUE VERIFICA QUE SE PUEDE CREAR UN NUEVO REEMBOLSO SI NO HAY PENDIENTES
    def test_can_create_new_refund_if_no_pending(self):
        
        self.login_user("cliente", "password123")
        
        test_ticket = Ticket.objects.create(
            ticket_code="TEST123",
            user=self.client_user,
            event=self.event,
            type_ticket="GENERAL",
            quantity=1
        )
            
        # Eliminar cualquier reembolso pendiente del usuario para el test
        RefundRequest.objects.filter(client=self.client_user, approved__isnull=True).delete()
    
        self.page.goto(f"{self.live_server_url}/refunds/")
        # Verificar que el botón de crear reembolso está visible
        create_button = self.page.get_by_role("link", name="Solicitar reembolso")
        expect(create_button).to_be_visible()
        # Hacer clic en el botón para crear un nuevo reembolso    
        create_button.click()
        expect(self.page).to_have_url(f"{self.live_server_url}/refunds/create/")
        select = self.page.locator('select[name="ticket_code"]')
        expect(select).to_be_visible()
        
        # Verifica que el select tiene el ticket de prueba
        options = select.locator('option')
        expect(options).to_contain_text(["TEST123"])
        
        # Seleccionar el ticket y llenar los datos
        select.select_option(value="TEST123")
        self.page.fill('input[name="reason"]', "Motivo de prueba")
        self.page.check('input[id="termsCheck"]')
        
        # Enviar el formulario
        self.page.get_by_role("button", name="Solicitar reembolso").click()
        
        # Verificar que se redirige a la página de detalle del reembolso
        expect(self.page).to_have_url(re.compile(r".*/refunds/\d+/"))
        
        # Verificar que el reembolso se creó correctamente
        expect(self.page.get_by_text("Pendiente")).to_be_visible()