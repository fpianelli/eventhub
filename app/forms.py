#Autor: Buiatti Pedro Nazareno
#Para manejar formularios

from django import forms
from .models import Notification

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'is_read', 'priority']
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
            })
        }


         