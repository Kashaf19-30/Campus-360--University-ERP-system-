"""
Create BSCS teacher credentials (teacher9@gmail.com onward), one teacher per course.

  python manage.py seed_bscs_teachers
  python manage.py seed_bscs_teachers --start 9 --password 'Abdullah@321'
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User, Role, UserRole
from academics.models import Department, DegreeProgram, ProgramCourse
from faculty.models import Designation, Faculty, EmployeeProfile, FacultyCourseAssignment
from faculty.assignment_utils import assign_faculty_to_course


DEFAULT_PASSWORD = 'Abdullah@321'
DEFAULT_OFFICE_FLOOR = '3rd'
DEFAULT_OFFICE_HOURS = '10 to 2'


class Command(BaseCommand):
    help = 'Create teacher credentials for unassigned BSCS courses (teacher9@gmail.com onward).'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=9, help='First teacher index (default: 9)')
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Password for all teachers')
        parser.add_argument('--office-floor', default=DEFAULT_OFFICE_FLOOR)
        parser.add_argument('--office-hours', default=DEFAULT_OFFICE_HOURS)
        parser.add_argument('--program-code', default='BSCS')

    @transaction.atomic
    def handle(self, *args, **options):
        program_code = options['program_code']
        start_index = options['start']
        password = options['password']
        office_floor = options['office_floor']
        office_hours = options['office_hours']

        department = Department.objects.filter(department_code='FCIT').first()
        if not department:
            self.stderr.write(self.style.ERROR('FCIT department not found. Run seed_admission_programs first.'))
            return

        program = DegreeProgram.objects.filter(
            program_code=program_code, department=department,
        ).first()
        if not program:
            self.stderr.write(self.style.ERROR(f'{program_code} program not found.'))
            return

        designation = Designation.objects.first()
        if not designation:
            designation = Designation.objects.create(designation_title='Lecturer')

        teacher_role, _ = Role.objects.get_or_create(
            role_name='Teacher',
            defaults={'description': 'Teacher role'},
        )

        program_courses = (
            ProgramCourse.objects.filter(program=program)
            .select_related('course')
            .order_by('semester_number', 'course__course_code')
        )

        assigned_course_ids = set(
            FacultyCourseAssignment.objects.filter(
                program=program, is_active=True,
            ).values_list('course_id', flat=True)
        )

        unassigned = [pc for pc in program_courses if pc.course_id not in assigned_course_ids]
        if not unassigned:
            self.stdout.write(self.style.SUCCESS(f'All {program_code} courses already have teachers.'))
            return

        self.stdout.write(
            f'Creating teachers for {len(unassigned)} unassigned {program_code} course(s) '
            f'starting at teacher{start_index}@gmail.com'
        )

        joining_date = timezone.now().date()
        year = joining_date.year
        created_count = 0
        skipped_count = 0
        teacher_index = start_index

        for pc in unassigned:
            course = pc.course
            email = f'teacher{teacher_index}@gmail.com'
            username = f'teacher{teacher_index}'

            while User.objects.filter(email=email).exists() or User.objects.filter(username=username).exists():
                teacher_index += 1
                email = f'teacher{teacher_index}@gmail.com'
                username = f'teacher{teacher_index}'

            if FacultyCourseAssignment.objects.filter(
                program=program, course=course, is_active=True,
            ).exists():
                skipped_count += 1
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='teacher',
            )
            UserRole.objects.create(user=user, role=teacher_role)

            count = Faculty.objects.count()
            emp_code = f'FAC-{year}-{str(count + 1).zfill(4)}'
            cnic_base = '0000000000000'
            cnic = cnic_base if not EmployeeProfile.objects.filter(cnic=cnic_base).exists() else f'{cnic_base[:9]}{count + 1:04d}'

            faculty = Faculty.objects.create(
                user=user,
                department=department,
                program=program,
                designation=designation,
                employee_code=emp_code,
                qualification='Master',
                joining_date=joining_date,
                employment_type='permanent',
                status='active',
                office_floor=office_floor,
                office_hours=office_hours,
                profile_completed=False,
            )
            EmployeeProfile.objects.create(
                employee_id=faculty.faculty_id,
                employee_type='faculty',
                cnic=cnic,
                date_of_birth='2000-01-01',
                gender='Male',
                phone_number='03000000000',
                emergency_contact_name='N/A',
                emergency_contact_phone='03000000000',
                emergency_contact_relation='Parent',
                current_address='N/A',
                permanent_address='N/A',
            )
            assign_faculty_to_course(faculty, program, course)

            self.stdout.write(
                self.style.SUCCESS(
                    f'  {email} -> {course.course_code} ({course.course_name}) [sem {pc.semester_number}]'
                )
            )
            created_count += 1
            teacher_index += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created {created_count} teacher(s), skipped {skipped_count}. '
                f'Password: {password!r}, office: {office_floor!r}, hours: {office_hours!r}'
            )
        )
