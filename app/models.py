from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

#AUTOR: Buiatti Pedro Nazareno
from django.db.models import Sum
from django.core.exceptions import ValidationError

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

    #AUTOR: Buiatti Pedro Nazareno
    STATUS_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('CANCELADO', 'Cancelado'),
        ('REPROGRAMADO', 'Reprogramado'),
        ('AGOTADO', 'Agotado'), 
        ('FINALIZADO', 'Finalizado'),
    ]

    #AUTOR: Buiatti Pedro Nazareno
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        blank=True,
        default='ACTIVO'
    )

    #AUTOR: Buiatti Pedro Nazareno
    max_capacity = models.PositiveBigIntegerField(default=100)
    new_scheduled_at = models.DateTimeField(null=True, blank=True) 


    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    #AUTOR: Buiatti Pedro Nazareno
    @property
    def tickets_sold(self):
        if not self.pk:
            return 0
        return self.ticket_set.aggregate(total=Sum('quantity'))['total'] or 0

    #AUTOR: Buiatti Pedro Nazareno
    @property
    def available_tickets(self):
        return self.max_capacity - self.tickets_sold

    #AUTOR: Buiatti Pedro Nazareno
    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.max_capacity
    
    #AUTOR: Buiatti Pedro Nazareno
    def clean(self):
        errors = {}
        if self.status == 'REPROGRAMADO' and not self.new_scheduled_at:
            errors['new_scheduled_at'] = 'Debe ingresar una nueva fecha para reprogramación'
        
        if self.pk:
            original = Event.objects.get(pk=self.pk)
            if original.status in ['AGOTADO', 'FINALIZADO'] and self.status != original.status:
                errors['status'] = 'No se puede modificar este estado'
        
        if not isinstance(self.max_capacity, int):
            errors["max_capacity"] = "La capacidad máxima debe ser un número entero."

        if self.status == 'AGOTADO' and self.tickets_sold < self.max_capacity:
            errors['status'] = 'No se puede marcar como AGOTADO si no se alcanzó la capacidad máxima'

        if errors:
            raise ValidationError(errors)
    
    #AUTOR: Buiatti Pedro Nazareno
    def save(self, *args, **kwargs):
        now = timezone.now()
        original_status = None
        if self.pk:
            original = Event.objects.get(pk=self.pk)
            original_status = original.status

        if original_status in ['AGOTADO', 'FINALIZADO']:
            if self.status != original_status:
                raise ValidationError("Evento AGOTADO/FINALIZADO no se puede modificar")

        relevant_date = self.new_scheduled_at if self.status == 'REPROGRAMADO' else self.scheduled_at

        new_status = self.status
        if self.tickets_sold >= self.max_capacity:
            new_status = 'AGOTADO'
        elif relevant_date and relevant_date < now:
            new_status = 'FINALIZADO'

        self.status = new_status

        super().save(*args, **kwargs)


    #AUTOR: Buiatti Pedro Nazareno (agregar parametros status=None, new_scheduled_at=None)
    @classmethod
    def validate(cls, title, description, scheduled_at, status=None, new_scheduled_at=None):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        #AUTOR: Buiatti Pedro Nazareno
        if status == 'REPROGRAMADO' and not new_scheduled_at:
            errors["new_scheduled_at"] = "Debe ingresar una nueva fecha para eventos reprogramados"
        
        return errors

    #AUTOR: Buiatti Pedro Nazareno (agregar parametro max_capacity=100)
    @classmethod
    def new(cls, title, description, scheduled_at, organizer, max_capacity=100):
        errors = Event.validate(title, description, scheduled_at)

        #AUTOR: Buiatti Pedro Nazareno
        try:
            max_capacity = int(max_capacity)  
        except (ValueError, TypeError):
            errors["max_capacity"] = "Capacidad máxima debe ser un número válido."
        
        #AUTOR: Buiatti Pedro Nazareno
        if errors:
            return False, errors

        Event.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,

            #AUTOR: Buiatti Pedro Nazareno
            max_capacity=max_capacity

        )

        return True, None
    
    #AUTOR: Buiatti Pedro Nazareno (agregar status, new_scheduled_at=None)
    def update(self, title, description, scheduled_at, organizer, status, new_scheduled_at=None):
        
        #AUTOR: Buiatti Pedro Nazareno
        allowed_statuses = ['ACTIVO', 'CANCELADO', 'REPROGRAMADO']
        if status not in allowed_statuses:
            raise ValidationError("Estado no permitido")
        
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer

        #AUTOR: Buiatti Pedro Nazareno
        self.status = status
        self.new_scheduled_at = new_scheduled_at if status == 'REPROGRAMADO' else None
    
        self.clean()
        self.save()




class Category(models.Model):
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=300)
    is_active = models.BooleanField()

    events = models.ManyToManyField('Event', related_name="categories")  # ← corregido

    def __str__(self):
        return self.name

    @classmethod
    def validate(cls, name, description):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese un nombre"
        elif name.isnumeric():
            errors["name"] = "El nombre no puede ser solo numeros"
        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        return errors

    @classmethod
    def new(cls, name, description, is_active):
        errors = Category.validate(name, description)

        if len(errors.keys()) > 0:
            return False, errors

        Category.objects.create(
            name=name,
            description=description,
            is_active=is_active,
        )

        return True, None

    def update(self, name, description, is_active):
        if name != "":
            self.name = name
        if description != "":
            self.description = description
        self.is_active = is_active  # <- Siempre asignar directamente

        self.save()
class Comment(models.Model):
    title= models.CharField(max_length=100)
    text= models.TextField()
    created_at= models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    #Validacion de los campos del comentario

    @classmethod
    def validate(cls, title, text):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un título"

        if text == "":
            errors["text"] = "Por favor ingrese un comentario"

        if len(title) > 100:
            errors["title"] = "El título no puede exceder los 100 caracteres"
            
        return errors

    #Metodo para crear un comentario

    @classmethod
    def new(cls, title, text, event, user):
        errors = Comment.validate(title, text)

        if len(errors.keys()) > 0:
            return False, errors

        Comment.objects.create(
            title=title,
            text=text,
            event=event,
            user=user,
        )

        return True, None

    #Metodo para actualizar un comentario
    # def update(self, title, text, event, user):
    #     self.title = title or self.title
    #     self.text = text or self.text
    #     self.event = event or self.event
    #     self.user = user or self.user

    #     self.save()
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
    def validate(cls, tC, reason, client):
        errors = {}

        if tC == "":
            errors["ticket_code"] = "Por favor ingrese el codigo del ticket a reembolsar"
        if reason == "":
            errors["reason"] = "Por favor ingrese la razon del reembolso"
        if client is None:
            errors["client"] = "Error al recuperar el cliente"
        return errors

    @classmethod
    def create_refund(cls, client, tC, reason):
        errors = RefundRequest.validate(tC, reason, client)
        if len(errors.keys()) > 0:
            return False, errors
    
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
        errors = RefundRequest.validate(tC, reason, client)
        if len(errors.keys()) > 0:
            return False, errors
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


#Autor: Buiatti Pedro Nazareno
#Modelo de notificacion
class Notification(models.Model):
    #Modelo de prioridad de la notificacion
    #Clase interna de conocimiento para Notificacion
    class NotificationPriority(models.TextChoices):
        HIGH = "HIGH", "Alta"
        MEDIUM = "MEDIUM", "Media"
        LOW = "LOW", "Baja"

    title = models.CharField(max_length=250)
    message = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.LOW
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL, #si se borra el evento, la notificación no se borra
        null=True, #permite que sea nulo
        blank=True, #campo vacío permitido en formularios
        related_name='notifications' #nombree para la relacion inversa
    )

    def __str__(self):
        return f"{self.title} - Creada el {self.created_at}"
    

#Autor: Buiatti Pedro Nazareno
#Modelo para intermedia entre Notificacion y Usuario
class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_notifications")
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="user_notifications")
    is_read = models.BooleanField(default=False) 

    def __str__(self):
        return f"Notificación: {self.notification.title} - Usuario_ {self.user.username}"

