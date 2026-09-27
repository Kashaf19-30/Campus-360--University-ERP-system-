import uuid
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.permissions import require_permission, require_any_permission, IsFinanceOfficer
from students.models import Student
from .models import FeeStructure, Challan
from .serializers import FeeStructureSerializer, ChallanSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission('fees.manage_fees', 'fees.view_fees')])
def list_fee_structures(request):
    structures = FeeStructure.objects.select_related('program', 'program__department').all().order_by(
        'program__department__department_name', 'program__program_name', 'semester_number', '-effective_from',
    )
    program = request.query_params.get('program')
    fee_type = request.query_params.get('fee_type')
    if program:
        structures = structures.filter(program__program_id=program)
    if fee_type:
        structures = structures.filter(fee_type=fee_type)
    return Response(FeeStructureSerializer(structures, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('fees.manage_fees')])
def create_fee_structure(request):
    serializer = FeeStructureSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, require_permission('fees.manage_fees')])
def delete_fee_structure(request, structure_id):
    try:
        structure = FeeStructure.objects.get(structure_id=structure_id)
    except FeeStructure.DoesNotExist:
        return Response({'error': 'Fee structure not found.'}, status=status.HTTP_404_NOT_FOUND)
    structure.delete()
    return Response({'message': 'Fee structure deleted.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('fees.view_own_fees')])
def my_challans(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student record not found.'}, status=status.HTTP_404_NOT_FOUND)
    challans = Challan.objects.filter(student=student).select_related('semester')
    return Response(ChallanSerializer(challans, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFinanceOfficer])
def generate_challan(request):
    serializer = ChallanSerializer(data=request.data)
    if serializer.is_valid():
        challan_number = f"CH-{timezone.now().year}-{str(uuid.uuid4().int)[:6]}"
        serializer.save(
            challan_number=challan_number,
            generated_by=request.user
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsFinanceOfficer])
def list_challans(request):
    challans = Challan.objects.select_related('student', 'semester').all()
    student = request.query_params.get('student')
    status_filter = request.query_params.get('status')
    if student:
        challans = challans.filter(student__student_id=student)
    if status_filter:
        challans = challans.filter(status=status_filter)
    return Response(ChallanSerializer(challans, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFinanceOfficer])
def generate_semester_challans(request):
    """Generate fee challans for all active students in a semester."""
    semester_id = request.data.get('semester_id')
    sem_num = request.data.get('semester_number')
    if not semester_id:
        return Response({'error': 'semester_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    from academics.models import Semester
    try:
        semester = Semester.objects.get(semester_id=semester_id)
    except Semester.DoesNotExist:
        return Response({'error': 'Semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    from datetime import timedelta
    created = 0
    skipped = 0
    for student in Student.objects.filter(status='active').select_related('program'):
        sn = sem_num or student.current_semester
        if Challan.objects.filter(
            student=student, semester=semester, curriculum_semester=sn,
        ).exists():
            skipped += 1
            continue
        fee_structure = FeeStructure.objects.filter(
            program=student.program, semester_number=sn, fee_type='semester_fee',
        ).order_by('-effective_from').first()
        amount = fee_structure.amount if fee_structure else (student.program.fee_per_semester or 75000)
        Challan.objects.create(
            challan_number=f"CH-{timezone.now().year}-{str(uuid.uuid4().int)[:6]}",
            student=student,
            semester=semester,
            curriculum_semester=sn,
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=amount,
            generated_by=request.user,
        )
        created += 1

    from accounts.audit import log_audit
    log_audit(request, 'generate_challans', 'semester', semester.semester_id, new_value={'created': created})
    return Response({'message': f'Generated {created} challans.', 'created': created, 'skipped': skipped})


def _user_is_finance(user):
    from accounts.rbac import user_has_permission
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user_has_permission(user, 'system.admin_access'):
        return True
    if user.user_type != 'finance_officer':
        return False
    return (
        user_has_permission(user, 'fees.view_fees')
        or user_has_permission(user, 'fees.manage_fees')
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('fees.view_own_fees')])
def download_my_challan(request, challan_id):
    if request.user.user_type != 'student':
        return Response({'error': 'Students only.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
        challan = Challan.objects.select_related('semester', 'student__program', 'student__user').get(
            challan_id=challan_id, student=student,
        )
    except (Student.DoesNotExist, Challan.DoesNotExist):
        return Response({'error': 'Challan not found.'}, status=status.HTTP_404_NOT_FOUND)

    from django.http import HttpResponse
    from .challan_pdf import generate_semester_challan_pdf
    pdf = generate_semester_challan_pdf(challan)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Semester-Challan-{challan.challan_number}.pdf"'
    return response


def _fee_challan_for_student(student, academic_semester=None, semester_id=None):
    """Challan finance should collect — pending promotion target or current curriculum sem."""
    from examinations.models import Result
    from academics.session_utils import get_active_session

    academic_semester = academic_semester or get_active_session()
    fee_curriculum = student.current_semester
    if academic_semester:
        pending = Result.objects.filter(
            student=student,
            semester=academic_semester,
            promotion_pending=True,
        ).first()
        if pending and pending.pending_promotion_semester:
            fee_curriculum = pending.pending_promotion_semester

    challan_qs = Challan.objects.filter(
        student=student,
        curriculum_semester=fee_curriculum,
    )
    if semester_id:
        challan_qs = challan_qs.filter(semester__semester_id=semester_id)
    return challan_qs.order_by('-created_at').first(), fee_curriculum


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finance_dashboard(request):
    """Finance officer overview: new admissions + enrolled student fee status."""
    if not _user_is_finance(request.user):
        return Response({'error': 'Finance officer access only.'}, status=status.HTTP_403_FORBIDDEN)

    from admissions.models import AdmissionApplication
    from examinations.models import Result
    from academics.session_utils import get_active_session
    from django.db.models import Q

    academic_semester = get_active_session()
    semester_id = request.query_params.get('semester')
    dept_id = request.query_params.get('department')
    program_id = request.query_params.get('program')
    sem_num = request.query_params.get('curriculum_semester')

    new_admissions = AdmissionApplication.objects.filter(
        status='challan_pending',
    ).select_related('applicant__user', 'program', 'program__department').order_by('-created_at')

    if dept_id:
        new_admissions = new_admissions.filter(program__department__department_id=dept_id)
    if program_id:
        new_admissions = new_admissions.filter(program__program_id=program_id)

    admissions_rows = [{
        'application_id': app.id,
        'application_number': app.application_number,
        'applicant_name': app.applicant.user.username if app.applicant_id else '',
        'program_name': app.program.program_name if app.program_id else '—',
        'department_name': app.program.department.department_name if app.program_id and app.program.department_id else '—',
        'challan_number': app.admission_challan_number,
        'challan_amount': str(app.admission_challan_amount or ''),
        'challan_paid': app.challan_paid,
        'status': app.status,
    } for app in new_admissions]

    students = Student.objects.filter(status='active').select_related(
        'user', 'program', 'program__department',
    )
    if program_id:
        students = students.filter(program__program_id=program_id)
    if dept_id:
        students = students.filter(program__department__department_id=dept_id)
    if sem_num:
        try:
            sn = int(sem_num)
            pending_ids = Result.objects.filter(
                semester=academic_semester,
                promotion_pending=True,
                pending_promotion_semester=sn,
            ).values_list('student_id', flat=True)
            students = students.filter(Q(current_semester=sn) | Q(student_id__in=pending_ids))
        except (TypeError, ValueError):
            pass

    enrolled_rows = []
    paid_count = 0
    unpaid_count = 0
    for student in students.order_by('registration_number'):
        challan, fee_curriculum = _fee_challan_for_student(
            student, academic_semester, semester_id,
        )
        fee_status = challan.status if challan else 'no_challan'
        if fee_status == 'paid':
            paid_count += 1
        else:
            unpaid_count += 1
        enrolled_rows.append({
            'student_id': student.student_id,
            'registration_number': student.registration_number,
            'student_name': student.user.username,
            'program_name': student.program.program_name,
            'department_name': student.program.department.department_name,
            'current_semester': student.current_semester,
            'challan_id': challan.challan_id if challan else None,
            'challan_number': challan.challan_number if challan else '',
            'curriculum_semester': fee_curriculum,
            'fee_status': fee_status,
            'total_amount': str(challan.total_amount) if challan else '',
            'promotion_pending': bool(
                Result.objects.filter(
                    student=student,
                    semester=academic_semester,
                    promotion_pending=True,
                ).exists()
            ),
        })

    return Response({
        'new_admissions': admissions_rows,
        'enrolled_students': enrolled_rows,
        'summary': {
            'pending_admissions': len(admissions_rows),
            'enrolled_total': len(enrolled_rows),
            'fees_paid': paid_count,
            'fees_unpaid': unpaid_count,
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_admission_challan_paid(request, application_id):
    """Finance marks admission fee paid → notifies admin for review."""
    if not _user_is_finance(request.user):
        return Response({'error': 'Finance officer access only.'}, status=status.HTTP_403_FORBIDDEN)

    from admissions.models import AdmissionApplication

    try:
        application = AdmissionApplication.objects.select_related('applicant__user', 'program').get(
            id=application_id,
        )
    except AdmissionApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    if application.status != 'challan_pending':
        return Response({'error': 'Application is not awaiting fee payment.'}, status=status.HTTP_400_BAD_REQUEST)

    paid = request.data.get('paid', True)
    if paid:
        application.challan_paid = True
        application.status = 'under_review'
        application.save(update_fields=['challan_paid', 'status'])
        from notifications.system_notify import notify_admins, notify_user
        notify_admins(
            'Admissions',
            'Admission fee received',
            (
                f'Application {application.application_number} fee marked paid. '
                'Ready for admin review.'
            ),
        )
        notify_user(
            application.applicant.user,
            'Admissions',
            'Admission fee confirmed',
            (
                f'Your admission fee for application {application.application_number} '
                'has been confirmed. Your application is now under admin review.'
            ),
        )
        return Response({'message': 'Admission fee marked paid. Admin and applicant notified.'})

    application.challan_paid = False
    application.status = 'challan_pending'
    application.save(update_fields=['challan_paid', 'status'])
    return Response({'message': 'Admission marked not paid.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_student_challan_paid(request, challan_id):
    """Finance marks a semester challan as paid."""
    if not _user_is_finance(request.user):
        return Response({'error': 'Finance officer access only.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        challan = Challan.objects.select_related('student').get(challan_id=challan_id)
    except Challan.DoesNotExist:
        return Response({'error': 'Challan not found.'}, status=status.HTTP_404_NOT_FOUND)

    paid = request.data.get('paid', True)
    enrollment_result = None

    if paid:
        from enrollments.promotion import enroll_student_for_semester, try_complete_pending_promotion
        from notifications.system_notify import notify_user
        try:
            with transaction.atomic():
                challan.amount_paid = challan.total_amount
                challan.status = 'paid'
                challan.save(update_fields=['amount_paid', 'status'])
                promo = try_complete_pending_promotion(
                    challan.student,
                    challan.semester,
                    challan.curriculum_semester,
                    performed_by=request.user,
                )
                if promo is not None:
                    enrollment_result = promo
                    challan.student.refresh_from_db()
                else:
                    enrollment_result = enroll_student_for_semester(
                        challan.student,
                        challan.semester,
                        performed_by=request.user,
                        curriculum_semester=challan.curriculum_semester,
                    )
        except Exception as exc:
            return Response(
                {'error': f'Payment recorded failed: enrollment error — {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        courses = enrollment_result.get('enrolled_courses') or []
        if enrollment_result.get('promoted'):
            notify_user(
                challan.student.user,
                'Academic',
                'Semester promotion complete',
                (
                    f'Semester {challan.curriculum_semester} fee received. '
                    f'You are now in curriculum semester {challan.student.current_semester}. '
                    f'Registered courses: {", ".join(courses) if courses else "see My Enrollments"}.'
                ),
                priority='high',
            )
        elif courses:
            notify_user(
                challan.student.user,
                'Registration',
                'Course registration complete',
                f'Semester fee received. Registered courses: {", ".join(courses)}.',
                priority='high',
            )
        elif enrollment_result.get('registration_blocked'):
            notify_user(
                challan.student.user,
                'Finance',
                'Registration still blocked',
                enrollment_result.get('warnings', ['Contact Finance Office.'])[0],
                priority='high',
            )
    else:
        challan.amount_paid = 0
        challan.status = 'pending'
        challan.save(update_fields=['amount_paid', 'status'])
        from enrollments.promotion import revoke_unpaid_curriculum_registrations
        revoke_unpaid_curriculum_registrations(
            challan.student, challan.semester, challan.curriculum_semester,
        )
        from notifications.system_notify import notify_user
        notify_user(
            challan.student.user,
            'Finance',
            'Registration suspended',
            'Semester fee marked unpaid. Course registrations for this semester have been removed. Contact the Finance Office.',
            priority='high',
        )

    return Response({
        'message': f'Challan marked {"paid" if paid else "unpaid"}.',
        'enrollment': enrollment_result,
    })