from django.urls import path
from . import views

urlpatterns = [
    # Profile URLs
    path('profile/', views.applicant_profile, name='applicant-profile'),
    
    # Academic Records URLs
    path('academic/', views.add_academic_record, name='add-academic'),
    path('academic/list/', views.get_academic_records, name='academic-list'),
    path('academic/<int:record_id>/', views.delete_academic_record, name='delete-academic-record'),
    
    # Programs for applicants
    path('programs/', views.list_admission_programs, name='admission-programs'),

    # Application URLs
    path('application/', views.admission_application, name='application'),
    path('application/<int:app_id>/', views.delete_application, name='delete-application'),
    
    # ========== ADD THESE DOCUMENT URLs ==========
    path('documents/', views.get_my_documents, name='get-documents'),
    path('documents/upload/', views.upload_document, name='upload-document'),
    path('documents/<int:doc_id>/', views.delete_document, name='delete-document'),
    path('documents/<int:doc_id>/download/', views.download_document, name='download-document'),
    path('challan/download/', views.download_admission_challan, name='download-admission-challan'),
    path('settings/', views.admission_settings_status, name='admission-settings'),

     # Applications — admin
    path('admin/settings/', views.admin_admission_settings, name='admin-admission-settings'),
    path('admin/applications/',                                         views.admin_list_applications,      name='admin-applications'),
    path('admin/applications/<int:application_id>/',                      views.admin_application_detail,     name='admin-application-detail'),
    path('admin/applications/<int:application_id>/delete/',             views.admin_delete_application,     name='admin-delete-application'),
    path('admin/applications/<int:application_id>/decide/',             views.make_decision,                name='make-decision'),
    path('admin/applications/<int:application_id>/documents/<int:doc_id>/download/', views.admin_download_document, name='admin-download-document'),
    path('admin/applications/<int:application_id>/documents/<int:doc_id>/verify/', views.admin_verify_document, name='admin-verify-document'),
]
