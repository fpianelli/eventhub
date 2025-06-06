# Generated by Django 5.2 on 2025-04-22 12:22

import uuid
from django.db import migrations, models

def generate_unique_codes(apps, schema_editor):
    Ticket = apps.get_model('app', 'Ticket')
    for ticket in Ticket.objects.all():
        ticket.ticket_code = str(uuid.uuid4())
        ticket.save()

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_ticket'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='price',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='seat',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='status',
        ),
        migrations.AddField(
            model_name='ticket',
            name='quantity',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='ticket',
            name='ticket_code',
            field=models.CharField(default=uuid.uuid4, editable=False, max_length=100, unique=True),
        ),
        migrations.RunPython(generate_unique_codes),
        migrations.AlterField(
            model_name='ticket',
            name='type_ticket',
            field=models.CharField(choices=[('GENERAL', 'General'), ('VIP', 'VIP')], max_length=50),
        ),
    ]
