"""One-off: delete student15@gmail.com and provision student16@gmail.com."""
import os
import sys
import uuid
from decimal import Decimal

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from accounts.rbac import ensure_user_role_for_type
from admissions.models import (
    AcademicRecord,
    AdmissionApplication,
    AdmissionDecision,
    Applicant,
    ApplicantDocument,
    ProgramPreference,
)
from admissions.views import _register_approved_student
from academics.models import CourseOffering, DegreeProgram, Semester
from enrollments.models import CourseRegistration
from enrollments.promotion import enroll_student_for_semester
from enrollments.repeat_utils import sync_offering_enrolled_count
from fees.models import Challan
from students.models import Student

PASSWORD = 'Abdullah@321'
DELETE_EMAIL = 'student15@gmail.com'
CREATE_EMAIL = 'student16@gmail.com'
CREATE_USERNAME = 'student16'
CREATE_CNIC = '3520212345816'
CREATE_NUM = 16

REQUIRED_PERSONAL_DOCS = ('cnic_front', 'cnic_back', 'domicile', 'photograph')
ACADEMIC_DOCS = ('matric_marksheet', 'inter_marksheet')


def delete_student_by_email(email: str) -> None:
    user = User.objects.filter(email=email).first()
    if not user:
        print(f'Delete: {email} not found — skipped.')
        return

    student = Student.objects.filter(user=user).first()
    offering_ids = []
    if student:
        offering_ids = list(
            CourseRegistration.objects.filter(student=student).values_list('offering_id', flat=True)
        )
        Challan.objects.filter(student=student).delete()

    applicant = Applicant.objects.filter(user=user).first()
    if applicant:
        apps = AdmissionApplication.objects.filter(applicant=applicant)
        AdmissionDecision.objects.filter(application__in=apps).delete()

    if student:
        print(
            f'Delete: {email} -> {student.registration_number} '
            f'({CourseRegistration.objects.filter(student=student).count()} regs before user delete)'
        )

    user.delete()
    print(f'Delete: removed user {email}')

    for offering_id in {oid for oid in offering_ids if oid}:
        offering = CourseOffering.objects.filter(pk=offering_id).first()
        if offering:
            sync_offering_enrolled_count(offering)
            print(f'Delete: synced offering #{offering_id} enrolled_count={offering.enrolled_count}')


def ensure_academic_records(applicant):
    defaults = {
        'matric': {
            'authority': 'BISE Sargodha',
            'qualification': 'Matriculation',
            'institute': 'Govt High School',
            'start_year': 2018,
            'end_year': 2020,
            'grading_system': 'marks',
            'obtained': Decimal('900'),
            'total': Decimal('1000'),
        },
        'inter': {
            'authority': 'BISE Sargodha',
            'qualification': 'Intermediate',
            'institute': 'Govt College',
            'start_year': 2020,
            'end_year': 2022,
            'grading_system': 'marks',
            'obtained': Decimal('900'),
            'total': Decimal('1100'),
        },
    }
    for level, data in defaults.items():
        AcademicRecord.objects.get_or_create(
            applicant=applicant,
            qualification_level=level,
            defaults=data,
        )


def ensure_verified_documents(applicant):
    placeholder = 'seed/test-document.pdf'
    for doc_type in (*REQUIRED_PERSONAL_DOCS, *ACADEMIC_DOCS):
        ApplicantDocument.objects.update_or_create(
            applicant=applicant,
            document_type=doc_type,
            defaults={
                'file_name': f'{doc_type}.pdf',
                'file_path': placeholder,
                'file_size': 2048,
                'file_type': 'application/pdf',
                'is_verified': True,
                'verified_at': timezone.now(),
                'verification_remarks': 'Seeded for test student provisioning.',
            },
        )


def provision_student(email, username, cnic, num, admin, program, semester) -> str:
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'user_type': 'applicant',
            'is_active': True,
        },
    )
    user.username = username
    user.set_password(PASSWORD)
    user.is_active = True
    user.save()

    applicant, _ = Applicant.objects.get_or_create(
        user=user,
        defaults={
            'first_name': 'Abdullah',
            'last_name': f'Test{num}',
            'father_name': 'Test Father',
            'cnic': cnic,
            'date_of_birth': timezone.now().date().replace(year=2005, month=1, day=15),
            'gender': 'male',
            'phone': f'0300123456{num}',
            'perm_address': 'University of Sialkot Campus',
            'guardian_name': 'Test Guardian',
            'guardian_cnic': cnic,
        },
    )
    applicant.first_name = 'Abdullah'
    applicant.last_name = f'Test{num}'
    applicant.cnic = cnic
    applicant.phone = f'0300123456{num}'
    applicant.perm_address = 'University of Sialkot Campus'
    applicant.save()

    ensure_academic_records(applicant)
    ensure_verified_documents(applicant)

    app = AdmissionApplication.objects.filter(applicant=applicant).exclude(status='rejected').first()
    if not app:
        app = AdmissionApplication.objects.create(
            applicant=applicant,
            program=program,
            application_number=f'APP-TEST-{num}-{uuid.uuid4().hex[:6].upper()}',
            session_type='spring',
            session_year=timezone.now().year,
            status='challan_pending',
            challan_paid=False,
            admission_challan_amount=Decimal('15000'),
            admission_challan_number=f'ADM-{num}-{uuid.uuid4().hex[:6].upper()}',
        )
        ProgramPreference.objects.get_or_create(
            application=app,
            program=program,
            defaults={'preference_order': 1},
        )

    app.program = program
    app.challan_paid = True
    app.admission_challan_amount = app.admission_challan_amount or Decimal('15000')
    if app.status in ('challan_pending', 'pending', 'draft'):
        app.status = 'under_review'
    app.save()

    student = Student.objects.filter(user=user).first()
    if not student:
        app.status = 'approved'
        app.is_documents_verified = True
        app.save(update_fields=['status', 'is_documents_verified'])
        reg = _register_approved_student(app, admin)
        if reg.get('error'):
            raise RuntimeError(f'{email}: {reg["error"]}')
        student = reg['student']

    user.user_type = 'student'
    user.save(update_fields=['user_type'])
    ensure_user_role_for_type(user)

    student.current_semester = 1
    student.program = program
    student.status = 'active'
    student.save(update_fields=['current_semester', 'program', 'status'])

    if app.status != 'registered':
        app.status = 'registered'
        app.save(update_fields=['status'])

    challan = Challan.objects.filter(student=student, semester=semester).first()
    if not challan:
        enroll_student_for_semester(student, semester, performed_by=admin)
        challan = Challan.objects.filter(student=student, semester=semester).first()

    if challan and challan.status != 'paid':
        challan.status = 'paid'
        challan.amount_paid = challan.total_amount
        challan.save(update_fields=['status', 'amount_paid'])

    enroll_result = enroll_student_for_semester(student, semester, performed_by=admin)
    courses = list(
        CourseRegistration.objects.filter(
            student=student,
            enrollment__semester=semester,
            status='registered',
        ).select_related('offering', 'course')
    )
    course_lines = [
        f'{r.course.course_code}(offering #{r.offering_id})'
        for r in courses
    ]

    return (
        f'{email} -> {student.registration_number} | '
        f'semester={student.current_semester} | fee=paid | '
        f'enrolled={course_lines} | warnings={enroll_result.get("warnings") or []}'
    )


@transaction.atomic
def main():
    admin = User.objects.filter(user_type='admin', is_active=True).first()
    if not admin:
        raise SystemExit('No admin user found.')

    program = DegreeProgram.objects.filter(program_code='BSCS', is_active=True).first()
    semester = Semester.objects.filter(is_current=True).first()
    if not program or not semester:
        raise SystemExit('Missing BSCS program or current semester.')

    delete_student_by_email(DELETE_EMAIL)
    summary = provision_student(
        CREATE_EMAIL, CREATE_USERNAME, CREATE_CNIC, CREATE_NUM, admin, program, semester,
    )
    print('Create:', summary)


if __name__ == '__main__':
    main()
