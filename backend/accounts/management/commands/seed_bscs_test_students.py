"""
Provision BSCS semester-1 test students for QA.

  python manage.py seed_bscs_test_students
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from accounts.rbac import ensure_user_role_for_type
from admissions.models import (
    AcademicRecord,
    AdmissionApplication,
    Applicant,
    ApplicantDocument,
    ProgramPreference,
)
from admissions.views import _register_approved_student
from academics.models import DegreeProgram, Semester
from enrollments.models import CourseRegistration
from enrollments.promotion import enroll_student_for_semester
from fees.models import Challan
from students.models import Student

PASSWORD = 'Abdullah@321'

TEST_STUDENTS = [
    {'email': 'student3@gmail.com', 'username': 'student3', 'cnic': '3520212345673', 'num': 3},
    {'email': 'student4@gmail.com', 'username': 'student4', 'cnic': '3520212345674', 'num': 4},
    {'email': 'student5@gmail.com', 'username': 'student5', 'cnic': '3520212345675', 'num': 5},
    {'email': 'student6@gmail.com', 'username': 'student6', 'cnic': '3520212345676', 'num': 6},
]

REQUIRED_PERSONAL_DOCS = ('cnic_front', 'cnic_back', 'domicile', 'photograph')
ACADEMIC_DOCS = ('matric_marksheet', 'inter_marksheet')


class Command(BaseCommand):
    help = 'Set up student3–6@gmail.com as BSCS semester-1 students with fees paid and courses enrolled.'

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(user_type='admin', is_active=True).first()
        if not admin:
            self.stderr.write('No admin user found. Create one first.')
            return

        program = DegreeProgram.objects.filter(program_code='BSCS', is_active=True).first()
        semester = Semester.objects.filter(is_current=True).first()
        if not program or not semester:
            self.stderr.write('Missing BSCS program or current semester. Run seed_erp_data first.')
            return

        for spec in TEST_STUDENTS:
            summary = self._provision_student(spec, admin, program, semester)
            self.stdout.write(self.style.SUCCESS(summary))

    def _provision_student(self, spec, admin, program, semester):
        email = spec['email']
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                'username': spec['username'],
                'user_type': 'applicant',
                'is_active': True,
            },
        )
        user.set_password(PASSWORD)
        user.is_active = True
        user.save(update_fields=['password', 'is_active'])

        applicant, _ = Applicant.objects.get_or_create(
            user=user,
            defaults={
                'first_name': 'Abdullah',
                'last_name': f'Test{spec["num"]}',
                'father_name': 'Test Father',
                'cnic': spec['cnic'],
                'date_of_birth': timezone.now().date().replace(year=2005, month=1, day=15),
                'gender': 'male',
                'phone': f'0300123456{spec["num"]}',
                'perm_address': 'University of Sialkot Campus',
                'guardian_name': 'Test Guardian',
                'guardian_cnic': spec['cnic'],
            },
        )
        updated = False
        for field, value in {
            'first_name': 'Abdullah',
            'last_name': f'Test{spec["num"]}',
            'cnic': spec['cnic'],
            'phone': f'0300123456{spec["num"]}',
            'perm_address': 'University of Sialkot Campus',
        }.items():
            if getattr(applicant, field) != value:
                setattr(applicant, field, value)
                updated = True
        if updated:
            applicant.save()

        self._ensure_academic_records(applicant)
        self._ensure_verified_documents(applicant)

        app = AdmissionApplication.objects.filter(applicant=applicant).exclude(status='rejected').first()
        if not app:
            app = AdmissionApplication.objects.create(
                applicant=applicant,
                program=program,
                application_number=f'APP-TEST-{spec["num"]}-{uuid.uuid4().hex[:6].upper()}',
                session_type='spring',
                session_year=timezone.now().year,
                status='challan_pending',
                challan_paid=False,
                admission_challan_amount=Decimal('15000'),
                admission_challan_number=f'ADM-{spec["num"]}-{uuid.uuid4().hex[:6].upper()}',
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
            if app.status != 'approved':
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
            ).values_list('course__course_code', flat=True)
        )

        return (
            f'{email} -> {student.registration_number} | '
            f'app={app.application_number} ({app.status}) | '
            f'admission_fee=paid | semester_fee=paid | '
            f'enrolled={courses or enroll_result.get("enrolled_courses") or []} | '
            f'warnings={enroll_result.get("warnings") or []}'
        )

    def _ensure_academic_records(self, applicant):
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

    def _ensure_verified_documents(self, applicant):
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
