from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from datetime import timedelta
from django.core.management import call_command
from app.models import Event, User, Ticket, Category

class EventStatusIntegrationTest(TestCase):
    def setUp(self):
        """Configuración inicial para todas las pruebas"""
        self.client = Client()
        self.organizer = User.objects.create_user(
            username="organizer_test",
            email="organizer@example.com",
            password="password123",
            is_organizer=True,
        )
        self.user = User.objects.create_user(
            username="usuario_test",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )
        
        self.category1 = Category.objects.create(name="Concierto", is_active=True)
        self.category2 = Category.objects.create(name="Teatro", is_active=True)
        
        now = timezone.now()
        
        self.event_1 = Event.objects.create(
            title="Evento ACTIVO",
            description="Evento en estado ACTIVO",
            scheduled_at=now + timedelta(days=2),
            organizer=self.organizer,
            max_capacity=2, 
            status="ACTIVO"
        )
        self.event_1.categories.add(self.category1)
        
        self.event_2 = Event.objects.create(
            title="Evento AGOTADO",
            description="Evento en estado AGOTADO",
            scheduled_at=now + timedelta(days=3),
            organizer=self.organizer,
            max_capacity=50,
            status="AGOTADO"
        )
        self.event_2.categories.add(self.category2)
        
        self.event_3 = Event.objects.create(
            title="Evento CANCELADO",
            description="Evento en estado CANCELADO",
            scheduled_at=now + timedelta(days=4),
            organizer=self.organizer,
            max_capacity=200,
            status="CANCELADO"
        )
        
        self.event_4 = Event.objects.create(
            title="Evento FINALIZADO",
            description="Evento en estado FINALIZADO",
            scheduled_at=now - timedelta(days=1),
            organizer=self.organizer,
            max_capacity=150,
            status="FINALIZADO"
        )
        
        self.event_5 = Event.objects.create(
            title="Evento REPROGRAMADO",
            description="Evento en estado REPROGRAMADO",
            scheduled_at=now - timedelta(days=1),  
            organizer=self.organizer,
            max_capacity=100,
            status="REPROGRAMADO",
            new_scheduled_at=now + timedelta(days=5)
        )
        
        self.events = {
            'active': self.event_1,
            'sold_out': self.event_2,
            'canceled': self.event_3,
            'finished': self.event_4,
            'rescheduled': self.event_5
        }



    def test_full_event_lifecycle(self):
        """Test completo del ciclo de vida usando el evento ACTIVO"""
        event = self.events['active']
        
        self.assertTrue(self.client.login(username="usuario_test", password="password123"))
        
        response = self.client.get(reverse("event_detail", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ACTIVO")
        self.assertContains(response, "2 entradas disponibles")
        
        response = self.client.post(
            reverse("ticket_form", args=[event.pk]),
            {
                "type_ticket": "GENERAL", 
                "quantity": "1",  
            },
            follow=True  
        )
        
        self.assertContains(response, "Mis Entradas", status_code=200)  
        event.refresh_from_db()
        self.assertEqual(event.available_tickets, 1)
        
        response = self.client.post(
            reverse("ticket_form", args=[event.pk]),
            {
                "type_ticket": "VIP", 
                "quantity": "1",
            },
            follow=True
        )
        
        event.refresh_from_db()
        self.assertEqual(event.status, "AGOTADO")
        self.assertEqual(event.available_tickets, 0)
        
        response = self.client.post(
            reverse("ticket_form", args=[event.pk]),
            {"type_ticket": "General", "quantity": "1"},
            follow=True
        )
        self.assertContains(response, "agotadas")



    def test_blocked_purchase_flows(self):
        """Test de compras bloqueadas para los estados CANCELADO/FINALIZADO/AGOTADO"""
        self.client.login(username="usuario_test", password="password123")
        
        #CANCELADO
        response = self.client.get(reverse("ticket_form", args=[self.events['canceled'].pk]))
        self.assertEqual(response.status_code, 302)  # Verificar redirección
        response = self.client.get(response.url)  # Seguir la redirección
        self.assertContains(response, "cancelado")  # Mensaje en event_detail
            
        #FINALIZADO
        response = self.client.post(
            reverse("ticket_form", args=[self.events['finished'].pk]),
            {"type_ticket": "General", "quantity": 1}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("no se pueden comprar" in str(m).lower() for m in messages))
        
        #AGOTADO
        response = self.client.post(
            reverse("ticket_form", args=[self.events['sold_out'].pk]),
            {"type_ticket": "VIP", "quantity": 1},
            follow=True
        )
        self.assertContains(response, "agotadas", status_code=200)
        
        #REPROGRAMADO (debería permitir la compra si hay capacidad)
        response = self.client.get(reverse("ticket_form", args=[self.events['rescheduled'].pk]))
        self.assertEqual(response.status_code, 200)


    def test_event_management_by_organizer(self):
        """Test de gestión de eventos por el organizador"""
        self.client.login(username="organizer_test", password="password123")
        
        #Crear evento
        new_date = (timezone.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        response = self.client.post(reverse("event_form"), {
            "title": "Nuevo Evento Test",
            "description": "Descripción test",
            "date": new_date,
            "time": "20:00",
            "max_capacity": 100,
            "status": "ACTIVO",
            "categories": [self.category1.pk, self.category2.pk]
        })
        self.assertRedirects(response, reverse("events"))
        
        #Verificar creación
        event = Event.objects.get(title="Nuevo Evento Test")
        self.assertEqual(event.status, "ACTIVO")
        self.assertEqual(event.categories.count(), 2)
        
        #Reprogramar evento
        response = self.client.post(reverse("event_edit", args=[event.pk]), {
            "title": "Evento Reprogramado",
            "description": event.description,
            "date": event.scheduled_at.strftime("%Y-%m-%d"),
            "time": event.scheduled_at.strftime("%H:%M"),
            "status": "REPROGRAMADO",
            "new_date": (event.scheduled_at + timedelta(days=2)).strftime("%Y-%m-%d"),
            "new_time": "18:00",
            "max_capacity": 150,
            "categories": [self.category1.pk]
        })
        event.refresh_from_db()
        self.assertEqual(event.status, "REPROGRAMADO")
        self.assertIsNotNone(event.new_scheduled_at)
        self.assertEqual(event.categories.count(), 1)
        
        #Intentar editar estado de evento FINALIZADO 
        finished_event = self.events['finished']
        response = self.client.post(reverse("event_edit", args=[finished_event.pk]), {
            "title": finished_event.title,
            "description": finished_event.description,
            "date": finished_event.scheduled_at.strftime("%Y-%m-%d"),
            "time": finished_event.scheduled_at.strftime("%H:%M"),
            "status": "ACTIVO", 
            "max_capacity": finished_event.max_capacity
        }, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("no se puede modificar" in str(m).lower() for m in messages))
        
        #Finalizar evento 
        event.status = 'REPROGRAMADO' 
        event.new_scheduled_at = timezone.now() - timedelta(days=1)
        event.save()
        call_command("update_finished_events")
        event.refresh_from_db()
        self.assertEqual(event.status, "FINALIZADO")


