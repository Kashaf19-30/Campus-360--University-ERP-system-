from django.urls import path
from . import views

urlpatterns = [
    path('exam-types/',        views.list_exam_types,          name='list-exam-types'),
    path('exam-types/create/', views.create_exam_type,         name='create-exam-type'),

    path('grades/', views.list_grades, name='list-grades'),
    path('grades/create/', views.create_grade, name='create-grade'),

    path('', views.list_examinations, name='list-examinations'),
    path('create/', views.create_examination, name='create-examination'),
    path('semester/status/', views.semester_assessment_status, name='semester-assessment-status'),
    path('semester/initialize/', views.initialize_semester_assessments, name='initialize-semester-assessments'),
    path('<int:exam_id>/', views.examination_detail, name='examination-detail'),
    path('marks-lock-status/', views.marks_lock_status, name='marks-lock-status'),
    path('<int:exam_id>/marks/', views.list_marks, name='list-marks'),
    path('<int:exam_id>/marks/enter/', views.enter_marks, name='enter-marks'),

    path('marks/<int:marks_id>/', views.update_marks, name='update-marks'),

    path('final-grades/me/', views.my_final_grades, name='my-final-grades'),
    path('marks/me/', views.my_assessment_marks, name='my-assessment-marks'),
    path('final-grades/create/', views.create_final_grade, name='create-final-grade'),

    path('results/me/', views.my_results, name='my-results'),
    path('results/', views.list_results, name='list-results'),
    path('results/generate/', views.generate_semester_results, name='generate-semester-results'),
    path('results/create/', views.create_result, name='create-result'),
    path('results/<int:result_id>/publish/', views.publish_result, name='publish-result'),
    path('results/publish-semester/', views.publish_semester_results, name='publish-semester-results'),
    path('results/<int:result_id>/approve/', views.approve_result, name='approve-result'),
    path('offerings/<int:offering_id>/compute-grades/', views.compute_offering_grades, name='compute-offering-grades'),
    path('offerings/<int:offering_id>/unlock-marks/', views.unlock_offering_marks, name='unlock-offering-marks'),
    path('offerings/<int:offering_id>/lock-marks/', views.lock_offering_marks, name='lock-offering-marks'),
    path('marks-edit-requests/', views.list_marks_edit_requests, name='list-marks-edit-requests'),
    path('marks-edit-requests/create/', views.request_marks_edit, name='request-marks-edit'),
    path('marks-edit-requests/<int:permission_id>/review/', views.review_marks_edit_request, name='review-marks-edit'),
    path('marks-edit-requests/<int:permission_id>/revoke/', views.revoke_marks_edit_request, name='revoke-marks-edit'),

    path('continuous-assessments/create/', views.create_continuous_assessment, name='create-continuous-assessment'),
    path('offering-edit-requests/', views.offering_marks_edit_requests, name='offering-marks-edit-requests'),
    path('offering-edit-requests/<int:request_id>/review/', views.review_offering_marks_edit_request, name='review-offering-marks-edit'),
]
