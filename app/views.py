import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

#Autor: Buiatti Pedro Nazareno (agregar Notification y UserNotification)
from .models import Event, User, Notification, UserNotification

#Autor: Buiatti Pedro Nazareno 
from .forms import NotificationForm


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
    notifications = UserNotification.objects.filter(user=request.user).order_by('-notification__created_at')
    numNotifications = notifications.filter(is_read=False).count()
    return render(request, 'notification.html', {
        'notificaciones': notifications,
        'numNotifications': numNotifications
    })

#Autor: Buiatti Pedro Nazareno
#Para crear una notificacion
@login_required
def createNotification(request):
    if request.method=="POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save()

            #Crear relacion para el usaurio actual
            UserNotification.objects.create(
                user=request.user,
                notification=notification,
                is_read=False
            )

            return redirect('listNotifications')
    else:
        form = NotificationForm()
    return render(request, 'notification.html', {'form': form})

#Autor: Buiatti Pedro Nazareno
@login_required
def deleteNotification(request, pk):
    userNotification = get_object_or_404(UserNotification, pk=pk, user=request.user)
    if request.method == "POST":
        userNotification.delete()
        return redirect('listNotifications')
    return render(request, 'notification.html', {
        'notificacion': userNotification.notfication
    })

#Autor: Buiatti Pedro Nazareno
@login_required
def updateNotification(request, pk):
    userNotification = get_object_or_404(UserNotification, pk=pk, user=request.user)
    notification = userNotification.notfication
    if request.method=="POST":
        form = NotificationForm(request.POST, instance=notification)
        if form.is_valid():
            form.save()
            return redirect('listNotifications')
        else:
            form = NotificationForm(instance=notification)
        return render(request, 'notification.html', {'form': form})





