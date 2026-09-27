from rest_framework import serializers
from .models import CourseOffering
from .session_utils import format_curriculum_semester


class CourseOfferingSerializer(serializers.ModelSerializer):
    course_code     = serializers.CharField(source='course.course_code', read_only=True)
    course_name     = serializers.CharField(source='course.course_name', read_only=True)
    semester_name   = serializers.SerializerMethodField()
    semester_label  = serializers.SerializerMethodField()
    faculty_name    = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='course.department.department_name', read_only=True)
    department_id = serializers.IntegerField(source='course.department_id', read_only=True)
    program_name    = serializers.SerializerMethodField()
    program_code    = serializers.SerializerMethodField()
    batch_years     = serializers.SerializerMethodField()
    marks_unlock_active = serializers.SerializerMethodField()
    marks_editable = serializers.SerializerMethodField()
    offering_type_label = serializers.SerializerMethodField()
    display_label = serializers.SerializerMethodField()

    class Meta:
        model = CourseOffering
        fields = '__all__'
        read_only_fields = ['offering_id', 'enrolled_count', 'created_at']

    def get_semester_name(self, obj):
        label = format_curriculum_semester(obj.curriculum_semester)
        if obj.repeat_offering:
            return f'{label} (Repeat)'
        return label

    def get_semester_label(self, obj):
        return self.get_semester_name(obj)

    def get_program_name(self, obj):
        pc = obj.course.program_courses.select_related('program').first()
        return pc.program.program_name if pc else obj.course.department.department_name

    def get_program_code(self, obj):
        pc = obj.course.program_courses.select_related('program').first()
        return pc.program.program_code if pc else ''

    def get_faculty_name(self, obj):
        from academics.display_utils import offering_teacher_name
        return offering_teacher_name(obj, default='Unassigned')

    def get_batch_years(self, obj):
        from enrollments.models import CourseRegistration
        years = CourseRegistration.objects.filter(
            offering=obj, status='registered',
        ).values_list('student__batch_year', flat=True).distinct()
        return sorted(set(y for y in years if y))

    def get_marks_unlock_active(self, obj):
        from examinations.marks_locking import offering_bulk_unlock_active
        return offering_bulk_unlock_active(obj)

    def get_marks_editable(self, obj):
        from examinations.marks_locking import offering_teacher_marks_eligible
        return offering_teacher_marks_eligible(obj)

    def get_offering_type_label(self, obj):
        return 'Repeat' if obj.repeat_offering else 'Regular'

    def get_display_label(self, obj):
        kind = self.get_offering_type_label(obj)
        if getattr(obj, 'cohort_sequence', 1) > 1:
            kind = f'{kind} · Class {obj.cohort_sequence}'
        return f'{obj.course.course_code} — {obj.course.course_name} ({kind})'


class CourseOfferingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOffering
        fields = ['course', 'semester', 'faculty', 'curriculum_semester', 'offering_type', 'is_active']
