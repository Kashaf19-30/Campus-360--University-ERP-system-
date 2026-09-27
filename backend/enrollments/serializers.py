from rest_framework import serializers
from .models import Enrollment, CourseRegistration, RepeatCourseRequest
from .promotion import get_student_semester_credit_summary
from academics.session_utils import format_curriculum_semester, curriculum_semester_for_course


class CourseRegistrationSerializer(serializers.ModelSerializer):
    course_code   = serializers.CharField(source='course.course_code', read_only=True)
    course_name   = serializers.CharField(source='course.course_name', read_only=True)
    faculty_name  = serializers.SerializerMethodField()
    semester_name = serializers.SerializerMethodField()
    semester_label = serializers.SerializerMethodField()
    academic_term = serializers.SerializerMethodField()
    curriculum_semester = serializers.SerializerMethodField()
    credit_hours  = serializers.IntegerField(source='course.credit_hours', read_only=True)
    registration_type_display = serializers.CharField(source='get_registration_type_display', read_only=True)

    class Meta:
        model = CourseRegistration
        fields = '__all__'
        read_only_fields = ['registration_id', 'registration_date', 'student', 'created_at']

    def _curriculum_semester_number(self, obj):
        return curriculum_semester_for_course(obj.student.program, obj.course)

    def get_faculty_name(self, obj):
        from academics.display_utils import offering_teacher_name
        return offering_teacher_name(obj.offering, default='—') if obj.offering_id else '—'

    def get_curriculum_semester(self, obj):
        return self._curriculum_semester_number(obj)

    def get_semester_name(self, obj):
        return format_curriculum_semester(self._curriculum_semester_number(obj))

    def get_semester_label(self, obj):
        return format_curriculum_semester(self._curriculum_semester_number(obj))

    def get_academic_term(self, obj):
        return format_curriculum_semester(self._curriculum_semester_number(obj))


class EnrollmentSerializer(serializers.ModelSerializer):
    course_registrations = CourseRegistrationSerializer(many=True, read_only=True)
    semester_name        = serializers.SerializerMethodField()
    semester_label       = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ['enrollment_id', 'enrollment_date', 'created_at']

    def get_semester_name(self, obj):
        return format_curriculum_semester(obj.student.current_semester)

    def get_semester_label(self, obj):
        return format_curriculum_semester(obj.student.current_semester)


class RepeatCourseRequestSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    credit_hours = serializers.IntegerField(source='course.credit_hours', read_only=True)
    semester_name = serializers.SerializerMethodField()
    semester_label = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    registration_number = serializers.CharField(source='student.registration_number', read_only=True)
    enrolled_credit_hours = serializers.SerializerMethodField()
    max_semester_credit_hours = serializers.SerializerMethodField()
    remaining_credit_hours = serializers.SerializerMethodField()
    credit_hours_after_approval = serializers.SerializerMethodField()
    would_exceed_credit_cap = serializers.SerializerMethodField()

    class Meta:
        model = RepeatCourseRequest
        fields = '__all__'
        read_only_fields = ['request_id', 'requested_at', 'reviewed_by', 'reviewed_at']

    def get_semester_name(self, obj):
        return format_curriculum_semester(obj.student.current_semester)

    def get_semester_label(self, obj):
        return format_curriculum_semester(obj.student.current_semester)

    def _credit_summary(self, obj):
        cache = getattr(self, '_credit_cache', None)
        if cache is None:
            cache = {}
            self._credit_cache = cache
        key = (obj.student_id, obj.semester_id)
        if key not in cache:
            cache[key] = get_student_semester_credit_summary(obj.student, obj.semester)
        return cache[key]

    def get_enrolled_credit_hours(self, obj):
        return self._credit_summary(obj)['enrolled_credit_hours']

    def get_max_semester_credit_hours(self, obj):
        return self._credit_summary(obj)['max_semester_credit_hours']

    def get_remaining_credit_hours(self, obj):
        return self._credit_summary(obj)['remaining_credit_hours']

    def get_credit_hours_after_approval(self, obj):
        summary = self._credit_summary(obj)
        return summary['enrolled_credit_hours'] + obj.course.credit_hours

    def get_would_exceed_credit_cap(self, obj):
        summary = self._credit_summary(obj)
        return (
            summary['enrolled_credit_hours'] + obj.course.credit_hours
            > summary['max_semester_credit_hours']
        )
