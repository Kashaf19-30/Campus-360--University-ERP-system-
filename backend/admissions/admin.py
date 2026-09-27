from django.contrib import admin
from .models import Applicant, AcademicRecord, AdmissionApplication, ProgramPreference

admin.site.register(Applicant)
admin.site.register(AcademicRecord)
admin.site.register(AdmissionApplication)
admin.site.register(ProgramPreference)
