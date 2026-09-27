from rest_framework import serializers
from .models import Attendance, AttendanceRecord, StudentAttendanceSummary, LeaveApplication


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_reg = serializers.CharField(source='student.registration_number', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['record_id']


class AttendanceSerializer(serializers.ModelSerializer):
    records       = AttendanceRecordSerializer(many=True, read_only=True)
    course_code   = serializers.CharField(source='offering.course.course_code', read_only=True)
    faculty_name  = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['attendance_id', 'marked_at']

    def get_faculty_name(self, obj):
        from academics.display_utils import offering_teacher_name
        return offering_teacher_name(obj.offering, default='—') if obj.offering_id else '—'


class StudentAttendanceSummarySerializer(serializers.ModelSerializer):
    course_code   = serializers.CharField(source='course.course_code', read_only=True)
    course_name   = serializers.CharField(source='course.course_name', read_only=True)
    semester_name = serializers.CharField(source='semester.semester_name', read_only=True)
    faculty_name  = serializers.SerializerMethodField()
    student_reg   = serializers.CharField(source='student.registration_number', read_only=True)

    class Meta:
        model = StudentAttendanceSummary
        fields = '__all__'
        read_only_fields = ['summary_id', 'last_updated_at']

    def get_faculty_name(self, obj):
        from academics.display_utils import offering_teacher_name
        return offering_teacher_name(obj.offering, default='—') if obj.offering_id else '—'


class LeaveApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_reg = serializers.CharField(source='student.registration_number', read_only=True)
    course_code = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    faculty_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = '__all__'
        read_only_fields = ['leave_id', 'submitted_at', 'reviewed_at', 'reviewed_by', 'status']

    def get_student_name(self, obj):
        return obj.student.user.username

    def get_course_code(self, obj):
        if obj.offering_id and obj.offering:
            return obj.offering.course.course_code
        return '—'

    def get_course_name(self, obj):
        if obj.offering_id and obj.offering:
            return obj.offering.course.course_name
        return '—'

    def get_faculty_name(self, obj):
        if obj.offering_id and obj.offering and obj.offering.faculty_id:
            return obj.offering.faculty.user.username
        return '—'

    def validate(self, attrs):
        from django.utils import timezone
        from enrollments.models import CourseRegistration

        today = timezone.localdate()
        if attrs.get('end_date') and attrs.get('start_date') and attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})
        if attrs.get('start_date') and attrs['start_date'] < today:
            raise serializers.ValidationError({'start_date': 'Start date cannot be before today.'})
        if attrs.get('end_date') and attrs['end_date'] < today:
            raise serializers.ValidationError({'end_date': 'End date cannot be before today.'})

        offering = attrs.get('offering')
        student = attrs.get('student')
        if not offering:
            raise serializers.ValidationError({'offering': 'Course selection is required.'})
        if student and not CourseRegistration.objects.filter(
            student=student,
            offering=offering,
            status='registered',
        ).exists():
            raise serializers.ValidationError({'offering': 'You are not registered in this course.'})
        return attrs
