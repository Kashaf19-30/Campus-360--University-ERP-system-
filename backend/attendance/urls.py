from django.urls import path
from . import views

urlpatterns = [
    path('mark/', views.mark_attendance, name='mark-attendance'),
    path('next-lecture/', views.next_lecture_number, name='next-lecture-number'),
    path('', views.list_attendance, name='list-attendance'),
    path('summary/me/', views.my_attendance_summary, name='my-attendance-summary'),
    path('summary/', views.list_attendance_summaries, name='list-attendance-summaries'),
    path('summary/export/', views.export_attendance_report, name='export-attendance-report'),
    path('leaves/submit/', views.submit_leave, name='submit-leave'),
    path('leaves/me/', views.my_leaves, name='my-leaves'),
    path('leaves/<int:leave_id>/', views.delete_leave, name='delete-leave'),
    path('leaves/teacher/', views.teacher_leaves, name='teacher-leaves'),
    path('leaves/<int:leave_id>/review/', views.review_leave, name='review-leave'),
]
