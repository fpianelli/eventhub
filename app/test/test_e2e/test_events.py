import datetime
import re

from django.utils import timezone
from playwright.sync_api import expect

from app.models import Event, User
from app.test.test_e2e.base import BaseE2ETest


class EventBaseTest(BaseE2ETest):
    """Clase base específica para tests de eventos"""

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

        # Crear eventos de prueba
        # Evento 1
        event_date1 = timezone.make_aware(datetime.datetime(2030, 2, 10, 10, 10))
        self.event1 = Event.objects.create(
            title="Evento de prueba 1",
            description="Descripción del evento 1",
            scheduled_at=event_date1,
            organizer=self.organizer,
        )

        # Evento 2
        event_date2 = timezone.make_aware(datetime.datetime(2030, 3, 15, 14, 30))
        self.event2 = Event.objects.create(
            title="Evento de prueba 2",
            description="Descripción del evento 2",
            scheduled_at=event_date2,
            organizer=self.organizer,
        )

        # Evento 3
        self.event3 = Event.objects.create(
            title="Evento de prueba 3",
            description="Descripción del evento 3",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )

    def _table_has_event_info(self):
        """Método auxiliar para verificar que la tabla tiene la información correcta de eventos"""
        # Verificar encabezados de la tabla
        headers = self.page.locator("table thead th")
        expect(headers.nth(0)).to_have_text("Título")
        expect(headers.nth(1)).to_have_text("Descripción")
        expect(headers.nth(2)).to_have_text("Fecha")
        expect(headers.nth(3)).to_have_text("Estado")  
        expect(headers.nth(4)).to_have_text("Disponibilidad")
        expect(headers.nth(5)).to_have_text("Categorias")
        expect(headers.nth(6)).to_have_text("Acciones")

        # Buscar eventos por título para evitar dependencia del orden
        event1_row = self.page.locator("tr:has-text('Evento de prueba 1')")
        event2_row = self.page.locator("tr:has-text('Evento de prueba 2')")
        event3_row = self.page.locator("tr:has-text('Evento de prueba 3')")

        # Verificar que los eventos están presentes
        expect(event1_row).to_be_visible()
        expect(event2_row).to_be_visible()
        expect(event3_row).to_be_visible()

        # Verificar datos del evento 1
        expect(event1_row.locator("td").nth(0)).to_have_text("Evento de prueba 1")
        expect(event1_row.locator("td").nth(1)).to_have_text("Descripción del evento 1")
        expect(event1_row.locator("td").nth(2)).to_have_text("10 feb 2030, 10:10")
        expect(event1_row.locator("td").nth(3)).to_contain_text("Activo", ignore_case=True)

        # Verificar datos del evento 2
        expect(event2_row.locator("td").nth(0)).to_have_text("Evento de prueba 2")
        expect(event2_row.locator("td").nth(1)).to_have_text("Descripción del evento 2")
        expect(event2_row.locator("td").nth(2)).to_have_text("15 mar 2030, 14:30")
        expect(event2_row.locator("td").nth(3)).to_contain_text("Activo", ignore_case=True)

        # Verificar datos del evento 3
        expect(event3_row.locator("td").nth(0)).to_have_text("Evento de prueba 3")
        expect(event3_row.locator("td").nth(1)).to_have_text("Descripción del evento 3")
        expect(event3_row.locator("td").nth(3)).to_contain_text("Finalizado", ignore_case=True)

    def _table_has_correct_actions(self, user_type):
        """Método auxiliar para verificar que las acciones son correctas según el tipo de usuario"""
        # Usar el evento1 para verificar acciones
        row = self.page.locator(f"tr:has-text('{self.event1.title}')")
        
        detail_button = row.get_by_role("link", name="Ver Detalle")
        edit_button = row.get_by_role("link", name="Editar")
        delete_form = row.locator("form")

        expect(detail_button).to_be_visible()
        expect(detail_button).to_have_attribute("href", f"/events/{self.event1.id}/")

        if user_type == "organizador":
            expect(edit_button).to_be_visible()
            expect(edit_button).to_have_attribute("href", f"/events/{self.event1.id}/edit/")

            expect(delete_form).to_have_attribute("action", f"/events/{self.event1.id}/delete/")
            expect(delete_form).to_have_attribute("method", "POST")

            delete_button = delete_form.get_by_role("button", name="Eliminar")
            expect(delete_button).to_be_visible()
        else:
            expect(edit_button).to_have_count(0)
            expect(delete_form).to_have_count(0)


class EventAuthenticationTest(EventBaseTest):
    """Tests relacionados con la autenticación y permisos de usuarios en eventos"""

    def test_events_page_requires_login(self):
        """Test que verifica que la página de eventos requiere inicio de sesión"""
        # Cerrar sesión si hay alguna activa
        self.context.clear_cookies()

        # Intentar ir a la página de eventos sin iniciar sesión
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que redirige a la página de login
        expect(self.page).to_have_url(re.compile(r"/accounts/login/"))


class EventDisplayTest(EventBaseTest):
    """Tests relacionados con la visualización de la página de eventos"""

    def test_events_page_display_as_organizer(self):
        """Test que verifica la visualización correcta de la página de eventos para organizadores"""
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar el título de la página
        expect(self.page).to_have_title("Eventos")

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("organizador")

    def test_events_page_regular_user(self):
        """Test que verifica la visualización de la página de eventos para un usuario regular"""
        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        expect(self.page).to_have_title("Eventos")

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("regular")

    def test_events_page_no_events(self):
        """Test que verifica el comportamiento cuando no hay eventos"""
        # Eliminar todos los eventos
        Event.objects.all().delete()

        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe un mensaje indicando que no hay eventos
        no_events_message = self.page.locator("text=No hay eventos disponibles")
        expect(no_events_message).to_be_visible()


class EventPermissionsTest(EventBaseTest):
    """Tests relacionados con los permisos de usuario para diferentes funcionalidades"""

    def test_buttons_visible_only_for_organizer(self):
        """Test que verifica que los botones de gestión solo son visibles para organizadores"""
        # Primero verificar como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_be_visible()

        # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que NO existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_have_count(0)


class EventCRUDTest(EventBaseTest):
    """Tests relacionados con las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) de eventos"""

    def test_create_new_event_organizer(self):
        """Test que verifica la funcionalidad de crear un nuevo evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Hacer clic en el botón de crear evento
        self.page.get_by_role("link", name="Crear Evento").click()

        # Verificar que estamos en la página de creación de evento
        expect(self.page).to_have_url(f"{self.live_server_url}/events/create/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Crear evento")
        expect(header).to_be_visible()

        # Completar el formulario
        self.page.get_by_label("Título del Evento").fill("Evento de prueba E2E")
        self.page.get_by_label("Descripción").fill("Descripción creada desde prueba E2E")
        self.page.locator("#date").fill("2025-06-15")
        self.page.locator("#time").fill("16:45")

        # Enviar el formulario
        with self.page.expect_navigation():
            self.page.get_by_role("button", name="Crear Evento").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que el nuevo evento existe
        row = self.page.locator(f"table tbody tr:has-text('Evento de prueba E2E')")
        expect(row).to_be_visible()
        
        expect(row.locator("td").nth(0)).to_have_text("Evento de prueba E2E")
        expect(row.locator("td").nth(1)).to_have_text("Descripción creada desde prueba E2E")
        expect(row.locator("td").nth(2)).to_have_text("15 jun 2025, 16:45")

    def test_edit_event_organizer(self):
        """Test que verifica la funcionalidad de editar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Buscar el evento por título
        row = self.page.locator("tr:has-text('Evento de prueba 2')")
        
        # Hacer clic en el botón editar
        row.get_by_role("link", name="Editar").click()

        # Verificar que estamos en la página de edición
        expect(self.page).to_have_url(f"{self.live_server_url}/events/{self.event2.id}/edit/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Editar evento")
        expect(header).to_be_visible()

        # Verificar y editar los campos
        title = self.page.get_by_label("Título del Evento")
        expect(title).to_have_value("Evento de prueba 2")
        title.fill("Titulo editado")

        description = self.page.get_by_label("Descripción")
        expect(description).to_have_value("Descripción del evento 2")
        description.fill("Descripcion Editada")

        date = self.page.locator("#date")
        expect(date).to_have_value("2030-03-15")
        date.fill("2025-04-20")

        time = self.page.locator("#time")
        expect(time).to_have_value("14:30")
        time.fill("03:00")

        # CORRECCIÓN PRINCIPAL: Usar selector CSS en lugar de texto
        self.page.locator("button.btn-primary").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que el evento ha sido actualizado
        row = self.page.locator(f"table tbody tr:has-text('Titulo editado')")
        expect(row).to_be_visible()
        
        expect(row.locator("td").nth(0)).to_have_text("Titulo editado")
        expect(row.locator("td").nth(1)).to_have_text("Descripcion Editada")
        expect(row.locator("td").nth(2)).to_have_text("20 abr 2025, 03:00")

    def test_delete_event_organizer(self):
        """Test que verifica la funcionalidad de eliminar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Contar eventos antes de eliminar
        initial_count = Event.objects.count()

        # Buscar el evento por título
        row = self.page.locator("tr:has-text('Evento de prueba 1')")
        
        # Hacer clic en el botón eliminar
        row.get_by_role("button", name="Eliminar").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que se redujo el conteo
        expect(self.page.locator("table tbody tr")).to_have_count(initial_count - 1)

        # Verificar que el evento eliminado ya no aparece
        expect(self.page.locator("tr:has-text('Evento de prueba 1')")).to_have_count(0)


class EventCountdownE2ETest(EventBaseTest):
    """Tests E2E para la funcionalidad de cuenta regresiva de eventos"""

    def test_countdown_past_event(self):
        """Test que verifica que no se muestra la cuenta regresiva para eventos pasados"""

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Navegar al evento que ya ocurrió
        self.page.goto(f"{self.live_server_url}/events/{self.event3.id}/")

        # Verificar que la sección de countdown no existe
        expect(self.page.locator(".countdown-container")).to_have_count(0)

        # Verificar que no se muestra el mensaje de que el evento ha comenzado
        expect(self.page.locator("text=¡El evento ha comenzado!")).to_have_count(0)

    def test_countdown_not_displayed_organizers(self):
        """Test que verifica que los organizadores no ven la cuenta regresiva"""

        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Navegar al evento 1
        self.page.goto(f"{self.live_server_url}/events/{self.event1.id}/")

        # Verificar que la sección de countdown no existe
        expect(self.page.locator(".countdown-container")).to_have_count(0)