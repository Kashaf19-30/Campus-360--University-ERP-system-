from django.contrib import admin
from .models import NotificationType, Notification, Announcement

admin.site.register(NotificationType)
admin.site.register(Notification)
admin.site.register(Announcement)