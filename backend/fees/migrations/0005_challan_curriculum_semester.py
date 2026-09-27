"""Track semester fees per curriculum semester, not just academic term."""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import migrations, models
from django.utils import timezone


def fix_unpaid_curriculum_enrollments(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    Semester = apps.get_model('academics', 'Semester')
    Challan = apps.get_model('fees', 'Challan')
    FeeStructure = apps.get_model('fees', 'FeeStructure')
    Enrollment = apps.get_model('enrollments', 'Enrollment')
    CourseRegistration = apps.get_model('enrollments', 'CourseRegistration')
    ProgramCourse = apps.get_model('academics', 'ProgramCourse')
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    User = apps.get_model('accounts', 'User')

    academic_semester = Semester.objects.filter(is_current=True).first()
    if not academic_semester:
        return

    admin = User.objects.filter(user_type='admin').first()
    if not admin:
        admin = User.objects.filter(is_superuser=True).first()

    def is_regular(student, course_id, curriculum_semester):
        return ProgramCourse.objects.filter(
            program_id=student.program_id,
            course_id=course_id,
            semester_number=curriculum_semester,
        ).exists()

    for student in Student.objects.filter(status='active').select_related('program'):
        if student.current_semester <= 1:
            continue
        paid = Challan.objects.filter(
            student=student,
            semester=academic_semester,
            curriculum_semester=student.current_semester,
            status='paid',
        ).exists()
        if paid:
            continue

        if not Challan.objects.filter(
            student=student,
            semester=academic_semester,
            curriculum_semester=student.current_semester,
        ).exists() and admin:
            fee_structure = FeeStructure.objects.filter(
                program_id=student.program_id,
                semester_number=student.current_semester,
                fee_type='semester_fee',
            ).order_by('-effective_from').first()
            amount = fee_structure.amount if fee_structure else (
                student.program.fee_per_semester or Decimal('75000')
            )
            Challan.objects.create(
                challan_number=f"CH-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}",
                student=student,
                semester=academic_semester,
                curriculum_semester=student.current_semester,
                due_date=timezone.now().date() + timedelta(days=30),
                total_amount=amount,
                generated_by=admin,
                status='pending',
            )

        enrollment = Enrollment.objects.filter(
            student=student, semester=academic_semester,
        ).first()
        if not enrollment:
            continue
        for reg in CourseRegistration.objects.filter(
            enrollment=enrollment, status='registered',
        ).select_related('course'):
            if not is_regular(student, reg.course_id, student.current_semester):
                continue
            if reg.offering_id:
                offering = CourseOffering.objects.filter(pk=reg.offering_id).first()
                if offering:
                    offering.enrolled_count = max(0, offering.enrolled_count - 1)
                    offering.save(update_fields=['enrolled_count'])
            reg.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0004_gap_fixes'),
        ('enrollments', '0008_reconcile_repeat_registrations'),
    ]

    operations = [
        migrations.AddField(
            model_name='challan',
            name='curriculum_semester',
            field=models.IntegerField(
                default=1,
                help_text='Curriculum semester number this fee covers (distinct from academic term).',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='challan',
            unique_together={('student', 'semester', 'curriculum_semester')},
        ),
        migrations.RunPython(fix_unpaid_curriculum_enrollments, migrations.RunPython.noop),
    ]
