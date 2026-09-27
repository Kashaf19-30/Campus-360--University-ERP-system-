from rest_framework import serializers
from .models import Designation, Faculty, EmployeeProfile, FacultyCourseAssignment


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = '__all__'
        read_only_fields = ['designation_id', 'created_at']


class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = '__all__'
        read_only_fields = ['profile_id', 'updated_at']


class FacultySerializer(serializers.ModelSerializer):
    username          = serializers.CharField(source='user.username', read_only=True)
    email             = serializers.CharField(source='user.email', read_only=True)
    department_name   = serializers.CharField(source='department.department_name', read_only=True)
    program_name      = serializers.CharField(source='program.program_name', read_only=True)
    program_code      = serializers.CharField(source='program.program_code', read_only=True)
    designation_title = serializers.CharField(source='designation.designation_title', read_only=True)
    employee_profile  = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = '__all__'
        read_only_fields = ['faculty_id', 'created_at', 'updated_at']

    def get_employee_profile(self, obj):
        profile = EmployeeProfile.objects.filter(
            employee_id=obj.faculty_id, employee_type='faculty'
        ).first()
        return EmployeeProfileSerializer(profile).data if profile else None


class FacultyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = [
            'user', 'department', 'program', 'designation', 'employee_code',
            'qualification', 'specialization', 'joining_date',
            'employment_type', 'status',
        ]


class FacultyCourseAssignmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.user.username', read_only=True)
    employee_code = serializers.CharField(source='faculty.employee_code', read_only=True)
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    program_code = serializers.CharField(source='program.program_code', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    department_name = serializers.CharField(
        source='program.department.department_name', read_only=True,
    )

    class Meta:
        model = FacultyCourseAssignment
        fields = [
            'assignment_id', 'faculty', 'faculty_name', 'employee_code',
            'program', 'program_name', 'program_code', 'department_name',
            'course', 'course_code', 'course_name',
            'assigned_at', 'is_active',
        ]
        read_only_fields = ['assignment_id', 'assigned_at']
