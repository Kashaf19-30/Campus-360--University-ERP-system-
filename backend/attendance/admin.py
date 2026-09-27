from django.contrib import admin
from .models import Attendance, AttendanceRecord, StudentAttendanceSummary

admin.site.register(Attendance)
admin.site.register(AttendanceRecord)
admin.site.register(StudentAttendanceSummary)