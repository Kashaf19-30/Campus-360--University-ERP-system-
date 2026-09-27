"""Basic concurrency / duplicate-prevention tests."""
import threading

from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import User
from admissions.models import Applicant, AdmissionApplication
from academics.models import Department, DegreeProgram


class ConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        dept = Department.objects.create(department_code='CON', department_name='Con')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS Con', program_code='CON',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )

    def test_unique_application_numbers_under_parallel_create(self):
        errors = []
        created = []

        def create_app(i):
            try:
                user = User.objects.create_user(
                    email=f'con{i}@test.edu', username=f'con{i}', password='pass', user_type='applicant',
                )
                app = Applicant.objects.create(user=user, first_name='C', last_name=str(i))
                obj = AdmissionApplication.objects.create(
                    applicant=app, program=self.program,
                    application_number=f'APP-CON-{i:04d}', status='draft',
                )
                created.append(obj.application_number)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=create_app, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(len(created), len(set(created)))
