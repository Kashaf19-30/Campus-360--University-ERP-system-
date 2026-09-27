from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.my_enrollments, name='my-enrollments'),
    path('', views.list_enrollments, name='list-enrollments'),
    path('repeat-requests/', views.repeat_course_requests, name='repeat-course-requests'),
    path('repeat-requests/admin/', views.list_repeat_requests, name='list-repeat-requests'),
    path('repeat-requests/failed/', views.my_failed_courses, name='my-failed-courses'),
    path('repeat-requests/<int:request_id>/review/', views.review_repeat_request, name='review-repeat-request'),
    path('academic-progress/semester/', views.academic_progress_semester, name='academic-progress-semester'),
    path('academic-progress/repeat/', views.academic_progress_repeat, name='academic-progress-repeat'),
    path('academic-progress/promote/', views.academic_progress_promote, name='academic-progress-promote'),
    path('academic-progress/my-status/', views.my_academic_status, name='my-academic-status'),
    path('academic-progress/teacher-warnings/', views.teacher_academic_warnings, name='teacher-academic-warnings'),
]