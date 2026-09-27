from django.urls import path
from . import views

urlpatterns = [
    path('structures/', views.list_fee_structures, name='fee-structures'),
    path('structures/create/', views.create_fee_structure, name='create-fee-structure'),
    path('structures/<int:structure_id>/', views.delete_fee_structure, name='delete-fee-structure'),

    path('challans/', views.list_challans, name='list-challans'),
    path('challans/generate/', views.generate_challan, name='generate-challan'),
    path('challans/me/', views.my_challans, name='my-challans'),
    path('challans/me/<int:challan_id>/download/', views.download_my_challan, name='download-my-challan'),

    path('challans/generate-bulk/', views.generate_semester_challans, name='generate-semester-challans'),

    path('finance/dashboard/', views.finance_dashboard, name='finance-dashboard'),
    path('finance/admissions/<int:application_id>/mark-paid/', views.mark_admission_challan_paid, name='mark-admission-paid'),
    path('finance/challans/<int:challan_id>/mark-paid/', views.mark_student_challan_paid, name='mark-challan-paid'),
]