"""Deactivate abandoned course offerings with zero roster activity."""
from django.core.management.base import BaseCommand

from academics.models import CourseOffering
from enrollments.repeat_utils import maybe_deactivate_empty_offering, offering_is_empty_shell


class Command(BaseCommand):
    help = 'Deactivate active offerings that have no students and no teaching history.'

    def handle(self, *args, **options):
        count = 0
        for offering in CourseOffering.objects.filter(is_active=True):
            if offering_is_empty_shell(offering) and maybe_deactivate_empty_offering(offering):
                count += 1
                self.stdout.write(
                    f'  deactivated offering #{offering.pk} '
                    f'({offering.course.course_code}, cohort {offering.cohort_sequence})'
                )
        self.stdout.write(self.style.SUCCESS(f'Deactivated {count} empty offering(s).'))
