from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.get_my_student_profile, name='my-student-profile'),
    path('me/degree-progress/', views.my_degree_progress, name='my-degree-progress'),
    path('me/degree-audit/', views.degree_audit_view, name='my-degree-audit'),
    path('me/transcript/', views.transcript_view, name='my-transcript'),
    path('me/profile/', views.update_student_profile, name='update-student-profile'),
    path('academic-standing/', views.academic_standing, name='academic-standing'),
    path('graduation-candidates/', views.list_graduation_candidates, name='graduation-candidates'),
    path('', views.list_students, name='list-students'),
    path('create/', views.create_student, name='create-student'),
    path('<int:student_id>/promote/', views.manual_promote_student, name='manual-promote-student'),
    path('<int:student_id>/repeat/', views.repeat_semester, name='repeat-semester'),
    path('<int:student_id>/confirm-dismissal/', views.confirm_dismissal, name='confirm-dismissal'),
    path('<int:student_id>/clear-review/', views.clear_dismissal_review, name='clear-dismissal-review'),
    path('<int:student_id>/degree-audit/', views.degree_audit_view, name='degree-audit'),
    path('<int:student_id>/confirm-graduation/', views.confirm_graduation, name='confirm-graduation'),
    path('<int:student_id>/transcript/', views.transcript_view, name='student-transcript'),
    path('<int:student_id>/status/', views.update_student_status, name='update-student-status'),
    path('<int:student_id>/profile/', views.admin_update_student_profile, name='admin-update-student-profile'),
    path('<int:student_id>/documents/<int:doc_id>/download/', views.admin_download_student_document, name='admin-download-student-document'),
    path('<int:student_id>/', views.get_student, name='get-student'),
]
