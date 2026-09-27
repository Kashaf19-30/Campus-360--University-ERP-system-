from rest_framework import serializers
from .models import Department, DegreeProgram, Semester, Course, ProgramCourse, AcademicPolicy


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['department_id', 'created_at']


class DegreeProgramSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)

    class Meta:
        model = DegreeProgram
        fields = '__all__'
        read_only_fields = ['program_id', 'created_at', 'program_type']

    def create(self, validated_data):
        validated_data['program_type'] = 'morning'
        return super().create(validated_data)


class SemesterSerializer(serializers.ModelSerializer):
    semester_name = serializers.SerializerMethodField()

    class Meta:
        model = Semester
        fields = '__all__'
        read_only_fields = ['semester_id', 'created_at']

    def get_semester_name(self, obj):
        return 'Active Session' if obj.is_current else obj.semester_name


class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['course_id', 'created_at']


class ProgramCourseSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    credit_hours = serializers.IntegerField(source='course.credit_hours', read_only=True)
    theory_credit_hours = serializers.IntegerField(source='course.theory_credit_hours', read_only=True)
    lab_credit_hours = serializers.IntegerField(source='course.lab_credit_hours', read_only=True)
    course_type = serializers.CharField(source='course.course_type', read_only=True)
    department_id = serializers.IntegerField(source='course.department_id', read_only=True)
    department_name = serializers.CharField(source='course.department.department_name', read_only=True)
    prerequisites = serializers.SerializerMethodField()

    class Meta:
        model = ProgramCourse
        fields = '__all__'
        read_only_fields = ['program_course_id', 'created_at']

    def get_prerequisites(self, obj):
        codes = []
        for p in obj.course.prerequisites.select_related('prerequisite_course'):
            if p.prerequisite_type == 'credit_hours':
                codes.append(f'{p.min_credit_hours}+ CH')
            elif p.prerequisite_course:
                codes.append(p.prerequisite_course.course_code)
        return codes


class ProgramCourseCreateSerializer(serializers.Serializer):
    program = serializers.IntegerField()
    semester_number = serializers.IntegerField(min_value=1, max_value=12)
    department = serializers.IntegerField(required=False, allow_null=True)
    course_code = serializers.CharField(max_length=20)
    course_name = serializers.CharField(max_length=200)
    course_type = serializers.ChoiceField(choices=['core', 'elective', 'university_requirement'])
    credit_hours = serializers.IntegerField(min_value=1)
    theory_credit_hours = serializers.IntegerField(min_value=0, default=0)
    lab_credit_hours = serializers.IntegerField(min_value=0, default=0)
    prerequisite_codes = serializers.ListField(
        child=serializers.CharField(max_length=20), required=False, default=list,
    )


class AcademicPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicPolicy
        fields = [
            'policy_id', 'min_sgpa_pass', 'min_sgpa_probation',
            'min_cgpa_graduation', 'max_consecutive_probation',
            'max_course_attempts', 'min_attendance_percentage',
            'max_semester_credit_hours', 'max_repeat_credit_hours',
            'auto_enroll_failed_prerequisites', 'allow_concurrent_prerequisite_enrollment',
            'soft_prerequisite_enrollment',
            'updated_at',
        ]
        read_only_fields = ['policy_id', 'updated_at']
