#Autor: Buiatti Pedro Nazareno

from django import forms
from .models import Notification

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'message', 'is_read', 'priority']