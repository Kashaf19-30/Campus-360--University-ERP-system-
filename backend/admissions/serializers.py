import re
from datetime import date

from rest_framework import serializers
from academics.models import DegreeProgram
from .models import (
    Applicant, AcademicRecord, AdmissionApplication, ProgramPreference,
    ApplicantDocument, AdmissionDecision, AdmissionLog, AdmissionSettings,
)


class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        exclude = ['user', 'created_at', 'updated_at']
        extra_kwargs = {
            'profile_image': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate_cnic(self, value):
        from accounts.validators import validate_cnic
        if not value:
            raise serializers.ValidationError('CNIC is required.')
        try:
            return validate_cnic(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_first_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('First name is required.')
        return value

    def validate_last_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Last name is required.')
        return value

    def validate_father_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Father name is required.')
        return value


class AcademicRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicRecord
        exclude = ['applicant', 'created_at']

    def validate_roll_number(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Roll number is required.')
        cleaned = str(value).strip()
        if not re.match(r'^[A-Za-z0-9-]{3,20}$', cleaned):
            raise serializers.ValidationError(
                'Roll number must be 3-20 characters (letters, numbers, hyphens only).'
            )
        return cleaned

    def validate(self, attrs):
        current_year = date.today().year
        start_year = attrs.get('start_year')
        end_year = attrs.get('end_year')

        if start_year is not None and (start_year < 1980 or start_year > current_year):
            raise serializers.ValidationError({
                'start_year': f'Start year must be between 1980 and {current_year}.',
            })
        if end_year is not None and (end_year < 1980 or end_year > current_year):
            raise serializers.ValidationError({
                'end_year': f'End year must be between 1980 and {current_year}.',
            })
        if start_year and end_year and end_year <= start_year:
            raise serializers.ValidationError({'end_year': 'End year must be after start year.'})

        obtained = attrs.get('obtained')
        total = attrs.get('total')
        if obtained is None:
            raise serializers.ValidationError({'obtained': 'Obtained marks are required.'})
        if total is None:
            raise serializers.ValidationError({'total': 'Total marks are required.'})
        try:
            obtained_val = float(obtained)
            total_val = float(total)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'obtained': 'Enter valid numeric marks.'})
        if total_val <= 0:
            raise serializers.ValidationError({'total': 'Total marks must be greater than zero (e.g. 1100).'})
        if obtained_val <= 0:
            raise serializers.ValidationError({'obtained': 'Obtained marks must be greater than zero (e.g. 950).'})
        if obtained_val > 99999:
            raise serializers.ValidationError({'obtained': 'Obtained marks cannot exceed 99,999.'})
        if total_val > 9999999:
            raise serializers.ValidationError({'total': 'Total marks cannot exceed 9,999,999.'})
        if obtained_val > total_val:
            raise serializers.ValidationError({'obtained': 'Obtained marks cannot be greater than total marks.'})

        level = attrs.get('qualification_level', '')
        if level not in ('matric', 'inter'):
            raise serializers.ValidationError({'qualification_level': 'Only Matric and Intermediate levels are allowed.'})

        return attrs


class ProgramPreferenceSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    department_name = serializers.CharField(source='program.department.department_name', read_only=True)
    program_id = serializers.IntegerField(source='program.program_id', read_only=True)
    program_code = serializers.CharField(source='program.program_code', read_only=True)

    class Meta:
        model = ProgramPreference
        exclude = ['application']


class AdmissionProgramSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)

    class Meta:
        model = DegreeProgram
        fields = [
            'program_id', 'program_name', 'program_code',
            'department_name', 'degree_level', 'duration_years',
            'accepting_admissions',
        ]


class ApplicantDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantDocument
        fields = '__all__'
        read_only_fields = ['document_id', 'uploaded_at', 'verified_at']

    def get_document_type_display(self, obj):
        return obj.get_document_type_display()


class AdmissionDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionDecision
        fields = '__all__'
        read_only_fields = ['decision_id', 'decision_date', 'created_at']


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    preferences = ProgramPreferenceSerializer(many=True, read_only=True)
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    decision = AdmissionDecisionSerializer(read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = '__all__'


class ApplicantDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.user_id', read_only=True)
    user_type = serializers.CharField(source='user.user_type', read_only=True)
    academic_records = AcademicRecordSerializer(many=True, read_only=True)
    documents = ApplicantDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Applicant
        exclude = ['user', 'created_at', 'updated_at']


class AdminApplicationListSerializer(serializers.ModelSerializer):
    preferences = ProgramPreferenceSerializer(many=True, read_only=True)
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.CharField(source='applicant.user.email', read_only=True)
    applicant_username = serializers.CharField(source='applicant.user.username', read_only=True)
    user_id = serializers.IntegerField(source='applicant.user.user_id', read_only=True)
    user_type = serializers.CharField(source='applicant.user.user_type', read_only=True)
    decision = AdmissionDecisionSerializer(read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = '__all__'

    def get_applicant_name(self, obj):
        return f'{obj.applicant.first_name} {obj.applicant.last_name}'.strip()


class AdminApplicationDetailSerializer(serializers.ModelSerializer):
    preferences = ProgramPreferenceSerializer(many=True, read_only=True)
    program_name = serializers.CharField(source='program.program_name', read_only=True)
    applicant = ApplicantDetailSerializer(read_only=True)
    decision = AdmissionDecisionSerializer(read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = '__all__'


class AdmissionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionLog
        fields = '__all__'
        read_only_fields = ['log_id', 'timestamp']


class AdmissionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionSettings
        fields = ['is_open', 'updated_at']
        read_only_fields = ['updated_at']
