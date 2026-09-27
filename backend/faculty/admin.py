from django.contrib import admin
from .models import Designation, Faculty, EmployeeProfile, FacultyCourseAssignment

admin.site.register(Designation)
admin.site.register(Faculty)
admin.site.register(EmployeeProfile)
admin.site.register(FacultyCourseAssignment)
