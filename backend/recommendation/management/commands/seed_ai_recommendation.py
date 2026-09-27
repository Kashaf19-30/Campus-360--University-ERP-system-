from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import DegreeProgram
from recommendation.models import Interest, CareerGoal, DegreeEligibility, TrendScore
from recommendation.services.program_weights import (
    CS_CODES, ENGINEERING_CODES, MEDICAL_CODES, BUSINESS_CODES, ARTS_CODES,
)

INTERESTS = [
    'Programming & Technology', 'Artificial Intelligence', 'Engineering',
    'Business & Finance', 'Healthcare', 'Psychology', 'Education',
    'Media & Communication', 'Research', 'Mathematics', 'Design & Creativity',
]

GOALS = [
    'High Salary', 'Work Abroad', 'Government Job', 'Entrepreneurship',
    'Research & Academia', 'Leadership & Management', 'Remote Work',
    'Helping People', 'Job Security',
]

ELIGIBILITY = {
    'FSc Pre-Engineering': CS_CODES | ENGINEERING_CODES,
    'FSc Pre-Medical': MEDICAL_CODES,
    'ICS Physics': CS_CODES,
    'ICS Statistics': CS_CODES | {'BSMATH', 'BSSTAT'},
    'ICS Economics': CS_CODES | BUSINESS_CODES | {'BSIT'},
    'ICom': BUSINESS_CODES,
    'FA Arts / Humanities': ARTS_CODES,
}


class Command(BaseCommand):
    help = 'Seed AI recommendation interests, goals, eligibility, and trend scores'

    @transaction.atomic
    def handle(self, *args, **options):
        for name in INTERESTS:
            Interest.objects.get_or_create(name=name)
        for name in GOALS:
            CareerGoal.objects.get_or_create(name=name)

        programs = {
            p.program_code.upper(): p
            for p in DegreeProgram.objects.filter(is_active=True, degree_level='BS')
        }

        elig_created = 0
        DegreeEligibility.objects.all().delete()
        for background, codes in ELIGIBILITY.items():
            for code in codes:
                program = programs.get(code)
                if program:
                    DegreeEligibility.objects.create(background=background, degree=program)
                    elig_created += 1

        trend_created = 0
        TrendScore.objects.all().delete()
        for background in ELIGIBILITY:
            for code in ELIGIBILITY[background]:
                program = programs.get(code)
                if not program:
                    continue
                base = 6
                if code in CS_CODES and 'ICS' in background:
                    base = 8
                if code in MEDICAL_CODES and background == 'FSc Pre-Medical':
                    base = 9
                if code in BUSINESS_CODES and background == 'ICom':
                    base = 9
                TrendScore.objects.create(background=background, degree=program, score=base)
                trend_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(INTERESTS)} interests, {len(GOALS)} goals, '
            f'{elig_created} eligibility rows, {trend_created} trend scores.'
        ))
