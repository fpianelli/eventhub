from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.urls import reverse
from django.contrib.messages import get_messages
from app.models import Event, User, Ticket

class EventStatusTest(TestCase):
    def setUp(self):
        """Configuración inicial para todas las pruebas"""
        self.organizer = User.objects.create_user(
            username="organizer_test",
            email="organizer@example.com",
            password="password123",
            is_organizer=True,
        )
        
        now = timezone.now()
        
        self.event_1 = Event.objects.create(
            title="Evento ACTIVO",
            description="Evento en estado ACTIVO",
            scheduled_at=now + timedelta(days=2),
            organizer=self.organizer,
            max_capacity=100,
            status="ACTIVO"
        )
        
        self.event_2 = Event.objects.create(
            title="Evento AGOTADO",
            description="Evento en estado AGOTADO",
            scheduled_at=now + timedelta(days=3),
            organizer=self.organizer,
            max_capacity=50,
            status="AGOTADO"
        )
        
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
        
        self.events = {
            'active': self.event_1,
            'sold_out': self.event_2,
            'canceled': self.event_3,
            'finished': self.event_4
        }



    def test_auto_sold_out_status(self):
        """Verifica que el estado cambie a AGOTADO al alcanzar la capacidad máxima"""
        event = self.events['active']
        
        Ticket.objects.create(
            event=event,
            user=self.organizer,
            quantity=event.max_capacity,
            type_ticket="General"
        )
        
        event.refresh_from_db()
        event.save()
        
        self.assertEqual(event.status, "AGOTADO")
        self.assertTrue(event.is_sold_out)


    def test_reprogrammed_event_requires_new_date(self):
        """Verifica que no se pueda reprogramar sin nueva fecha"""
        event = self.events['active']
        event.status = "REPROGRAMADO"
        
        with self.assertRaises(ValidationError) as context:
            event.clean()
            
        self.assertIn("new_scheduled_at", context.exception.message_dict)

    def test_auto_finalized_status(self):
        """Verifica que eventos pasados se marquen como FINALIZADO al guardar"""
        past_event = Event.objects.create(
            title="Evento Pasado",
            description="Evento para test FINALIZADO",
            scheduled_at=timezone.now() - timedelta(days=1),
            organizer=self.organizer,
            max_capacity=100,
            status="ACTIVO"
        )
        past_event.save()
        
        self.assertEqual(past_event.status, "FINALIZADO")

    def test_cron_job_finalizes_events(self):
        """Verifica el comando de actualización de eventos finalizados"""
        from django.core.management import call_command
        
        event = Event.objects.create(
            title="Evento para CRON",
            description="Test comando CRON",
            scheduled_at=timezone.now() - timedelta(days=1),
            organizer=self.organizer,
            max_capacity=100,
            status="ACTIVO"
        )
        
        call_command("update_finished_events")
        event.refresh_from_db()
        
        self.assertEqual(event.status, "FINALIZADO")

    def test_readonly_finalized_status(self):
        """Verifica que no se pueda modificar un evento FINALIZADO"""
        event = self.events['finished']
        
        with self.assertRaises(ValidationError) as context:
            event.status = "ACTIVO"
            event.clean()
            
        self.assertIn("No se puede modificar", str(context.exception))

  