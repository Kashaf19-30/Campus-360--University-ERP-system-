from django.contrib import admin
from .models import ExamType, Examination, Grade, Marks, FinalGrade, Result, ResultApproval

admin.site.register(ExamType)
admin.site.register(Examination)
admin.site.register(Grade)
admin.site.register(Marks)
admin.site.register(FinalGrade)
admin.site.register(Result)
admin.site.register(ResultApproval)
