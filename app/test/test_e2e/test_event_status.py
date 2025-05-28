from datetime import datetime, timedelta
import re
from django.utils import timezone
from playwright.sync_api import expect
from app.models import Event, User, Ticket
from app.test.test_e2e.base import BaseE2ETest
from uuid import uuid4
from playwright.sync_api import TimeoutError
from django.db.models import Sum

class EventLifecycleE2ETest(BaseE2ETest):
    """Pruebas E2E para el ciclo de vida completo de un evento"""

    def create_test_user(self, is_organizer=False):
        """Crea usuarios con username único dentro de la prueba"""
        username = f"testuser_{uuid4().hex[:8]}"
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password123",
            is_organizer=is_organizer
        )
    
    def custom_logout(self):
        """Método personalizado para cerrar sesión usando el formulario"""
        logout_button = self.page.locator("button[name='logout']")
        with self.page.expect_navigation():
            logout_button.click()
        
        expect(self.page).to_have_url(re.compile(r".*/accounts/login/.*"))
        expect(self.page.get_by_role("link", name="Ingresá")).to_be_visible()

    def test_full_event_lifecycle(self):

        organizer = self.create_test_user(is_organizer=True)
        user = self.create_test_user()
        
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.get_by_label("Usuario").fill(organizer.username)
        self.page.get_by_label("Contraseña").fill("password123")
        
        with self.page.expect_navigation():
            self.page.get_by_role("button", name="Iniciar sesión").click()
        
        self.page.goto(f"{self.live_server_url}/events/create/")
        self.page.get_by_label("Título del Evento").fill("Festival de Música")
        self.page.get_by_label("Descripción").fill("Evento anual de música")
        self.page.locator("#date").fill((timezone.now() + timedelta(days=3)).strftime("%Y-%m-%d"))
        self.page.get_by_role("textbox", name="Hora").fill("18:00")
        self.page.get_by_label("Capacidad Máxima").fill("2")
        
        with self.page.expect_navigation():
            self.page.get_by_role("button", name="Crear Evento").click()
        
        event = Event.objects.get(title="Festival de Música")
        self.assertEqual(event.available_tickets, 2)
        
        self.custom_logout()
        self.login_user(user.username, "password123")
        self.page.goto(f"{self.live_server_url}/events/{event.pk}/")
        
        expect(self.page.get_by_role("link", name="Comprar Entradas")).to_be_visible()
        
        with self.page.expect_navigation():
            self.page.get_by_role("link", name="Comprar Entradas").click()

        self.page.select_option("#type_ticket", "GENERAL")

        self.page.evaluate(
            """
            ({ selector, value }) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.value = value;  // Establecer el valor directamente
                    element.dispatchEvent(new Event('input', { bubbles: true }));  // Disparar evento input
                } else {
                    console.error(`Element not found for selector: ${selector}`);
                }
            }
            """,
            {"selector": "#quantity", "value": "2"} 
        )


        expect(self.page.locator("#quantity")).to_have_value("2")

        self.page.fill("#card_number", "4111111111111111")  
        self.page.fill("#expiry_date", "12/25")           
        self.page.fill("#cvv", "123")                       
        self.page.fill("#cardholder_name", "Test User")    
        self.page.check("#terms_check")                    

        confirm_button = self.page.get_by_role("button", name="Confirmar Compra")
        expect(confirm_button).to_be_enabled(timeout=5000)

        with self.page.expect_navigation():
            confirm_button.click()

        event.refresh_from_db()  # Actualizar el estado del evento desde la base de datos
        self.assertEqual(event.available_tickets, 0)
        self.assertEqual(event.status, "AGOTADO")
        
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")

        total_tickets = Ticket.objects.aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 2)
        
        self.page.goto(f"{self.live_server_url}/events/{event.pk}/")
        expect(self.page.get_by_text("Agotado", exact=True)).to_be_visible()

        event = Event.objects.get(title="Festival de Música")
        if event:
            Event.objects.filter(pk=event.pk).update(status="FINALIZADO")

        self.page.goto(f"{self.live_server_url}/events/{event.pk}/")
        expect(self.page.locator(".badge:has-text('FINALIZADO')")).to_be_visible()