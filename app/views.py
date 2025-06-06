import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Event, User, Comment, RefundRequest, Ticket, Category, Notification, UserNotification, TicketDiscount
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import NotificationForm, TicketDiscountForm
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ValidationError

from django.http import JsonResponse



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
    errors = {}

    #Calcular cuenta regresiva para usuarios no organizadores
    countdown = None
    if not request.user.is_organizer:
        countdown = event.get_countdown()

    #Eliminar comentario
    if "delete_comment" in request.POST:
        comment_id = request.POST.get("comment_id")
        comment = get_object_or_404(Comment, pk=comment_id)
        if comment.user == request.user:
            comment.delete()
            messages.success(request, "Comentario eliminado correctamente")
        return redirect("event_detail", id=id)

    #Editar comentario
    edit_comment = None
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "edit_comment":  #Guardar edición
            comment_id = request.POST.get("comment_id")
            comment = get_object_or_404(Comment, pk=comment_id)
            if comment.user == request.user:
                title = request.POST.get("title", "").strip() #Valor por defecto vacío
                text = request.POST.get("text", "").strip() #Valor por defecto vacío

                #Validar campos title y text
                errors = Comment.validate(title, text)

                if not errors:  #Si no hay errores
                    comment.title = title
                    comment.text = text
                    comment.save()
                    messages.success(request, "Comentario actualizado correctamente")
                    return redirect("event_detail", id=id)
                else:
                    #Si hay errores, mantenemos el comentario en edición
                    edit_comment = comment
                    for field, message in errors.items():
                        messages.error(request, f"{field}: {message}")

        #Crear nuevo comentario
        elif form_type == "new_comment":
            title = request.POST.get("title", "").strip()
            text = request.POST.get("text", "").strip()

            #Validar campos title y text
            errors = Comment.validate(title, text)

            if not errors:
                Comment.objects.create(
                    title=title,
                    text=text,
                    event=event,
                    user=request.user
                )
                messages.success(request, "Comentario creado correctamente")
                return redirect("event_detail", id=id)
            else:
                for field, message in errors.items():
                    messages.error(request, f"{field}: {message}")

    #Carga comentario para editar
    edit_comment_id = request.GET.get("edit_comment")
    if edit_comment_id:
        edit_comment = get_object_or_404(Comment, pk=edit_comment_id)
        if edit_comment.user != request.user:
            messages.error(request, "No tienes permiso para editar este comentario")
            return redirect("event_detail", id=id)

    return render(request, "app/event_detail.html", {
        "event": event,
        "comments": comments,
        "edit_comment": edit_comment,
        "errors": errors,
        "user_is_organizer": request.user.is_organizer,
        "countdown": countdown
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

        #AUTOR: Buiatti Pedro Nazareno
        status = request.POST.get("status")
        new_date = request.POST.get("new_date")
        new_time = request.POST.get("new_time")
        max_capacity = request.POST.get("max_capacity", 100)
        try:
            max_capacity = int(max_capacity)
        except ValueError:
            messages.error(request, 'La capacidad máxima debe ser un número entero válido (ej: 100, 200)')
            return redirect('event_edit', id=id) if id else redirect('event_form')

        #AUTOR: Buiatti Pedro Nazareno
        if status == 'REPROGRAMADO' and (not new_date or not new_time):
            messages.error(request, "Debe ingresar fecha y hora para reprogramar un evento")
            return redirect('event_edit', id=id) if id else redirect('event_form')

        #AUTOR: Buiatti Pedro Nazareno
        new_scheduled_at = None
        if status == 'REPROGRAMADO' and new_date and new_time:
            [new_year, new_month, new_day] = new_date.split("-")
            [new_hour, new_minutes] = new_time.split(":")
            new_scheduled_at = timezone.make_aware(
                datetime.datetime(int(new_year), int(new_month), int(new_day), int(new_hour), int(new_minutes))
            )

        #AUTOR: Buiatti Pedro Nazareno
        if status != 'REPROGRAMADO':
            new_scheduled_at = None

        #AUTOR: Buiatti Pedro Nazareno
        allowed_statuses = ['ACTIVO', 'CANCELADO', 'REPROGRAMADO']
        if status not in allowed_statuses:
            messages.error(request, "Estado no permitido")
            return redirect('event_edit', id=id) if id else redirect('event_form')

        if id is None:
            event = Event.objects.create(
                title=title,
                description=description,
                scheduled_at=scheduled_at,
                organizer=request.user,

                #AUTOR: Buiatti Pedro Nazareno
                max_capacity= max_capacity,
                status='ACTIVO',
                new_scheduled_at=new_scheduled_at

            )

            for category_id in selected_categories:
                category = Category.objects.get(id=category_id)
                category.events.add(event)

            return redirect("events")
        else:
            event = get_object_or_404(Event, pk=id)
            event.title = title
            event.description = description
            event.scheduled_at = scheduled_at
            event.organizer = request.user

            #AUTOR: Buiatti Pedro Nazareno
            event.status = status
            event.new_scheduled_at = new_scheduled_at

            #AUTOR: Buiatti Pedro Nazareno (editado, antes estaba solo el event.save())
            try:
                event.save()  
                event.categories.clear()
                for category_id in selected_categories:
                    category = Category.objects.get(id=category_id)
                    category.events.add(event)
                return redirect("events")
            except ValidationError as e:
                messages.error(request, str(e))  
                return redirect('event_edit', id=id)

        

    event = None
    selected_category_ids = []
    if id is not None:
        event = get_object_or_404(Event, pk=id)
        selected_category_ids = event.categories.values_list('id', flat=True)


    #AUTOR: Buiatti Pedro Nazareno
    status_choices = [
        ('ACTIVO', 'Activo'),
        ('CANCELADO', 'Cancelado'),
        ('REPROGRAMADO', 'Reprogramado')
    ]
    
    # Si el evento ya está AGOTADO o FINALIZADO, mostramos el estado como texto
    if event and event.status in ['AGOTADO', 'FINALIZADO']:
        readonly_status = True
    else:
        readonly_status = False

    return render(
        request,
        "app/event_form.html",
        {
            "event": event,
            "categories": categories,
            "selected_category_ids": selected_category_ids,
            "user_is_organizer": request.user.is_organizer,

            #AUTOR: Buiatti Pedro Nazareno
            "status_choices": status_choices,
            'readonly_status': readonly_status,
            'current_status': event.status if event else None
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
        messages.error(request, "No tienes permisos para acceder a esta página")
        return redirect('events')

    #Eliminar comentario
    if request.method == "POST" and "delete_comment" in request.POST:
        comment_id = request.POST.get("comment_id")
        comment = get_object_or_404(Comment, pk=comment_id)

        #Verificar que el comentario pertenece a un evento del organizador
        if comment.event.organizer != request.user:
            messages.error(request, "No tienes permiso para eliminar este comentario")
            return redirect("my_events_comments")

        comment.delete()
        messages.success(request, "Comentario eliminado correctamente")
        return redirect("my_events_comments")

    #Obtener todos los comentarios de los eventos del organizador
    comments = Comment.objects.filter(event__organizer=request.user).select_related('event', 'user').order_by('-created_at')

    return render(request, "app/my_events_comments.html", {
        "comments": comments,
        "user_is_organizer": request.user.is_organizer
    })
#AMB DE REFUND REQUESTS

# def is_pending(client_id):
#     request = RefundRequest.objects.filter(client__pk = client_id)
#     pending = any(r.approved is None for r in request)
#     return pending

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
    errors = {}
    tickets = Ticket.objects.filter(user=client)
    if id is not None:
        rr = get_object_or_404(RefundRequest, pk=id)
        client2 = get_object_or_404(User, id=rr.client.pk)
        tickets = Ticket.objects.filter(user=client2)
    else: 
        if client and RefundRequest.is_pending(client.pk):
            return redirect("refund_requests")
    
    if request.method == "POST":
        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")

        errors = RefundRequest.validate(ticket_code, reason, client)


        if len(errors) > 0:
            return render(
                request,
                "refundRequest/refund_form.html",
                {
                    "rr": rr,
                    "errors": errors,
                    "data": request.POST,
                    "user_is_organizer": request.user.is_organizer,
                },
            )

        if not id:
            rr = RefundRequest.create_refund(client, ticket_code, reason)
            if approval:
                rr.approve_refund()
            return redirect('refund_detail', id=rr.pk)
        else:
            rr = get_object_or_404(RefundRequest, pk=id)
            rr.edit_refund(ticket_code, reason, client2)
            return redirect('refund_detail', id=rr.pk)

    return render(
        request,
        "refundRequest/refund_form.html",
        {"rr": rr, "user_is_organizer": request.user.is_organizer, "tickets": tickets},
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

    #AUTOR: Buiatti Pedro Nazareno 
    if event.status == 'AGOTADO':
        messages.error(request, "Las entradas para este evento están agotadas.")
        return redirect('event_detail', id=event_id)

    #AUTOR: Buiatti Pedro Nazareno 
    if event.status in ['CANCELADO', 'FINALIZADO', 'AGOTADO']:
        messages.error(request, "No se pueden comprar entradas para este evento")
        return redirect('event_detail', id=event_id)
    

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
        
        #AUTOR: Buiatti Pedro Nazareno 
        if (event.tickets_sold + int(quantity)) > event.max_capacity:
            messages.error(request, f"No hay suficientes entradas disponibles. Solo quedan {event.max_capacity - event.tickets_sold} entradas.")
            return render(request, "app/ticket_form.html", {
                'event': event,
                'errors': {'quantity': 'Cantidad no disponible'},
                'data': request.POST,
                'id_edit': False,
            })

        ticket = Ticket(
            user=request.user,
            type_ticket=type_ticket,
            quantity=int(quantity),
            event=event
        )
        ticket.save()

        #AUTOR: Buiatti Pedro Nazareno
        event.refresh_from_db()
        event.save()

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



class OrganizerRequiredMixin(AccessMixin):
    """Evita que el usuario no organizador acceda, sin mostrar errores ni mensajes."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, 'is_organizer', False):
            # Redirige silenciosamente a la página anterior
            referer = request.META.get('HTTP_REFERER', '/')
            return redirect(referer)

        return super().dispatch(request, *args, **kwargs)

class OrganizerContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_is_organizer"] = getattr(self.request.user, "is_organizer", False)
        return context


class TicketDiscountListView(LoginRequiredMixin, OrganizerContextMixin, OrganizerRequiredMixin, ListView):
    model = TicketDiscount
    template_name = 'app/ticketdiscount_list.html'



class TicketDiscountCreateView(LoginRequiredMixin, OrganizerContextMixin, OrganizerRequiredMixin, CreateView):
    model = TicketDiscount
    form_class = TicketDiscountForm
    template_name = 'app/ticketdiscount_form.html'
    success_url = reverse_lazy('ticketdiscount_list')

class TicketDiscountUpdateView(LoginRequiredMixin, OrganizerContextMixin, OrganizerRequiredMixin, UpdateView):
    model = TicketDiscount
    form_class = TicketDiscountForm
    template_name = 'app/ticketdiscount_form.html'
    success_url = reverse_lazy('ticketdiscount_list')

class TicketDiscountDeleteView(LoginRequiredMixin, OrganizerContextMixin, OrganizerRequiredMixin, DeleteView):
    model = TicketDiscount
    template_name = 'app/ticketdiscount_confirm_delete.html'
    success_url = reverse_lazy('ticketdiscount_list')


def validate_ticket(request):
    code = request.GET.get('code')

    if not code:
        return JsonResponse({'valid': False, 'message': 'Datos incompletos'}, status=400)

    try:
        descuento = TicketDiscount.objects.get(code=code)
        return JsonResponse({
            'valid': True,
            'discount_percent': descuento.percentage,
            'message': f'Cupón aplicado: {descuento.percentage}% de descuento'
        })
    except TicketDiscount.DoesNotExist:
        return JsonResponse({'valid': False, 'message': 'Código inválido'})



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

    specific_recipient = None
    if not is_broadcast:
        specific_notification = UserNotification.objects.filter(
            notification=notification
        ).exclude(user=request.user).select_related('user').first()
        if specific_notification:
            specific_recipient = specific_notification.user

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

        
        if specific_recipient:
            initial_data['recipient'] = specific_recipient.pk



        form = NotificationForm(
            instance=notification, 
            user=request.user, 
            initial=initial_data
        )

    return render(request, 'notificationForm.html', {
        'form': form,
        'user_notification': user_notification,
        'users': User.objects.exclude(id=request.user.id),
        'is_broadcast': is_broadcast,
        'specific_recipient': specific_recipient
    })
