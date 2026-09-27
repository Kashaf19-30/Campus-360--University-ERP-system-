from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_my_notifications, name='list-notifications'),
    path('<int:notification_id>/read/', views.mark_read, name='mark-read'),
    path('read-all/', views.mark_all_read, name='mark-all-read'),

    path('announcements/', views.list_announcements, name='list-announcements'),
    path('announcements/create/', views.create_announcement, name='create-announcement'),
    path('announcements/target-options/', views.get_announcement_target_options, name='announcement-target-options'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement-detail'),

    path('types/', views.list_notification_types, name='notification-types'),
    path('types/create/', views.create_notification_type, name='create-notification-type'),
]