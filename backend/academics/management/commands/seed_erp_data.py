"""
Seed ERP reference data: semester, courses, curriculum links, fee structures,
exam types, grade scale, and notification types.

Academic terms (Semester rows) are created here — not via the admin dashboard.
Re-run this command to refresh the current term dates. Superusers can also
use the semesters API for maintenance.

Course offerings are NOT seeded; they are created automatically when students
enroll (teacher must be assigned in Teacher Course Management first).

Does NOT create demo teachers or students — create those via Admin → Credentials.

Run after migrations and seed_admission_programs:
  python manage.py seed_admission_programs
  python manage.py seed_erp_data
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from academics.models import Department, DegreeProgram, Semester, Course, ProgramCourse
from academics.admission_programs import ADMISSION_DEPARTMENTS
from faculty.models import Designation
from complaints.models import ComplaintCategory
from fees.models import FeeStructure
from notifications.models import NotificationType

UNIVERSITY_COURSES = [
    {'course_code': 'ENG101', 'course_name': 'English Composition', 'credit_hours': 3, 'course_type': 'university_requirement'},
    {'course_code': 'ISL101', 'course_name': 'Islamic Studies', 'credit_hours': 2, 'course_type': 'university_requirement'},
    {'course_code': 'PAK101', 'course_name': 'Pakistan Studies', 'credit_hours': 2, 'course_type': 'university_requirement'},
]

DEPT_SEM1_COURSES = {
    'FCIT': [
        {'course_code': 'CS101', 'course_name': 'Introduction to Programming', 'credit_hours': 3, 'course_type': 'core'},
        {'course_code': 'CS102', 'course_name': 'Discrete Structures', 'credit_hours': 3, 'course_type': 'core'},
    ],
    'FENG': [
        {'course_code': 'ENGF101', 'course_name': 'Engineering Fundamentals', 'credit_hours': 3, 'course_type': 'core'},
        {'course_code': 'MTH101', 'course_name': 'Calculus I', 'credit_hours': 3, 'course_type': 'core'},
    ],
    'FMHS': [
        {'course_code': 'ANAT101', 'course_name': 'Human Anatomy', 'credit_hours': 4, 'course_type': 'core'},
        {'course_code': 'PHYS101', 'course_name': 'Biophysics', 'credit_hours': 3, 'course_type': 'core'},
    ],
    'FBMS': [
        {'course_code': 'MGT101', 'course_name': 'Principles of Management', 'credit_hours': 3, 'course_type': 'core'},
        {'course_code': 'ACC101', 'course_name': 'Financial Accounting', 'credit_hours': 3, 'course_type': 'core'},
    ],
    'FASE': [
        {'course_code': 'SOC101', 'course_name': 'Introduction to Sociology', 'credit_hours': 3, 'course_type': 'core'},
        {'course_code': 'PSY101', 'course_name': 'Introduction to Psychology', 'credit_hours': 3, 'course_type': 'core'},
    ],
}

COMPLAINT_CATEGORIES = [
    ('Academic', 'Issues related to courses, grades, or faculty'),
    ('Administrative', 'Registration, documents, or office services'),
    ('Facilities', 'Campus infrastructure, labs, or hostel'),
    ('Financial', 'Fee challans or payments'),
    ('Harassment', 'Conduct or safety concerns'),
]

NOTIFICATION_TYPES = [
    ('Registration', 'Student registration and enrollment'),
    ('Academic', 'Academic updates and announcements'),
    ('Financial', 'Fee and payment notifications'),
    ('General', 'General campus notifications'),
]

from academics.curriculum_cs_programs import PROGRAM_CURRICULA, DEPARTMENT_CODE, resolve_elective_course
from academics.prerequisite_sync import sync_all_prerequisites, sync_program_prerequisites


class Command(BaseCommand):
    help = 'Seed ERP reference data (no demo teachers or students)'

    def _ensure_course(self, department, course_data):
        course, created = Course.objects.update_or_create(
            course_code=course_data['course_code'],
            defaults={
                'department': department,
                'course_name': course_data['course_name'],
                'credit_hours': course_data['credit_hours'],
                'theory_credit_hours': course_data.get('theory_credit_hours', course_data['credit_hours']),
                'lab_credit_hours': course_data.get('lab_credit_hours', 0),
                'course_type': course_data['course_type'],
                'is_active': True,
            },
        )
        return course, created

    def _prune_stale_program_courses(self, program, program_code):
        """Remove ProgramCourse rows not in canonical PROGRAM_CURRICULA."""
        from academics.models import ProgramCourse

        expected = set()
        for sem_num, course_list in PROGRAM_CURRICULA.get(program_code, {}).items():
            for course_data in course_list:
                course_data = resolve_elective_course(program_code, course_data)
                expected.add((sem_num, course_data['course_code']))

        stale = []
        for pc in ProgramCourse.objects.filter(program=program).select_related('course'):
            key = (pc.semester_number, pc.course.course_code)
            if key not in expected:
                stale.append(pc.program_course_id)

        if stale:
            ProgramCourse.objects.filter(program_course_id__in=stale).delete()

    def handle(self, *args, **options):
        today = timezone.now().date()
        year = today.year

        Semester.objects.filter(is_current=True).update(is_current=False)
        # Single internal active session — curriculum semester is shown in the UI instead.
        end_date = today + timedelta(days=365 * 8)
        semester, _ = Semester.objects.update_or_create(
            semester_name='Active Session',
            defaults={
                'academic_year': year,
                'semester_type': 'spring',
                'start_date': today,
                'end_date': end_date,
                'mid_term_cutoff_date': today + timedelta(days=180),
                'marks_grace_end_date': end_date + timedelta(days=7),
                'is_current': True,
            },
        )
        # Rename legacy Spring/Fall rows so they are not shown as calendar terms.
        for legacy in Semester.objects.exclude(semester_id=semester.semester_id):
            name = legacy.semester_name or ''
            if name.startswith(('Spring ', 'Fall ', 'Summer ')):
                legacy.semester_name = f'Legacy Session {legacy.semester_id}'
                legacy.is_current = False
                legacy.save(update_fields=['semester_name', 'is_current'])

        from examinations.models import ExamType
        DEFAULT_EXAM_TYPES = [
            ('Continuous Assessment', 30, 'pre_mid'),
            ('Mid Term', 30, 'mid_term'),
            ('Final Term', 40, 'final'),
        ]
        for type_name, weight, period in DEFAULT_EXAM_TYPES:
            ExamType.objects.update_or_create(
                type_name=type_name,
                defaults={'weightage_percentage': weight, 'marks_period': period},
            )

        from examinations.models import Grade
        from decimal import Decimal
        GRADE_SCALE = [
            ('A+', Decimal('90'), Decimal('100'), Decimal('4.00'), 'pass', 'Outstanding'),
            ('A', Decimal('85'), Decimal('89.99'), Decimal('4.00'), 'pass', 'Excellent'),
            ('A-', Decimal('80'), Decimal('84.99'), Decimal('3.70'), 'pass', 'Very Good'),
            ('B+', Decimal('75'), Decimal('79.99'), Decimal('3.30'), 'pass', 'Good'),
            ('B', Decimal('70'), Decimal('74.99'), Decimal('3.00'), 'pass', 'Above Average'),
            ('B-', Decimal('65'), Decimal('69.99'), Decimal('2.70'), 'pass', 'Average'),
            ('C+', Decimal('60'), Decimal('64.99'), Decimal('2.30'), 'pass', 'Satisfactory'),
            ('C', Decimal('55'), Decimal('59.99'), Decimal('2.00'), 'pass', 'Pass'),
            ('C-', Decimal('50'), Decimal('54.99'), Decimal('1.70'), 'pass', 'Minimum Pass'),
            ('F', Decimal('0'), Decimal('49.99'), Decimal('0.00'), 'fail', 'Fail'),
        ]
        for letter, min_pct, max_pct, points, status, desc in GRADE_SCALE:
            Grade.objects.update_or_create(
                grade_letter=letter,
                defaults={
                    'min_percentage': min_pct,
                    'max_percentage': max_pct,
                    'grade_points': points,
                    'status': status,
                    'description': desc,
                },
            )

        from academics.models import AcademicPolicy
        AcademicPolicy.objects.get_or_create(pk=1)

        Designation.objects.get_or_create(
            designation_title='Assistant Professor',
            defaults={'designation_level': 3, 'job_description': 'Faculty member'},
        )

        fcit_dept = Department.objects.filter(department_code='FCIT').first()
        if not fcit_dept:
            self.stdout.write(self.style.WARNING('Run seed_admission_programs first.'))
            return

        finance_user, finance_created = User.objects.get_or_create(
            email='finance@campus360.edu',
            defaults={
                'username': 'demo.finance',
                'user_type': 'finance_officer',
                'is_active': True,
            },
        )
        if finance_created:
            finance_user.set_password('Finance@123')
            finance_user.save()

        courses_created = 0
        program_links = 0

        uni_courses = []
        for course_data in UNIVERSITY_COURSES:
            course, created = self._ensure_course(fcit_dept, course_data)
            if created:
                courses_created += 1
            uni_courses.append(course)

        for dept_data in ADMISSION_DEPARTMENTS:
            dept_code = dept_data['department_code']
            department = Department.objects.filter(department_code=dept_code).first()
            if not department:
                continue

            dept_course_objs = list(uni_courses)
            for course_data in DEPT_SEM1_COURSES.get(dept_code, []):
                course, created = self._ensure_course(department, course_data)
                if created:
                    courses_created += 1
                dept_course_objs.append(course)

            programs = DegreeProgram.objects.filter(department=department, is_active=True)
            curriculum_program_codes = set(PROGRAM_CURRICULA.keys())
            for program in programs:
                if department.department_code == DEPARTMENT_CODE and program.program_code in curriculum_program_codes:
                    # FCIT computing programs use PROGRAM_CURRICULA only (see below).
                    if not program.fee_per_semester:
                        program.fee_per_semester = 75000
                        program.save(update_fields=['fee_per_semester'])
                    FeeStructure.objects.update_or_create(
                        program=program,
                        semester_number=1,
                        fee_type='semester_fee',
                        effective_from=today,
                        defaults={'amount': program.fee_per_semester or 75000},
                    )
                    continue

                if not program.fee_per_semester:
                    program.fee_per_semester = 75000
                    program.save(update_fields=['fee_per_semester'])

                FeeStructure.objects.update_or_create(
                    program=program,
                    semester_number=1,
                    fee_type='semester_fee',
                    effective_from=today,
                    defaults={'amount': program.fee_per_semester or 75000},
                )

                for course in dept_course_objs:
                    _, linked = ProgramCourse.objects.update_or_create(
                        program=program,
                        course=course,
                        semester_number=1,
                        defaults={'is_core': True},
                    )
                    if linked:
                        program_links += 1

        for name, desc in COMPLAINT_CATEGORIES:
            cat, created = ComplaintCategory.objects.get_or_create(
                category_name=name,
                defaults={'description': desc},
            )
            if not created and cat.description != desc:
                cat.description = desc
                cat.save(update_fields=['description'])

        for type_name, desc in NOTIFICATION_TYPES:
            NotificationType.objects.get_or_create(
                type_name=type_name,
                defaults={'description': desc},
            )

        cs_links = 0
        fcit = Department.objects.filter(department_code=DEPARTMENT_CODE).first()
        if fcit:
            for program_code, semesters in PROGRAM_CURRICULA.items():
                program = DegreeProgram.objects.filter(program_code=program_code).first()
                if not program:
                    continue
                for sem_num, course_list in semesters.items():
                    for course_data in course_list:
                        course_data = resolve_elective_course(program_code, course_data)
                        course, _ = self._ensure_course(fcit, course_data)
                        _, linked = ProgramCourse.objects.update_or_create(
                            program=program,
                            course=course,
                            semester_number=sem_num,
                            defaults={'is_core': course_data['course_type'] == 'core'},
                        )
                        if linked:
                            cs_links += 1
                    self._prune_stale_program_courses(program, program_code)

        self.stdout.write(self.style.SUCCESS(
            f'ERP seed complete: semester={semester.semester_name}, '
            f'courses={courses_created}, program_course_links={program_links}, '
            f'cs_course_links={cs_links}, '
            f'prerequisites={sync_all_prerequisites()}, program_prerequisites={sync_program_prerequisites()}'
        ))
