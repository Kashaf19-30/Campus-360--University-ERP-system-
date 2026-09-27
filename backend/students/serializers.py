from rest_framework import serializers
from .models import Student, StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model   = StudentProfile
        exclude = ['student']


class StudentSerializer(serializers.ModelSerializer):
    profile             = StudentProfileSerializer(read_only=True)
    program_name        = serializers.CharField(source='program.program_name', read_only=True)
    program_code        = serializers.CharField(source='program.program_code', read_only=True)
    email               = serializers.CharField(source='user.email', read_only=True)
    username            = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model  = Student
        fields = [
            'student_id', 'registration_number', 'batch_year',
            'admission_date', 'current_semester', 'status',
            'cgpa', 'total_credit_hours_completed',
            'consecutive_probation_count', 'academic_review_required',
            'graduation_date',
            'program_name', 'program_code',
            'email', 'username',
            'profile', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'student_id', 'registration_number', 'cgpa',
            'total_credit_hours_completed',
            'created_at', 'updated_at',
        ]


class StudentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Student
        fields = [
            'user', 'applicant', 'program',
            'batch_year', 'admission_date', 'current_semester', 'status',
        ]
