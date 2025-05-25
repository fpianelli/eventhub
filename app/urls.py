from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

from .views import (
    TicketDiscountListView,
    TicketDiscountCreateView,
    TicketDiscountUpdateView,
    TicketDiscountDeleteView,
)

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", views.login_view, name="login"),
    path("events/", views.events, name="events"),
    path("events/create/", views.event_form, name="event_form"),
    path("events/<int:id>/edit/", views.event_form, name="event_edit"),
    path("events/<int:id>/", views.event_detail, name="event_detail"),
    path("events/<int:id>/delete/", views.event_delete, name="event_delete"),
    path("categories/", views.categories, name="categories"),
    path("categories/create/", views.category_form, name="category_form"),
    path("categories/<int:id>/edit/", views.category_form, name="category_edit"),
    path("categories/<int:id>/", views.category_detail, name="category_detail"),
    path("categories/<int:id>/delete/", views.category_delete, name="category_delete"),
    path('my-events-comments/', views.my_events_comments, name='my_events_comments'),
    path("refunds/", views.refund_requests, name="refund_requests"),
    path("refunds/create/", views.refund_form, name="refund_form"),
    path("refunds/<int:id>/edit/", views.refund_form, name="refund_edit"),
    path("refunds/<int:id>/approve/", views.refund_approve, name="refund_approve"),
    path("refunds/<int:id>/reject/", views.refund_reject, name="refund_reject"),
    path("refunds/<int:id>/", views.refund_detail, name="refund_detail"),
    path("refunds/<int:id>/delete/", views.refund_delete, name="refund_delete"),
    path("tickets/", views.ticket_detail, name="ticket_detail"),
    path('tickets/<int:ticket_id>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:ticket_id>/delete/', views.ticket_delete, name='ticket_delete'),
    path('events/<int:event_id>/buy_tickets/', views.ticket_form, name='ticket_form'),

    #Autor: Buiatti Pedro Nazareno
    path('notification', views.listNotifications, name='listNotifications'),
    path('notification/create/', views.createNotification, name='createNotification'),
    path('notification/update/<pk>/', views.updateNotification, name='updateNotification'),
    path('notification/delete/<int:pk>/', views.deleteNotification, name='deleteNotification'),

    path('ticketdiscounts/', TicketDiscountListView.as_view(), name='ticketdiscount_list'),
    path('ticketdiscounts/create/', TicketDiscountCreateView.as_view(), name='ticketdiscount_create'),
    path('ticketdiscounts/<int:pk>/edit/', TicketDiscountUpdateView.as_view(), name='ticketdiscount_update'),
    path('ticketdiscounts/<int:pk>/delete/', TicketDiscountDeleteView.as_view(), name='ticketdiscount_delete'),
    path('validate-ticket/', views.validate_ticket, name='validate_ticket'),

]
