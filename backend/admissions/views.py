# admissions/views.py
import uuid
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import require_permission, require_any_permission, IsAdmissionApplicant
from accounts.audit import log_audit
from accounts.models import UserRole, Role
from students.models import Student, StudentProfile
from academics.models import DegreeProgram, Semester, ProgramCourse, CourseOffering
from enrollments.models import Enrollment, CourseRegistration
from fees.models import FeeStructure, Challan
from notifications.models import NotificationType, Notification
from .models import (
    Applicant, AcademicRecord, AdmissionApplication, ProgramPreference, 
    ApplicantDocument, AdmissionDecision, AdmissionLog, AdmissionSettings,
) 
from .serializers import (
    ApplicantSerializer, AcademicRecordSerializer,
    AdmissionApplicationSerializer, ApplicantDocumentSerializer,
    AdmissionDecisionSerializer, AdmissionProgramSerializer,
    AdminApplicationListSerializer, AdminApplicationDetailSerializer,
    AdmissionSettingsSerializer,
)
from .settings_utils import get_admission_settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.conf import settings
from decimal import Decimal
from .document_validation import validate_document_upload
from .challan_pdf import build_challan_payload, generate_challan_pdf

def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


LOCKED_APPLICATION_STATUSES = {
    'pending', 'challan_pending', 'under_review', 'documents_pending',
    'approved', 'rejected', 'registered',
}


def _required_personal_docs_verified(applicant):
    """All required personal documents must exist and pass OCR verification."""
    missing = []
    for doc_type in REQUIRED_PERSONAL_DOCS:
        doc = ApplicantDocument.objects.filter(
            applicant=applicant, document_type=doc_type, is_verified=True,
        ).first()
        if not doc:
            missing.append(doc_type.replace('_', ' '))
    if missing:
        return False, f'Missing or OCR-unverified documents: {", ".join(missing)}.'
    return True, ''

REQUIRED_PERSONAL_DOCS = {'cnic_front', 'cnic_back', 'domicile', 'photograph'}
MIN_DOCUMENT_SIZE = 1024  # 1 KB minimum to reject blank files
ADMISSION_FEE_AMOUNT = Decimal('15000')


def _program_admission_fee(program):
    """Fixed admission fee for new applicants (not semester fee)."""
    return ADMISSION_FEE_AMOUNT


def _applicant_has_submitted_application(applicant):
    """True once the applicant has submitted an application (non-draft)."""
    return AdmissionApplication.objects.filter(
        applicant=applicant,
        status__in=LOCKED_APPLICATION_STATUSES,
    ).exists()


def _get_applicant_for_user(user):
    try:
        return Applicant.objects.get(user=user)
    except Applicant.DoesNotExist:
        return None


def _locked_response():
    return Response(
        {'error': 'Your application has been submitted. You cannot make changes.'},
        status=status.HTTP_403_FORBIDDEN,
    )


def _log(application, action_type, performed_by, prev_status, new_status, request, remarks=''):
    AdmissionLog.objects.create(
        application=application,
        action_type=action_type,
        performed_by=performed_by,
        previous_status=prev_status,
        new_status=new_status,
        remarks=remarks,
        ip_address=_get_ip(request),
    )


def _parse_preference_order(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = ''.join(ch for ch in value if ch.isdigit())
        if digits:
            return int(digits)
    return 1


def _resolve_program(pref):
    program_id = pref.get('program_id')
    if program_id:
        return DegreeProgram.objects.filter(
            program_id=program_id,
            is_active=True,
            accepting_admissions=True,
        ).first()

    program_name = pref.get('program') or pref.get('program_name')
    if program_name:
        return DegreeProgram.objects.filter(
            program_name=program_name,
            is_active=True,
            accepting_admissions=True,
        ).first()
    return None


def _check_eligibility(applicant):
    """
    Automatic eligibility check.
    Returns (eligible: bool, percentage: float|None, message: str).
    """
    inter_record = AcademicRecord.objects.filter(
        applicant=applicant,
        qualification_level='inter',
    ).order_by('-end_year').first()

    if not inter_record:
        inter_record = AcademicRecord.objects.filter(
            applicant=applicant,
            qualification_level='intermediate',
        ).order_by('-end_year').first()

    if not inter_record:
        return False, None, 'Intermediate academic record is required.'

    if inter_record.grading_system == 'marks':
        if not inter_record.total or inter_record.total <= 0:
            return False, None, 'Invalid intermediate marks record.'
        percentage = float(inter_record.obtained / inter_record.total * 100)
        if percentage < 50:
            return False, percentage, 'You do not meet the program requirement. Minimum 50% marks in Intermediate are required.'
        return True, percentage, ''

    if inter_record.grading_system == 'cgpa':
        if float(inter_record.obtained) < 2.0:
            return False, None, 'You do not meet the program requirement. Minimum 2.0 CGPA in Intermediate is required.'
        return True, None, ''

    return False, None, 'Invalid grading system for intermediate record.'


def _has_matric_and_inter(applicant):
    levels = set(
        AcademicRecord.objects.filter(applicant=applicant)
        .values_list('qualification_level', flat=True)
    )
    has_matric = 'matric' in levels
    has_inter = 'inter' in levels or 'intermediate' in levels
    return has_matric and has_inter


def _validate_personal_documents(applicant):
    """Ensure all required personal documents exist and are not blank."""
    docs = ApplicantDocument.objects.filter(
        applicant=applicant,
        document_type__in=REQUIRED_PERSONAL_DOCS,
    )
    uploaded_types = set(docs.values_list('document_type', flat=True))
    missing = REQUIRED_PERSONAL_DOCS - uploaded_types
    if missing:
        labels = {
            'cnic_front': 'CNIC Front',
            'cnic_back': 'CNIC Back',
            'domicile': 'Domicile',
            'photograph': 'Photograph',
        }
        return False, f"Missing required documents: {', '.join(labels[t] for t in sorted(missing))}"

    for doc in docs:
        if doc.file_size < MIN_DOCUMENT_SIZE:
            return False, f"{doc.get_document_type_display()} appears to be blank or invalid. Please upload a valid document."
        if doc.file_path and not default_storage.exists(doc.file_path):
            return False, f"{doc.get_document_type_display()} file not found. Please re-upload."

    return True, ''


ACADEMIC_DOC_TYPES = {
    'matric': ['matric_marksheet', 'matric_certificate'],
    'inter': ['inter_marksheet', 'inter_certificate'],
}


def _validate_academic_documents(applicant):
    """Matric and inter each need at least one document (marksheet or certificate)."""
    uploaded = set(
        ApplicantDocument.objects.filter(applicant=applicant).values_list('document_type', flat=True)
    )
    missing_labels = []
    level_labels = {'matric': 'Matric', 'inter': 'Intermediate'}
    for level, doc_types in ACADEMIC_DOC_TYPES.items():
        if not any(doc_type in uploaded for doc_type in doc_types):
            missing_labels.append(level_labels.get(level, level.title()))
    if missing_labels:
        return False, f"Upload at least one document for: {', '.join(missing_labels)}"
    return True, ''


def _generate_unique_app_number():
    year = timezone.now().year
    for _ in range(20):
        app_number = f'APP-{year}-{uuid.uuid4().hex[:8].upper()}'
        if not AdmissionApplication.objects.filter(application_number=app_number).exists():
            return app_number
    raise ValueError('Could not generate a unique application number.')


def _validate_sequential_preferences(orders):
    """Preferences must be 1, then optionally 2, then optionally 3 — in sequence."""
    if not orders:
        return False, 'At least one program preference is required.'
    sorted_orders = sorted(orders)
    expected = list(range(1, len(sorted_orders) + 1))
    if sorted_orders != expected:
        return False, 'Select preferences in sequence: 1st preference first, then 2nd, then 3rd.'
    if len(sorted_orders) > 3:
        return False, 'Maximum 3 program preferences allowed.'
    return True, ''


def _sync_user_role(user, role_key, assigned_by=None):
    role_name_map = {
        'student': 'Student',
        'teacher': 'Teacher',
        'admin': 'Admin',
        'applicant': 'Applicant',
    }
    role_name = role_name_map.get(role_key)
    if not role_name:
        return
    role, _ = Role.objects.get_or_create(
        role_name=role_name,
        defaults={'description': f'{role_name} role'},
    )
    UserRole.objects.filter(user=user).delete()
    UserRole.objects.create(user=user, role=role, assigned_by=assigned_by or user)


def _get_or_create_offering_for_enrollment(course, program, semester, warnings):
    from faculty.assignment_utils import resolve_offering_for_enrollment
    return resolve_offering_for_enrollment(course, program, semester, warnings)


def _auto_enroll_student(student, program, performed_by):
    """Create semester challan; course registration only after finance marks fee paid."""
    from enrollments.promotion import enroll_student_for_semester
    from notifications.system_notify import notify_user

    try:
        current_semester = Semester.objects.get(is_current=True)
    except Semester.DoesNotExist:
        return {
            'enrolled_courses': [],
            'warnings': ['No active semester found. Run seed_erp_data.'],
            'registration_blocked': True,
        }

    enroll_result = enroll_student_for_semester(student, current_semester, performed_by=performed_by)

    if enroll_result.get('registration_blocked'):
        notify_user(
            student.user,
            'Finance',
            'Semester fee payment required',
            (
                f'Welcome! Your registration number is {student.registration_number}. '
                f'Pay Semester {student.current_semester} fee to register your courses.'
            ),
            priority='high',
        )
    else:
        course_list = ', '.join(enroll_result.get('enrolled_courses') or []) or 'pending'
        notify_user(
            student.user,
            'Registration',
            'Welcome to Campus 360',
            (
                f'Registration confirmed. Program: {program.program_name}. '
                f'Enrolled courses: {course_list}.'
            ),
            priority='high',
        )

    return enroll_result


STALE_PURGE_STATUSES = ('pending', 'challan_pending')


def _delete_applicant_account(user):
    """Remove applicant admission data in FK-safe order, then delete the user."""
    applicant = Applicant.objects.filter(user=user).first()
    if not applicant:
        user.delete()
        return

    with transaction.atomic():
        for app in AdmissionApplication.objects.filter(applicant=applicant):
            AdmissionDecision.objects.filter(application=app).delete()
            AdmissionLog.objects.filter(application=app).delete()
            ProgramPreference.objects.filter(application=app).delete()
            app.delete()
        ApplicantDocument.objects.filter(applicant=applicant).delete()
        AcademicRecord.objects.filter(applicant=applicant).delete()
        applicant.delete()
        user.delete()


def _purge_stale_applications():
    """Delete applicants who never paid admission fee within 15 days of submission."""
    cutoff = timezone.now() - timedelta(days=15)
    stale_apps = AdmissionApplication.objects.filter(
        challan_paid=False,
        submitted_at__lt=cutoff,
        status__in=STALE_PURGE_STATUSES,
    ).select_related('applicant__user')

    deleted = 0
    seen_users = set()
    for app in stale_apps:
        user_id = app.applicant.user_id
        if user_id in seen_users:
            continue
        seen_users.add(user_id)
        _delete_applicant_account(app.applicant.user)
        deleted += 1
    return deleted


def _audit_registration_snapshot(registration_info):
    """JSON-safe subset of registration result for audit logs."""
    if not registration_info:
        return None
    if registration_info.get('error'):
        return {'error': registration_info['error']}
    student = registration_info.get('student')
    enroll = registration_info.get('enroll_result') or {}
    return {
        'registration_number': registration_info.get('registration_number'),
        'student_id': getattr(student, 'student_id', None),
        'enrolled_courses': enroll.get('enrolled_courses'),
        'warnings': enroll.get('warnings'),
    }


def _preference_program_ids(application):
    ids = list(
        ProgramPreference.objects.filter(application=application).values_list('program_id', flat=True)
    )
    if application.program_id and application.program_id not in ids:
        ids.append(application.program_id)
    return ids


def _resolve_admin_selected_program(application, selected_program_id):
    try:
        program_id = int(selected_program_id)
    except (TypeError, ValueError):
        return None
    allowed = set(_preference_program_ids(application))
    if program_id not in allowed:
        return None
    return DegreeProgram.objects.filter(program_id=program_id).first()


def _register_approved_student(application, performed_by):
    """Create student record and convert applicant to student."""
    applicant = application.applicant
    user = applicant.user

    if Student.objects.filter(user=user).exists():
        return {'error': 'Student record already exists for this user.'}

    batch_year = timezone.now().year

    existing_count = Student.objects.filter(
        program=application.program,
        batch_year=batch_year,
    ).count()
    registration_number = f"{application.program.program_code}-{batch_year}-{str(existing_count + 1).zfill(4)}"

    student = Student.objects.create(
        user=user,
        applicant=applicant,
        program=application.program,
        registration_number=registration_number,
        batch_year=batch_year,
        admission_date=timezone.now().date(),
    )
    StudentProfile.objects.create(
        student=student,
        guardian_name=applicant.guardian_name,
        guardian_cnic=applicant.guardian_cnic,
        guardian_phone=applicant.phone,
        residential_address=applicant.perm_address,
        permanent_address=applicant.perm_address,
        permanent_address_same_as_residential=True,
    )
    user.user_type = 'student'
    user.save(update_fields=['user_type'])
    _sync_user_role(user, 'student', assigned_by=performed_by)
    application.status = 'registered'
    application.save(update_fields=['status'])
    enroll_result = _auto_enroll_student(student, application.program, performed_by)
    return {
        'student': student,
        'registration_number': registration_number,
        'enroll_result': enroll_result,
    }

# ========== EXISTING VIEWS ==========

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def applicant_profile(request):
    if request.method == 'GET':
        try:
            applicant = Applicant.objects.get(user=request.user)
            return Response(ApplicantSerializer(applicant).data)
        except Applicant.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

    applicant, _ = Applicant.objects.get_or_create(user=request.user)
    if _applicant_has_submitted_application(applicant):
        return _locked_response()

    serializer = ApplicantSerializer(applicant, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def add_academic_record(request):
    try:
        applicant = Applicant.objects.get(user=request.user)
    except Applicant.DoesNotExist:
        return Response({'error': 'Complete your profile first.'}, status=400)

    if _applicant_has_submitted_application(applicant):
        return _locked_response()

    level = request.data.get('qualification_level')
    doc_groups = {
        'matric': ['matric_marksheet', 'matric_certificate'],
        'inter': ['inter_marksheet', 'inter_certificate'],
    }
    if level in doc_groups:
        uploaded = set(
            ApplicantDocument.objects.filter(applicant=applicant).values_list('document_type', flat=True)
        )
        if not any(d in uploaded for d in doc_groups[level]):
            return Response(
                {'error': 'Upload a marksheet or certificate for this qualification before saving.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = AcademicRecordSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(applicant=applicant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def get_academic_records(request):
    try:
        applicant = Applicant.objects.get(user=request.user)
        records = AcademicRecord.objects.filter(applicant=applicant)
        return Response(AcademicRecordSerializer(records, many=True).data)
    except Applicant.DoesNotExist:
        return Response([])


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def list_admission_programs(request):
    programs = DegreeProgram.objects.select_related('department').filter(
        is_active=True,
        accepting_admissions=True,
    ).exclude(degree_level__in=['MS', 'PhD']).order_by(
        'department__department_name', 'program_name',
    )
    return Response(AdmissionProgramSerializer(programs, many=True).data)


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def admission_application(request):
    if request.method == 'GET':
        try:
            applicant = Applicant.objects.get(user=request.user)
            apps = AdmissionApplication.objects.filter(applicant=applicant)
            return Response(AdmissionApplicationSerializer(apps, many=True).data)
        except Applicant.DoesNotExist:
            return Response([])

    try:
        applicant = Applicant.objects.get(user=request.user)
    except Applicant.DoesNotExist:
        return Response({'error': 'Complete your profile first.'}, status=400)

    from .settings_utils import is_admissions_open
    if not is_admissions_open():
        return Response(
            {'error': 'Admissions are currently closed. Application submission is not available.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if AdmissionApplication.objects.filter(applicant=applicant).exists():
        return Response(
            {'error': 'You already have a submitted application.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    preferences_data = request.data.get('preferences', [])
    if not preferences_data:
        return Response({'error': 'At least one program preference is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if not _has_matric_and_inter(applicant):
        return Response(
            {'error': 'Both Matric and Intermediate academic records are required before submitting.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    docs_ok, docs_msg = _validate_personal_documents(applicant)
    if not docs_ok:
        return Response({'error': docs_msg}, status=status.HTTP_400_BAD_REQUEST)

    acad_docs_ok, acad_docs_msg = _validate_academic_documents(applicant)
    if not acad_docs_ok:
        return Response({'error': acad_docs_msg}, status=status.HTTP_400_BAD_REQUEST)

    resolved_preferences = []
    for pref in preferences_data:
        program = _resolve_program(pref)
        if not program:
            return Response(
                {'error': f"Invalid or unavailable program: {pref.get('program') or pref.get('program_id')}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = _parse_preference_order(pref.get('preference_order') or pref.get('preference'))
        resolved_preferences.append((program, order))

    pref_orders = [order for _, order in resolved_preferences]
    seq_ok, seq_msg = _validate_sequential_preferences(pref_orders)
    if not seq_ok:
        return Response({'error': seq_msg}, status=status.HTTP_400_BAD_REQUEST)

    program_ids = [p.program_id for p, _ in resolved_preferences]
    if len(program_ids) != len(set(program_ids)):
        return Response({'error': 'Each program can only be selected once.'}, status=status.HTTP_400_BAD_REQUEST)

    resolved_preferences.sort(key=lambda item: item[1])
    primary_program = resolved_preferences[0][0]

    eligible, inter_pct, eligibility_msg = _check_eligibility(applicant)

    app_number = _generate_unique_app_number()

    with transaction.atomic():
        application = AdmissionApplication.objects.create(
            applicant=applicant,
            program=primary_program,
            application_number=app_number,
            admission_type='Regular',
            session_year=timezone.now().year,
            session_type='spring',
            is_eligible=eligible,
        )

        for program, order in resolved_preferences:
            ProgramPreference.objects.create(
                application=application,
                program=program,
                preference_order=order,
            )

        if not eligible:
            application.status = 'rejected'
            application.rejection_message = eligibility_msg
            application.save(update_fields=['status', 'rejection_message'])
            AdmissionDecision.objects.create(
                application=application,
                decision='rejected',
                decided_by=request.user,
                remarks='Auto-rejected due to eligibility criteria.',
                rejection_reason=eligibility_msg,
            )
            _log(application, 'rejected', request.user, 'draft', 'rejected', request,
                 remarks=eligibility_msg)
            return Response({
                'application_id': application.id,
                'application_number': application.application_number,
                'status': application.status,
                'rejected': True,
                'message': eligibility_msg,
            }, status=status.HTTP_201_CREATED)

        challan_number = f'ADM-CH-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}'
        challan_amount = _program_admission_fee(primary_program)
        application.status = 'challan_pending'
        application.admission_challan_number = challan_number
        application.admission_challan_amount = challan_amount
        application.save(update_fields=[
            'status', 'admission_challan_number', 'admission_challan_amount', 'is_eligible',
        ])

        _log(application, 'submitted', request.user, 'draft', 'challan_pending', request,
             remarks='Application submitted. Awaiting admission challan payment.')

    return Response({
        'application_id': application.id,
        'application_number': application.application_number,
        'status': application.status,
        'challan_number': application.admission_challan_number,
        'challan_amount': str(application.admission_challan_amount),
        'rejected': False,
    }, status=status.HTTP_201_CREATED)


# ========== DOCUMENT VIEWS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def get_my_documents(request):
    """Get all documents for the current applicant"""
    try:
        applicant = Applicant.objects.get(user=request.user)
        documents = ApplicantDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')
        serializer = ApplicantDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    except Applicant.DoesNotExist:
        return Response([])


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def upload_document(request):
    """Upload a document for the current applicant"""
    try:
        applicant = Applicant.objects.get(user=request.user)
    except Applicant.DoesNotExist:
        return Response(
            {'error': 'Please complete your profile first. Go to Complete Profile tab and save your details.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    document_type = request.data.get('document_type', 'photograph')
    personal_doc_types = ['cnic_front', 'cnic_back', 'domicile', 'photograph']

    if document_type == 'paid_challan':
        return Response(
            {'error': 'Challan upload is not supported. Pay at the finance office; Finance will confirm payment.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if _applicant_has_submitted_application(applicant):
        return _locked_response()

    missing_profile = []
    if not (applicant.first_name or '').strip():
        missing_profile.append('first name')
    if not (applicant.last_name or '').strip():
        missing_profile.append('last name')
    if not (applicant.father_name or '').strip():
        missing_profile.append('father name')
    if not (applicant.cnic or '').strip():
        missing_profile.append('CNIC')
    if missing_profile:
        return Response(
            {'error': f'Complete your profile before uploading documents: {", ".join(missing_profile)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Only apply limit for personal documents
    if document_type in personal_doc_types:
        personal_doc_count = ApplicantDocument.objects.filter(
            applicant=applicant, 
            document_type__in=personal_doc_types
        ).count()
        if personal_doc_count >= 4:
            return Response(
                {'error': 'Maximum 4 personal documents allowed (CNIC Front, CNIC Back, Domicile, Photograph). You cannot upload more personal documents.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # No limit for academic documents - they can be uploaded freely
    
    # Get uploaded file
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response(
            {'error': 'No file provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate file size (max 1 MB = 1,048,576 bytes)
    if uploaded_file.size > 1048576:
        return Response(
            {'error': 'File size must be ≤ 1 MB'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if uploaded_file.size < MIN_DOCUMENT_SIZE:
        return Response(
            {'error': 'File appears to be blank or too small. Please upload a valid document.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    file_content = uploaded_file.read()
    file_ext = uploaded_file.name.split('.')[-1].lower()
    allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
    if file_ext not in allowed_extensions:
        return Response(
            {'error': f'Only {", ".join(allowed_extensions)} files are allowed'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── OCR validation (blank, blur, name match, challan checks) ──
    applicant_full_name = f'{applicant.first_name} {applicant.last_name}'.strip()
    validation_context = {
        'applicant_name': applicant_full_name,
        'first_name': applicant.first_name or '',
        'last_name': applicant.last_name or '',
        'father_name': applicant.father_name or '',
        'applicant_cnic': applicant.cnic or '',
    }
    result = validate_document_upload(
        file_content,
        file_ext,
        document_type,
        **validation_context,
    )
    if not result.ok:
        return Response({'error': result.error}, status=status.HTTP_400_BAD_REQUEST)

    # Create directory if it doesn't exist
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'documents', f'applicant_{applicant.id}')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    upload_path = f'documents/applicant_{applicant.id}/{unique_filename}'
    
    saved_path = default_storage.save(upload_path, ContentFile(file_content))

    ApplicantDocument.objects.filter(applicant=applicant, document_type=document_type).delete()

    auto_verified = True
    document = ApplicantDocument.objects.create(
        applicant=applicant,
        document_type=document_type,
        file_name=uploaded_file.name,
        file_path=saved_path,
        file_size=uploaded_file.size,
        file_type=file_ext,
        is_verified=True,
        verified_at=timezone.now(),
        verification_remarks=result.remarks,
    )

    msg = 'Document uploaded and verified by OCR.'
    
    return Response(
        {
            'message': msg,
            'document_id': document.document_id,
            'auto_verified': True,
            'ocr_confidence': round(result.confidence, 3),
            'application_status': (
                AdmissionApplication.objects.filter(applicant=applicant)
                .order_by('-submitted_at').values_list('status', flat=True).first()
            ),
        }, 
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def download_admission_challan(request):
    """Download admission challan as PDF or JSON metadata."""
    from django.http import HttpResponse

    try:
        applicant = Applicant.objects.select_related('user').get(user=request.user)
    except Applicant.DoesNotExist:
        return Response({'error': 'Applicant profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    application = AdmissionApplication.objects.filter(
        applicant=applicant,
        status__in=['challan_pending', 'under_review'],
    ).select_related('program', 'program__department').first()

    if not application:
        return Response({'error': 'No pending admission challan found.'}, status=status.HTTP_404_NOT_FOUND)

    if application.challan_paid:
        return Response(
            {'error': 'Challan has already been paid. Download is no longer available.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    payload = build_challan_payload(application, applicant)
    fmt = request.query_params.get('format', 'pdf').lower()

    if fmt == 'json':
        return Response(payload)

    pdf_bytes = generate_challan_pdf(payload)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Admission-Challan-{application.admission_challan_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def delete_document(request, doc_id):
    """Delete a document by ID"""
    try:
        applicant = Applicant.objects.get(user=request.user)
        if _applicant_has_submitted_application(applicant):
            return _locked_response()

        document = ApplicantDocument.objects.get(document_id=doc_id, applicant=applicant)
        
        # Delete the physical file from storage
        if document.file_path:
            default_storage.delete(document.file_path)
        
        # Delete the database record
        document.delete()
        
        return Response(
            {'message': 'Document deleted successfully'}, 
            status=status.HTTP_200_OK
        )
        
    except Applicant.DoesNotExist:
        return Response(
            {'error': 'Applicant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ApplicantDocument.DoesNotExist:
        return Response(
            {'error': 'Document not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def download_document(request, doc_id):
    """Download a document file"""
    try:
        applicant = Applicant.objects.get(user=request.user)
        document = ApplicantDocument.objects.get(document_id=doc_id, applicant=applicant)
        
        from django.http import FileResponse, Http404
        
        if default_storage.exists(document.file_path):
            file = default_storage.open(document.file_path, 'rb')
            response = FileResponse(file, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            return response
        else:
            raise Http404("File not found")
            
    except (Applicant.DoesNotExist, ApplicantDocument.DoesNotExist):
        return Response(
            {'error': 'Document not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def delete_application(request, app_id):
    """Delete an application by ID"""
    try:
        applicant = Applicant.objects.get(user=request.user)
        application = AdmissionApplication.objects.get(id=app_id, applicant=applicant)

        if application.status in LOCKED_APPLICATION_STATUSES:
            return Response(
                {'error': 'Submitted applications cannot be deleted.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Delete all preferences first (cascade will handle if set)
        application.preferences.all().delete()
        # Delete the application
        application.delete()
        
        return Response(
            {'message': 'Application deleted successfully'}, 
            status=status.HTTP_200_OK
        )
        
    except Applicant.DoesNotExist:
        return Response(
            {'error': 'Applicant not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except AdmissionApplication.DoesNotExist:
        return Response(
            {'error': 'Application not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmissionApplicant])
def delete_academic_record(request, record_id):
    """Delete an academic record by ID"""
    try:
        applicant = Applicant.objects.get(user=request.user)
        if _applicant_has_submitted_application(applicant):
            return _locked_response()

        record = AcademicRecord.objects.get(id=record_id, applicant=applicant)
        record.delete()
        return Response({'message': 'Academic record deleted successfully'}, status=status.HTTP_200_OK)
    except Applicant.DoesNotExist:
        return Response({'error': 'Applicant not found'}, status=status.HTTP_404_NOT_FOUND)
    except AcademicRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Admin endpoints ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def admission_settings_status(request):
    settings = get_admission_settings()
    return Response(AdmissionSettingsSerializer(settings).data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, require_permission('admissions.view_application')])
def admin_admission_settings(request):
    settings = get_admission_settings()
    if request.method == 'GET':
        return Response(AdmissionSettingsSerializer(settings).data)

    serializer = AdmissionSettingsSerializer(settings, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        log_audit(
            request,
            'update_admission_settings',
            'admission_settings',
            settings.settings_id,
            new_value=serializer.data,
        )
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('admissions.view_application')])
def admin_list_applications(request):
    try:
        _purge_stale_applications()
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Stale application purge skipped due to error')

    qs = AdmissionApplication.objects.select_related(
        'applicant', 'applicant__user', 'program', 'program__department'
    ).prefetch_related('preferences', 'decision').filter(
        Q(challan_paid=True)
        | Q(status__in=['approved', 'rejected', 'registered'])
    ).exclude(status='draft').order_by('-submitted_at')

    tab = request.query_params.get('tab')
    if tab == 'pending':
        qs = qs.filter(status='under_review')
    elif tab == 'accepted':
        qs = qs.filter(status__in=['approved', 'registered'])
    elif tab == 'rejected':
        qs = qs.filter(status='rejected')
    else:
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

    dept = request.query_params.get('department')
    if dept:
        qs = qs.filter(program__department__department_id=dept)
    program = request.query_params.get('program')
    if program:
        qs = qs.filter(program__program_id=program)

    return Response(AdminApplicationListSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('admissions.view_application')])
def admin_application_detail(request, application_id):
    try:
        application = AdmissionApplication.objects.select_related(
            'applicant', 'applicant__user', 'program'
        ).prefetch_related(
            'preferences',
            'applicant__academic_records',
            'applicant__documents',
            'decision',
        ).get(id=application_id)
    except AdmissionApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(AdminApplicationDetailSerializer(application).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('admissions.view_application')])
def admin_download_document(request, application_id, doc_id):
    try:
        application = AdmissionApplication.objects.select_related('applicant').get(id=application_id)
        document = ApplicantDocument.objects.get(
            document_id=doc_id,
            applicant=application.applicant,
        )
        from django.http import FileResponse, Http404

        if default_storage.exists(document.file_path):
            file = default_storage.open(document.file_path, 'rb')
            response = FileResponse(file, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            return response
        raise Http404("File not found")
    except (AdmissionApplication.DoesNotExist, ApplicantDocument.DoesNotExist):
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('admissions.decide_application')])
def make_decision(request, application_id):
    try:
        application = AdmissionApplication.objects.get(id=application_id)
    except AdmissionApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    decision_value = request.data.get('decision')
    if decision_value not in ['approved', 'rejected']:
        return Response(
            {'error': 'decision must be approved or rejected.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if application.status in ('registered', 'approved', 'rejected'):
        return Response(
            {'error': 'This application has already been decided.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if decision_value == 'approved':
        if application.status != 'under_review':
            return Response(
                {'error': 'Application must be under review before approval.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not application.challan_paid:
            return Response(
                {'error': 'Admission fee must be paid before approval.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        docs_ok, docs_err = _required_personal_docs_verified(application.applicant)
        if not docs_ok:
            return Response({'error': docs_err}, status=status.HTTP_400_BAD_REQUEST)

    remarks_val = request.data.get('remarks', '').strip()
    if not remarks_val:
        return Response(
            {'error': 'Remarks are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if decision_value == 'rejected' and not request.data.get('rejection_reason', '').strip():
        return Response(
            {'error': 'Rejection reason is required when rejecting an application.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    prev = application.status
    registration_info = None
    selected_program_id = request.data.get('selected_program_id')

    if decision_value == 'approved':
        if not selected_program_id:
            return Response(
                {'error': 'Please select a final program from the applicant preferences.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        selected_program = _resolve_admin_selected_program(application, selected_program_id)
        if not selected_program:
            return Response(
                {'error': 'Selected program must be one of the applicant\'s listed preferences.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    with transaction.atomic():
        if hasattr(application, 'decision') and application.decision:
            application.decision.delete()

        registration_deadline = None
        rejection_reason = request.data.get('rejection_reason', '')

        AdmissionDecision.objects.create(
            application=application,
            decision=decision_value,
            decided_by=request.user,
            remarks=remarks_val,
            registration_deadline=registration_deadline,
            rejection_reason=rejection_reason,
            merit_score=request.data.get('merit_score'),
            merit_position=request.data.get('merit_position'),
        )

        if decision_value == 'rejected':
            application.status = 'rejected'
            application.rejection_message = rejection_reason or remarks_val
            application.save(update_fields=['status', 'rejection_message'])
        elif decision_value == 'approved':
            application.program = selected_program
            application.status = 'approved'
            application.is_documents_verified = True
            application.save(update_fields=['program', 'status', 'is_documents_verified'])
            registration_info = _register_approved_student(application, request.user)
            if registration_info.get('error'):
                transaction.set_rollback(True)
                return Response({'error': registration_info['error']}, status=status.HTTP_400_BAD_REQUEST)

        new_status = application.status
        _log(application, decision_value, request.user, prev, new_status, request, remarks=remarks_val)
        log_audit(request, f'admission_{decision_value}', 'admission_application', application.id,
                  new_value={
                      'decision': decision_value,
                      'selected_program_id': selected_program_id,
                      'registration': _audit_registration_snapshot(registration_info),
                  })

    response_data = {
        'message': f'Application {decision_value}.' + (
            ' Student registered automatically.' if decision_value == 'approved' else ''
        ),
        'application_number': application.application_number,
        'status': application.status,
    }
    if registration_info and registration_info.get('registration_number'):
        response_data['registration_number'] = registration_info['registration_number']
        response_data['student_id'] = registration_info['student'].student_id
        enroll = registration_info.get('enroll_result') or {}
        response_data['enrolled_courses'] = enroll.get('enrolled_courses', [])
        response_data['enrollment_warnings'] = enroll.get('warnings', [])
    return Response(response_data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, require_permission('admissions.decide_application')])
def admin_delete_application(request, application_id):
    try:
        application = AdmissionApplication.objects.select_related('applicant__user').get(id=application_id)
    except AdmissionApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    if application.status != 'rejected':
        return Response(
            {'error': 'Only rejected applications can be deleted.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = application.applicant.user
    user.delete()
    return Response({'message': 'Rejected application deleted.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('admissions.view_application')])
def admin_verify_document(request, application_id, doc_id):
    """Manual document verification disabled — OCR handles verification on upload."""
    return Response(
        {'error': 'Manual document verification is disabled. Documents are verified automatically by OCR on upload.'},
        status=status.HTTP_403_FORBIDDEN,
    )


