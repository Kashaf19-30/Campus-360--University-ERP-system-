from django.contrib import admin
from .models import Department, DegreeProgram, Semester, Course, ProgramCourse

admin.site.register(Department)
admin.site.register(DegreeProgram)
admin.site.register(Semester)
admin.site.register(Course)
admin.site.register(ProgramCourse)