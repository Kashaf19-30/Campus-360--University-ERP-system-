# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/admissions/', include('admissions.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/students/', include('students.urls')),
    path('api/faculty/', include('faculty.urls')),
    path('api/enrollments/', include('enrollments.urls')),
    path('api/examinations/', include('examinations.urls')),
    path('api/attendance/', include('attendance.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/fees/', include('fees.urls')),
    path('api/complaints/', include('complaints.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/recommendations/', include('recommendation.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)