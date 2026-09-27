from django.contrib import admin
from .models import Enrollment, CourseRegistration, RepeatCourseRequest

admin.site.register(Enrollment)
admin.site.register(CourseRegistration)
admin.site.register(RepeatCourseRequest)
