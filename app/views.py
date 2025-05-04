import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Event, User, Comment, RefundRequest, Ticket, Category, Notification, UserNotification 
from django.views.decorators.http import require_POST

#Autor: Buiatti Pedro Nazareno (agregar Notification y UserNotification)
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
    comments = event.comments.all().order_by("-created_at")

    #Eliminar comentario
    if "delete_comment" in request.POST:
        comment_id = request.POST.get("comment_id")
        comment = get_object_or_404(Comment, pk=comment_id)
        if comment.user == request.user:
            comment.delete()
        return redirect("event_detail", id=id)

    #Editar comentario
    edit_comment = None
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "edit_comment":  #Guardar edición
            comment_id = request.POST.get("comment_id")
            comment = get_object_or_404(Comment, pk=comment_id)
            if comment.user == request.user:
                comment.title = request.POST.get("title")
                comment.text = request.POST.get("text")
                comment.save()
            return redirect("event_detail", id=id)

        #Crear nuevo comentario
        elif form_type == "new_comment":
            title = request.POST.get("title")
            text = request.POST.get("text")
            Comment.objects.create(
                title=title,
                text=text,
                event=event,
                user=request.user
            )
            return redirect("event_detail", id=id)

    #Carga comentario para editar
    edit_comment_id = request.GET.get("edit_comment")
    if edit_comment_id:
        edit_comment = get_object_or_404(Comment, pk=edit_comment_id)
        if edit_comment.user != request.user:
            return redirect("event_detail", id=id)

    return render(request, "app/event_detail.html", {
        "event": event,
        "comments": comments,
        "edit_comment": edit_comment,
        "user_is_organizer": request.user.is_organizer
    })

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

    categories = Category.objects.filter(is_active=True).order_by("id")

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")
        selected_categories = request.POST.getlist("categories")  # ← captura los checkboxes

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        if id is None:
            event = Event.objects.create(
                title=title,
                description=description,
                scheduled_at=scheduled_at,
                organizer=request.user,
            )
        else:
            event = get_object_or_404(Event, pk=id)
            event.title = title
            event.description = description
            event.scheduled_at = scheduled_at
            event.organizer = request.user
            event.save()

            # Si es edición, limpiamos categorías anteriores
            event.categories.clear()

        # Ahora asociamos las categorías seleccionadas
        for category_id in selected_categories:
            category = Category.objects.get(id=category_id)
            category.events.add(event)

        return redirect("events")

    event = {}
    selected_category_ids = []
    if id is not None:
        event = get_object_or_404(Event, pk=id)
        selected_category_ids = event.categories.values_list('id', flat=True)

    return render(
        request,
        "app/event_form.html",
        {
            "event": event,
            "categories": categories,
            "selected_category_ids": selected_category_ids,
            "user_is_organizer": request.user.is_organizer,
        },
    )

@login_required
def categories(request):

    categories = Category.objects.order_by("id")

    return render(
        request,
        "app/categories.html",
        {"categories": categories, "user_is_organizer": request.user.is_organizer},
    )

@login_required
def category_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("categories")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"


        if id is None:
            Category.new(name, description, is_active)
        else:
            category = get_object_or_404(Category, pk=id)
            category.update(name, description, is_active)

        return redirect("categories")

    category = {}
    if id is not None:
        category = get_object_or_404(Category , pk=id)

    return render(
        request,
        "app/category_form.html",
        {"category": category, "user_is_organizer": request.user.is_organizer},
    )

@login_required
def category_detail(request, id):
    category = get_object_or_404(Category, pk=id)
    return render(request, "app/category_detail.html", {"category": category})

@login_required
def category_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("categories")

    if request.method == "POST":
        category = get_object_or_404(Category, pk=id)
        category.delete()
        return redirect("categories")

    return redirect("categories")

def my_events_comments(request):
    if not request.user.is_organizer:
        return redirect('events')

    #Eliminar comentario
    if request.method == "POST" and "delete_comment" in request.POST:
        comment_id = request.POST.get("comment_id")
        comment = get_object_or_404(Comment, pk=comment_id)

        #Verificar que el comentario pertenece a un evento del organizador
        if comment.event.organizer == request.user:
            comment.delete()
            return redirect("my_events_comments")

    #Obtener todos los comentarios de los eventos del organizador
    comments = Comment.objects.filter(event__organizer=request.user).select_related('event', 'user').order_by('-created_at')

    return render(request, "app/my_events_comments.html", {
        "comments": comments,
        "user_is_organizer": request.user.is_organizer
    })
#AMB DE REFUND REQUESTS
@login_required
def refund_requests(request):
    rr = RefundRequest.objects.all().order_by("created_at")
    if request.user.is_organizer:
        return render(
        request,
        "refundRequest/refunds_organizer.html",
        {"refunds": rr, "user_is_organizer": request.user.is_organizer},
        )
    else:
        return render(
        request,
        "refundRequest/refunds.html",
        {"refunds": rr, "user_is_organizer": request.user.is_organizer, "user": request.user},
        )
@login_required
def refund_detail(request, id):
    rr = get_object_or_404(RefundRequest, pk=id)
    return render(request, "refundRequest/refund_detail.html", {"refund": rr, "user_is_organizer": request.user.is_organizer})

@login_required
def refund_delete(request, id=None):
    if request.method == "POST":
        rr = get_object_or_404(RefundRequest, pk=id)
        rr.delete()
        return redirect("refund_requests")
    return redirect("refund_requests")

@login_required
def refund_approve(request, id):
    if request.user.is_organizer:
        if request.method == "POST":
            rr = get_object_or_404(RefundRequest, pk=id)
            rr.approve_refund()
        return redirect("refund_requests")
    else:
        return redirect("refund_requests")

@login_required
def refund_reject(request, id):
    if request.user.is_organizer:
        if request.method == "POST":
            rr = get_object_or_404(RefundRequest, pk=id)
            rr.reject_refund()
        return redirect("refund_requests")
    else:
        return redirect("refund_requests")

@login_required
def refund_form(request, id=None, approval=False):
    client = request.user
    rr = None
    if id is not None:
        rr = get_object_or_404(RefundRequest, pk=id)

    if request.method == "POST":
        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")

        if not id:
            rr = RefundRequest.create_refund(client, ticket_code, reason)
            if approval:
                rr.approve_refund()
            return redirect('refund_detail', id=rr.pk)
        else:
            rr = get_object_or_404(RefundRequest, pk=id)
            rr.edit_refund(ticket_code, reason, client)
            return redirect('refund_detail', id=rr.pk)
    return render(
        request,
        "refundRequest/refund_form.html",
        {"rr": rr, "user_is_organizer": request.user.is_organizer},
    )



@login_required
def ticket_detail(request):
    if request.user.is_organizer:
        tickets = Ticket.objects.filter(event__organizer=request.user).order_by("buy_date")
    else:
        tickets = Ticket.objects.filter(user=request.user).order_by("buy_date")
    return render(request, "app/ticket_detail.html", {"tickets": tickets, "is_organizer": request.user.is_organizer,})

@login_required
def ticket_form(request, event_id):

    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':

        type_ticket = request.POST.get('type_ticket')
        quantity = request.POST.get('quantity')

        errors = Ticket.validate_ticket(type_ticket, quantity)

        if len(errors) > 0:
            return render(request, "app/ticket_form.html", {
                'event': event,
                'errors': errors,
                'data': request.POST,
                'is_edit': False,
            })

        ticket = Ticket(
            user=request.user,
            type_ticket=type_ticket,
            quantity=int(quantity),
            event=event
        )
        ticket.save()
        return redirect('ticket_detail')
    return render(request, "app/ticket_form.html", {'event': event, 'ticket': None, 'is_edit': False, 'data': {}, 'errors': {},})

@login_required
def ticket_edit(request, ticket_id):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':

        type_ticket = request.POST.get('type_ticket')
        quantity = request.POST.get('quantity')

        errors = Ticket.validate_ticket(type_ticket, quantity)

        if len(errors) > 0:
            return render(request, "app/ticket_form.html", {
                'ticket': ticket,
                'event': ticket.event,
                'errors': errors,
                'data': request.POST,
                'is_edit': True,
            })

        ticket.type_ticket = type_ticket
        ticket.quantity = int(quantity)
        ticket.save()
        return redirect('ticket_detail')
    else:
        return render(request, 'app/ticket_form.html', {
            'ticket': ticket,
            'event': ticket.event,
            'is_edit': True,
            'data': {},
            'errors': {},
        })


@require_POST
@login_required
def ticket_delete(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    return redirect('ticket_detail')


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
