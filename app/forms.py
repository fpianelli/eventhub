#Autor: Buiatti Pedro Nazareno
#Para manejar formularios

from django import forms
from .models import Notification, Event
from django.forms import ModelChoiceField
from django.db.models import QuerySet

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'priority', 'event']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control rounded',
                'placeholder': 'Ej: Cambio de horario del evento'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control rounded',
                'rows': 5,
                'placeholder': 'Escribe el contenido de la notificación...'
            }),
            'priority':forms.Select(attrs={
                'class': 'form-control rounded'
            }),
            'event': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        eventField = self.fields.get('event')
        if isinstance(eventField, forms.ModelChoiceField):
            if user and user.is_organizer:
                eventField.queryset = Event.objects.filter(organizer=user)
            else:
                eventField.queryset = Event.objects.none()
            


         