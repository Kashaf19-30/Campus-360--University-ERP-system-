from django.db import models
from django.conf import settings


class Student(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'), ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'), ('graduated', 'Graduated'),
        ('dropped', 'Dropped'), ('expelled', 'Expelled'),
    ]

    student_id                   = models.AutoField(primary_key=True)
    user                         = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile'
    )
    applicant                    = models.OneToOneField(
        'admissions.Applicant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='student'
    )
    program                      = models.ForeignKey(
        'academics.DegreeProgram', on_delete=models.RESTRICT, related_name='students'
    )
    registration_number          = models.CharField(max_length=50, unique=True)
    batch_year                   = models.IntegerField()
    admission_date               = models.DateField()
    current_semester             = models.IntegerField(default=1)
    status                       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    cgpa                         = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_credit_hours_completed = models.IntegerField(default=0)
    consecutive_probation_count  = models.IntegerField(default=0)
    academic_review_required     = models.BooleanField(default=False)
    graduation_date              = models.DateField(null=True, blank=True)
    created_at                   = models.DateTimeField(auto_now_add=True)
    updated_at                   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students_student'

    def __str__(self):
        return f"{self.registration_number} — {self.user.username}"


class StudentProfile(models.Model):
    student                               = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name='profile'
    )
    blood_group                           = models.CharField(max_length=5, blank=True)
    medical_conditions                    = models.TextField(blank=True)
    disabilities                          = models.TextField(blank=True)
    previous_cgpa                         = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    guardian_name                         = models.CharField(max_length=100, blank=True)
    guardian_cnic                         = models.CharField(max_length=15, blank=True)
    guardian_phone                        = models.CharField(max_length=20, blank=True)
    guardian_occupation                   = models.CharField(max_length=100, blank=True)
    residential_address                   = models.TextField(blank=True)
    permanent_address                     = models.TextField(blank=True)
    permanent_address_same_as_residential = models.BooleanField(default=True)
    profile_locked                        = models.BooleanField(default=False)
    updated_at                            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students_profile'

    def __str__(self):
        return f"Profile — {self.student.registration_number}"