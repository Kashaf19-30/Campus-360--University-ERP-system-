from django.urls import path
from . import views

urlpatterns = [
    path('designations/', views.list_designations, name='list-designations'),
    path('designations/create/', views.create_designation, name='create-designation'),

    path('', views.list_faculty, name='list-faculty'),
    path('create/', views.create_faculty, name='create-faculty'),
    path('me/', views.get_my_faculty_profile, name='my-faculty-profile'),
    path('<int:faculty_id>/', views.faculty_detail, name='faculty-detail'),

    path('profile/', views.employee_profile, name='employee-profile'),
    path('onboarding/complete/', views.complete_teacher_onboarding, name='complete-teacher-onboarding'),

    path('course-assignments/', views.list_faculty_course_assignments, name='list-faculty-course-assignments'),
    path('course-assignments/create/', views.create_faculty_course_assignment, name='create-faculty-course-assignment'),
    path('course-assignments/<int:assignment_id>/', views.remove_faculty_course_assignment, name='remove-faculty-course-assignment'),
    path('course-assignments/unassigned/', views.list_unassigned_program_courses, name='list-unassigned-program-courses'),
    path('workload/', views.faculty_workload_summary, name='faculty-workload-summary'),
]
