import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

#Autor: Buiatti Pedro Nazareno (agregar Notification y UserNotification)
from .models import Event, User, Notification, UserNotification 
from .forms import NotificationForm
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q
from django.db import transaction

def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect("events")

    return render(request, "accounts/login.html")


def home(request):
    return render(request, "home.html")


@login_required
def events(request):
    events = Event.objects.all().order_by("scheduled_at")
    return render(
        request,
        "app/events.html",
        {"events": events, "user_is_organizer": request.user.is_organizer},
    )


@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)
    return render(request, "app/event_detail.html", {"event": event})


@login_required
def event_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=id)
        event.delete()
        return redirect("events")

    return redirect("events")


@login_required
def event_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        if id is None:
            Event.new(title, description, scheduled_at, request.user)
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, scheduled_at, request.user)

        return redirect("events")

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    return render(
        request,
        "app/event_form.html",
        {"event": event, "user_is_organizer": request.user.is_organizer},
    )




#Autor: Buiatti Pedro Nazareno
#Para listar notificaciones
@login_required
def listNotifications(request):
    user = request.user
    detail_id = request.GET.get('detail_id')
    notifications = UserNotification.objects.filter(user=user).select_related('notification').order_by('-notification__created_at')

    eventId = request.GET.get('event_id')
    priority = request.GET.get('priority')
    searchQuery = request.GET.get('q', '').strip()
    
    if eventId:
        notifications = notifications.filter(notification__event__id=eventId)
    if priority:
        notifications = notifications.filter(notification__priority=priority)
    if searchQuery:
        notifications = notifications.filter(
            Q(notification__title__icontains=searchQuery) |
            Q(notification__message__icontains=searchQuery)
        )

    all_users_count = User.objects.count()
    notifications_data = []
    for user_notification in notifications:
        notification = user_notification.notification
        recipients_count = UserNotification.objects.filter(notification=notification).count()
        is_broadcast = recipients_count == all_users_count
        show_detail = str(user_notification.pk) == detail_id  
        
        notifications_data.append({
            'user_notification': user_notification,
            'is_broadcast': is_broadcast,
            'show_detail': show_detail  
        })

    numNotifications = notifications.filter(is_read=False).count()

    form = None
    if user.is_organizer:
        form = NotificationForm(user=user)

    context = {
        'notifications_data': notifications_data,
        'numNotifications': numNotifications,
        'is_organizer': user.is_organizer,
        'form': form,
        'events': Event.objects.filter(organizer=user) if user.is_organizer else None,
        'priorities': Notification.NotificationPriority.choices,
    }

    if not user.is_organizer:
        context['notificaciones'] = notifications

    return render(request, 'notification.html', context)

#Autor: Buiatti Pedro Nazareno
#Para crear una notificacion
@login_required
def createNotification(request):
    user = request.user
    if not user.is_organizer:
        return redirect('listNotifications')

    if request.method=="POST":
        form = NotificationForm(request.POST, user=user)
        if form.is_valid():
            notification = form.save(commit=False) #Guarda la instancia sin guardarla en la base aún
            notification.save() # Se guarda en la base con el usuario creador 

            recipient_type = request.POST.get('recipient_type')
            if recipient_type == 'all':
                users = User.objects.all()
            else:
                user_id = request.POST.get('recipient')
                users = User.objects.filter(id=user_id)

            UserNotification.objects.create(user=user, notification=notification, is_read=False)

            #Crear relacion para el usuario actual
            for recipient in users:
                if recipient and recipient != user:
                    UserNotification.objects.create(
                        user=recipient,
                        notification=notification,
                        is_read=False
                    )

            messages.success(request, "Notificación creada con éxito")
            return redirect('listNotifications')
    else:
        form = NotificationForm(user=user)
    return render(request, 'notificationForm.html', {'form': form, 'users': User.objects.all()})

#Autor: Buiatti Pedro Nazareno
#Para borrar una notificacion
@login_required
def deleteNotification(request, pk):
    user = request.user
    user_notification = get_object_or_404(UserNotification, pk=pk, user=user)

    if request.method == "POST":
        if user.is_organizer:
            notification = user_notification.notification
            notification.delete()
            messages.success(request, "La notificación ha sido eliminada para todos.")
        else:
            user_notification.is_read = True
            user_notification.save()
            messages.success(request, "La notificación ha sido marcada como leída.")

        return redirect('listNotifications')
    
    return redirect('listNotifications')

#Autor: Buiatti Pedro Nazareno
#Para editar una notificacion
@login_required
def updateNotification(request, pk): 

    if pk == 'all':
        UserNotification.objects.filter(user=request.user).update(is_read=True)
        messages.success(request, "Todas las notificaciones han sido marcadas como leídas.")
        return redirect('listNotifications')

    try:
        notification = Notification.objects.get(pk=pk)
        user_notification = UserNotification.objects.get(
            notification=notification,
            user=request.user
        )
    except (Notification.DoesNotExist, UserNotification.DoesNotExist):
        messages.error(request, "Notificación no encontrada o no tienes permisos")
        return redirect('listNotifications')
    
    if not request.user.is_organizer:
        if request.method == "POST":
            user_notification.is_read = True
            user_notification.save()
            messages.success(request, "Notificación marcada como leída.")
            return redirect('listNotifications')
        else:
            return redirect('listNotifications')

    total_users = User.objects.count()
    current_recipients = UserNotification.objects.filter(notification=notification).count()
    is_broadcast = current_recipients == total_users

    if request.method == "POST":
        form = NotificationForm(request.POST, instance=notification, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic(): 
                  
                    notification = form.save()
                    recipient_type = request.POST.get('recipient_type')
                    UserNotification.objects.filter(notification=notification).exclude(user=request.user).delete()

                    if recipient_type == 'all':
                        recipients = User.objects.exclude(id=request.user.id)
                        for recipient in recipients:
                            UserNotification.objects.get_or_create(
                                user=recipient,
                                notification=notification,
                                defaults={'is_read': False}
                            )
                        msg = "Notificación actualizada para todos los usuarios"
                    
                    elif recipient_type == 'specific':
                        recipient_id = request.POST.get('recipient')
                        if recipient_id:
                            try:
                                recipient = User.objects.get(id=recipient_id)
                                if recipient != request.user:
                                    UserNotification.objects.create(
                                        user=recipient,
                                        notification=notification,
                                        is_read=False
                                    )
                                msg = f"Notificación actualizada para {recipient.username}"
                            except User.DoesNotExist:
                                messages.error(request, "Usuario seleccionado no válido")
                                return render(request, 'notificationForm.html', {
                                    'form': form,
                                    'user_notification': user_notification,
                                    'users': User.objects.exclude(id=request.user.id),
                                    'is_broadcast': is_broadcast
                                })
            
                    messages.success(request, msg)
                    return redirect('listNotifications')
            except Exception as e:
                messages.error(request, f"Error al guardar cambios: {str(e)}")
                return redirect('listNotifications')
    else:
        initial_data = {
            'recipient_type': 'all' if is_broadcast else 'specific',
        }

        if not is_broadcast:
            specific = UserNotification.objects.filter(
                notification=notification
            ).exclude(user=request.user).select_related('user').first()
            if specific:
                initial_data['recipient'] = specific.user.pk  

        form = NotificationForm(instance=notification, user=request.user, initial=initial_data)

    return render(request, 'notificationForm.html', {
        'form': form,
        'user_notification': user_notification,
        'users': User.objects.exclude(id=request.user.id),
        'is_broadcast': is_broadcast
    })