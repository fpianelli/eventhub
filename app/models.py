from django.contrib.auth.models import AbstractUser
from django.db import models


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

