from django.db import models
from django.conf import settings


class FeeStructure(models.Model):
    FEE_TYPE_CHOICES = [
        ('semester_fee', 'Semester Fee'),
        ('admission_fee', 'Admission Fee'),
        ('examination_fee', 'Examination Fee'),
    ]

    structure_id    = models.AutoField(primary_key=True)
    program         = models.ForeignKey('academics.DegreeProgram', on_delete=models.CASCADE, related_name='fee_structures')
    semester_number = models.IntegerField(null=True, blank=True)
    fee_type        = models.CharField(max_length=50, choices=FEE_TYPE_CHOICES, default='semester_fee')
    amount          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_from  = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fee_structure'
        unique_together = ['program', 'semester_number', 'effective_from']

    def __str__(self):
        return f"{self.program.program_code} - {self.get_fee_type_display()}: {self.amount}"


class Challan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    challan_id     = models.AutoField(primary_key=True)
    challan_number = models.CharField(max_length=50, unique=True)
    student        = models.ForeignKey('students.Student', on_delete=models.RESTRICT, related_name='challans')
    semester       = models.ForeignKey('academics.Semester', on_delete=models.RESTRICT, related_name='challans')
    curriculum_semester = models.IntegerField(
        default=1,
        help_text='Curriculum semester number this fee covers (distinct from academic term).',
    )
    issue_date     = models.DateField(auto_now_add=True)
    due_date       = models.DateField()
    late_fee       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='generated_challans'
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'challan'
        unique_together = ['student', 'semester', 'curriculum_semester']
