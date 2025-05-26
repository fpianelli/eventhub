from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Event

class Command(BaseCommand):
    help = 'Actualiza automáticamente el estado de eventos pasados a FINALIZADO'

    def handle(self, *args, **options):
        now = timezone.now()
        updated = Event.objects.filter(
            scheduled_at__lt=now,
            status__in=['ACTIVO', 'REPROGRAMADO', 'AGOTADO']
        ).update(status='FINALIZADO')
        
        self.stdout.write(self.style.SUCCESS(f'Actualizados {updated} eventos a FINALIZADO'))


#crontab -e 
# 0 0 * * * /venv/bin/python /eventhub/manage.py update_finished_events (configuracion, mas o menos)

# python manage.py test app.test.test_unit.test_event_status

