from django.core.management.base import BaseCommand
from academics.models import Department, DegreeProgram
from academics.admission_programs import ADMISSION_DEPARTMENTS, DEFAULT_PROGRAM_FIELDS


class Command(BaseCommand):
    help = 'Seed departments and degree programs for admissions'

    def handle(self, *args, **options):
        created_depts = 0
        created_programs = 0
        updated_programs = 0

        for dept_data in ADMISSION_DEPARTMENTS:
            department, dept_created = Department.objects.update_or_create(
                department_code=dept_data['department_code'],
                defaults={
                    'department_name': dept_data['department_name'],
                    'is_active': True,
                },
            )
            if dept_created:
                created_depts += 1

            for prog in dept_data['programs']:
                duration = prog.get('duration_years', 4)
                defaults = {
                    **DEFAULT_PROGRAM_FIELDS,
                    'department': department,
                    'program_name': prog['program_name'],
                    'degree_level': prog.get('degree_level', 'BS'),
                    'duration_years': duration,
                    'total_semesters': duration * 2,
                    'total_credit_hours': 250 if duration >= 5 else 130,
                    'is_active': True,
                    'accepting_admissions': True,
                }
                _, created = DegreeProgram.objects.update_or_create(
                    program_code=prog['program_code'],
                    defaults=defaults,
                )
                if created:
                    created_programs += 1
                else:
                    updated_programs += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created_depts} departments created, '
            f'{created_programs} programs created, {updated_programs} programs updated.'
        ))
