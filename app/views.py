import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Event, User, Comment, RefundRequest, Ticket
from django.views.decorators.http import require_POST


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

@login_required
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
