from rest_framework import serializers
from .models import FeeStructure, Challan


class FeeStructureSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    program_code = serializers.CharField(source='program.program_code', read_only=True)

    class Meta:
        model = FeeStructure
        fields = '__all__'
        read_only_fields = ['structure_id', 'created_at']


class ChallanSerializer(serializers.ModelSerializer):
    semester_name = serializers.SerializerMethodField()
    semester_label = serializers.SerializerMethodField()
    student_reg = serializers.CharField(source='student.registration_number', read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Challan
        fields = '__all__'
        read_only_fields = ['challan_id', 'challan_number', 'generated_by', 'created_at', 'updated_at']

    def get_semester_name(self, obj):
        from academics.session_utils import format_curriculum_semester
        return format_curriculum_semester(obj.curriculum_semester)

    def get_semester_label(self, obj):
        from academics.session_utils import format_curriculum_semester
        return format_curriculum_semester(obj.curriculum_semester)

    def get_student_name(self, obj):
        user = getattr(obj.student, 'user', None)
        return user.username if user else ''
