from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid


class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)

    @classmethod
    def validate_new_user(cls, email, username, password, password_confirm):
        errors = {}

        if email is None:
            errors["email"] = "El email es requerido"
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Ya existe un usuario con este email"

        if username is None:
            errors["username"] = "El username es requerido"
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Ya existe un usuario con este nombre de usuario"

        if password is None or password_confirm is None:
            errors["password"] = "Las contraseñas son requeridas"
        elif password != password_confirm:
            errors["password"] = "Las contraseñas no coinciden"

        return errors


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, description, scheduled_at):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer):
        errors = Event.validate(title, description, scheduled_at)

        if len(errors.keys()) > 0:
            return False, errors

        Event.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
        )

        return True, None

    def update(self, title, description, scheduled_at, organizer):
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer

        self.save()

class RefundRequest(models.Model):
    approved = models.BooleanField(null=True, default=None)
    approval_date = models.DateTimeField(null=True, blank=True)
    ticket_code = models.CharField(max_length=100, default="")
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refund_requests")
    def __str__(self):
        return f"RefundRequest {self.pk} - User: {self.client.username} - Ticket: {self.ticket_code} - Approved: {self.approved}"
    
    @classmethod
    def create_refund(cls, client, tC, reason):
        return cls.objects.create(
            client=client,
            ticket_code=tC,
            reason=reason,
            approved=None,
        )

    def cancel_refund(self):
        self.delete()
        

    def approve_refund(self):
        self.approved = True
        self.approval_date = timezone.now()
        self.save(update_fields=["approved", "approval_date"])

    def reject_refund(self):
        self.approved = False
        self.approval_date = None
        self.save(update_fields=["approved", "approval_date"])
    
    def edit_refund(self, tC, reason, client):
        self.ticket_code = tC or self.ticket_code
        self.reason = reason or self.reason
        self.client = client or self.client

        self.save(update_fields=["ticket_code", "reason", "client"])
    
     

    
    
        
class Ticket (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    buy_date = models.DateField(auto_now_add=True)
    type_ticket = models.CharField(
        max_length=50,
        choices=[("GENERAL", "General"), ("VIP", "VIP")]
        )
    ticket_code = models.CharField(max_length=100, unique=True, editable=False, default=uuid.uuid4)
    quantity = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event} - {self.user.username} - {self.type_ticket}"
    
    @classmethod
    def validate_ticket(cls, type_ticket, quantity):

        errors = {}

        if not type_ticket:
            errors["type_ticket"] = "El tipo de entrada es requerido"
        elif type_ticket not in dict(cls._meta.get_field('type_ticket').choices):
            errors["type_ticket"] = "El tipo de entrada no es válido"

        if quantity is None:
            errors["quantity"] = "La cantidad es requerida"
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    errors["quantity"] = "La cantidad debe ser mayor que cero"
            except ValueError:
                errors["quantity"] = "La cantidad debe ser un número entero válido"
        
        return errors

