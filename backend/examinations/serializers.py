from rest_framework import serializers
from decimal import Decimal
from .models import (
    ExamType, Examination, Grade, Marks, FinalGrade,
    Result, ResultApproval, MarksEditPermission, OfferingMarksEditRequest,
)


class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = '__all__'
        read_only_fields = ['exam_type_id']


class ExaminationSerializer(serializers.ModelSerializer):
    course_code  = serializers.CharField(source='course.course_code', read_only=True)
    exam_type_name = serializers.CharField(source='exam_type.type_name', read_only=True)

    class Meta:
        model = Examination
        fields = '__all__'
        read_only_fields = ['exam_id', 'created_at']


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = ['grade_id']


class MarksSerializer(serializers.ModelSerializer):
    student_reg  = serializers.CharField(source='student.registration_number', read_only=True)
    student_username = serializers.CharField(source='student.user.username', read_only=True)
    exam_name    = serializers.CharField(source='exam.exam_name', read_only=True)

    class Meta:
        model = Marks
        fields = '__all__'
        read_only_fields = ['marks_id', 'entered_at']

    def validate(self, attrs):
        is_absent = attrs.get(
            'is_absent',
            self.instance.is_absent if self.instance else False,
        )
        obtained = attrs.get('obtained_marks')
        if obtained is None and self.instance is not None and 'obtained_marks' not in attrs:
            obtained = self.instance.obtained_marks

        exam = self.instance.exam if self.instance else None
        if exam is None:
            exam_ref = attrs.get('exam') or self.initial_data.get('exam')
            if isinstance(exam_ref, Examination):
                exam = exam_ref
            elif exam_ref:
                exam = Examination.objects.filter(pk=exam_ref).first()

        if not is_absent and obtained is not None and exam is not None:
            if obtained < 0:
                raise serializers.ValidationError(
                    {'obtained_marks': 'Marks cannot be negative.'},
                )
            if Decimal(str(obtained)) > Decimal(str(exam.total_marks)):
                raise serializers.ValidationError(
                    {
                        'obtained_marks': (
                            f'Marks cannot exceed the exam total of {exam.total_marks:g}.'
                        ),
                    },
                )
        return attrs


class StudentMarksSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.exam_name', read_only=True)
    course_code = serializers.CharField(source='exam.course.course_code', read_only=True)
    course_name = serializers.CharField(source='exam.course.course_name', read_only=True)
    exam_total_marks = serializers.DecimalField(
        source='exam.total_marks', max_digits=6, decimal_places=2, read_only=True,
    )
    assessment_category = serializers.CharField(source='exam.assessment_category', read_only=True)
    weight_percentage = serializers.SerializerMethodField()
    weighted_points = serializers.SerializerMethodField()
    max_weighted_points = serializers.SerializerMethodField()

    class Meta:
        model = Marks
        fields = [
            'marks_id', 'exam_name', 'course_code', 'course_name',
            'exam_total_marks', 'assessment_category', 'weight_percentage',
            'obtained_marks', 'weighted_points', 'max_weighted_points',
            'is_absent', 'remarks', 'entered_at',
        ]
        read_only_fields = fields

    def get_weight_percentage(self, obj):
        from .assessment_setup import resolve_exam_weight_percentage
        return float(resolve_exam_weight_percentage(obj.exam))

    def get_weighted_points(self, obj):
        from .assessment_setup import resolve_exam_weight_percentage, compute_weighted_mark_points
        weight = resolve_exam_weight_percentage(obj.exam)
        pts, _ = compute_weighted_mark_points(
            obj.obtained_marks, obj.exam.total_marks, weight, is_absent=obj.is_absent,
        )
        return float(pts) if pts is not None else None

    def get_max_weighted_points(self, obj):
        from .assessment_setup import resolve_exam_weight_percentage
        return float(resolve_exam_weight_percentage(obj.exam))


class FinalGradeSerializer(serializers.ModelSerializer):
    grade_letter = serializers.CharField(source='grade.grade_letter', read_only=True)
    course_code  = serializers.CharField(source='course.course_code', read_only=True)
    course_name  = serializers.CharField(source='course.course_name', read_only=True)
    weighted_points = serializers.DecimalField(
        source='total_obtained_marks', max_digits=6, decimal_places=2, read_only=True,
    )
    max_weighted_points = serializers.DecimalField(
        source='total_marks', max_digits=6, decimal_places=2, read_only=True,
    )

    class Meta:
        model = FinalGrade
        fields = '__all__'
        read_only_fields = ['final_grade_id', 'created_at']


class ResultSerializer(serializers.ModelSerializer):
    student_reg  = serializers.CharField(source='student.registration_number', read_only=True)
    semester_name = serializers.SerializerMethodField()
    semester_label = serializers.SerializerMethodField()
    curriculum_semester = serializers.SerializerMethodField()

    class Meta:
        model = Result
        fields = '__all__'
        read_only_fields = ['result_id', 'created_at']

    def _curriculum_semester_number(self, obj):
        from examinations.models import FinalGrade
        from academics.session_utils import curriculum_semester_for_course
        fg = FinalGrade.objects.filter(
            student=obj.student, semester=obj.semester,
        ).select_related('course', 'student__program').first()
        if fg:
            return curriculum_semester_for_course(fg.student.program, fg.course)
        return obj.student.current_semester

    def get_curriculum_semester(self, obj):
        return self._curriculum_semester_number(obj)

    def get_semester_name(self, obj):
        from academics.session_utils import format_curriculum_semester
        return format_curriculum_semester(self._curriculum_semester_number(obj))

    def get_semester_label(self, obj):
        return self.get_semester_name(obj)


class ResultApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultApproval
        fields = '__all__'
        read_only_fields = ['approval_id', 'approval_date']


class MarksEditPermissionSerializer(serializers.ModelSerializer):
    student_reg = serializers.CharField(source='student.registration_number', read_only=True)
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    faculty_name = serializers.SerializerMethodField()
    course_code = serializers.CharField(source='offering.course.course_code', read_only=True)
    teacher_name = serializers.CharField(source='granted_to.user.username', read_only=True)
    exam_name = serializers.CharField(source='examination.exam_name', read_only=True)

    class Meta:
        model = MarksEditPermission
        fields = '__all__'
        read_only_fields = ['permission_id', 'created_at', 'granted_by', 'granted_to', 'reviewed_at']

    def get_faculty_name(self, obj):
        from academics.display_utils import offering_teacher_name
        return offering_teacher_name(obj.offering, default='—') if obj.offering_id else '—'


class OfferingMarksEditRequestSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='offering.course.course_code', read_only=True)
    course_name = serializers.CharField(source='offering.course.course_name', read_only=True)
    faculty_name = serializers.CharField(source='faculty.user.username', read_only=True)
    semester_name = serializers.SerializerMethodField()
    semester_label = serializers.SerializerMethodField()
    semester_number = serializers.SerializerMethodField()

    class Meta:
        model = OfferingMarksEditRequest
        fields = '__all__'
        read_only_fields = ['request_id', 'requested_at', 'reviewed_by', 'reviewed_at']

    def get_semester_number(self, obj):
        if obj.offering_id:
            return obj.offering.curriculum_semester
        return None

    def get_semester_name(self, obj):
        from academics.session_utils import format_curriculum_semester
        if obj.offering_id:
            return format_curriculum_semester(obj.offering.curriculum_semester)
        return '—'

    def get_semester_label(self, obj):
        return self.get_semester_name(obj)
