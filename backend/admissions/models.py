# admissions/models.py
from django.db import models
from django.conf import settings
from academics.models import DegreeProgram

class Applicant(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applicant_profile'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100, blank=True)
    cnic = models.CharField(max_length=13, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    religion = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, default='Pakistani')
    marital_status = models.CharField(max_length=20, blank=True)
    perm_country = models.CharField(max_length=50, blank=True)
    perm_state = models.CharField(max_length=50, blank=True)
    perm_city = models.CharField(max_length=50, blank=True)
    perm_address = models.TextField(blank=True)
    emergency_name = models.CharField(max_length=100, blank=True)
    emergency_relation = models.CharField(max_length=50, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_cnic = models.CharField(max_length=13, blank=True)
    guardian_relation = models.CharField(max_length=50, blank=True)
    profile_image = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admissions_applicant'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class AcademicRecord(models.Model):
    GRADING_CHOICES = [('marks','Marks'),('cgpa','CGPA')]
    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE,
        related_name='academic_records'
    )
    authority = models.CharField(max_length=200)
    qualification_level = models.CharField(max_length=50)
    qualification = models.CharField(max_length=200)
    institute = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=20, blank=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    grading_system = models.CharField(max_length=10, choices=GRADING_CHOICES, default='marks')
    obtained = models.DecimalField(max_digits=7, decimal_places=2)
    total = models.DecimalField(max_digits=7, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admissions_academic_record'


class AdmissionApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending','Pending'),
        ('challan_pending', 'Challan Pending'),
        ('under_review','Under Review'),
        ('documents_pending', 'Documents Pending'),
        ('approved','Approved'),
        ('rejected','Rejected'),
        ('registered', 'Registered'),
    ]
    SESSION_TYPE_CHOICES = [
        ('spring', 'Spring'),
        ('fall', 'Fall'),
        ('summer', 'Summer'),
    ]
    ADMISSION_TYPE_CHOICES = [
        ('Regular','Regular'),
        ('Lateral','Lateral'),
        ('Migration','Migration'),
    ]
    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE,
        related_name='applications'
    )
    program = models.ForeignKey(
        DegreeProgram, on_delete=models.RESTRICT,
        related_name='applications'
    )
    application_number = models.CharField(max_length=50, unique=True)
    admission_type = models.CharField(max_length=20, choices=ADMISSION_TYPE_CHOICES, default='Regular')
    session_year = models.IntegerField(null=True, blank=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_fee_paid = models.BooleanField(default=False)
    is_eligible = models.BooleanField(null=True, blank=True)
    is_documents_verified = models.BooleanField(default=False)
    admission_challan_number = models.CharField(max_length=50, blank=True)
    admission_challan_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    challan_paid = models.BooleanField(default=False)
    challan_rejected_at = models.DateTimeField(null=True, blank=True, help_text='Deadline anchor for re-upload after OCR/admin rejection')
    rejection_message = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admissions_application'


class ProgramPreference(models.Model):
    application = models.ForeignKey(
        AdmissionApplication, on_delete=models.CASCADE,
        related_name='preferences'
    )
    program = models.ForeignKey(
        'academics.DegreeProgram',
        on_delete=models.RESTRICT,
        related_name='preferences'
    )
    preference_order = models.IntegerField()

    class Meta:
        db_table = 'admissions_program_preference'


# ========== APPLICANT DOCUMENT MODEL ==========
class ApplicantDocument(models.Model):
    DOCUMENT_TYPES = [
        # Personal Documents
        ('cnic_front', 'CNIC Front'),
        ('cnic_back', 'CNIC Back'),
        ('domicile', 'Domicile'),
        ('photograph', 'Photograph'),
        # Academic Documents
        ('matric_marksheet', 'Matric Marksheet'),
        ('matric_certificate', 'Matric Certificate'),
        ('inter_marksheet', 'Inter Marksheet'),
        ('inter_certificate', 'Inter Certificate'),
        ('paid_challan', 'Paid Admission Challan'),
    ]
    
    document_id = models.AutoField(primary_key=True)
    
    # Foreign key to Applicant model - this will create applicant_id column
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    # Foreign key to User who verified the document
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents',
    )
    
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'applicant_documents'
        ordering = ['-uploaded_at']
        unique_together = ['applicant', 'document_type']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.applicant.user.username}"

class AdmissionDecision(models.Model):
        DECISION_CHOICES = [
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]

        decision_id = models.AutoField(primary_key=True)
        application = models.OneToOneField(
            AdmissionApplication, on_delete=models.RESTRICT,
            related_name='decision'
        )
        decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
        decided_by = models.ForeignKey(
            settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
            related_name='admission_decisions'
        )
        decision_date = models.DateField(auto_now_add=True)
        remarks = models.TextField(null=True, blank=True)
        registration_deadline = models.DateField(null=True, blank=True)
        rejection_reason = models.TextField(null=True, blank=True)
        merit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        merit_position = models.IntegerField(null=True, blank=True)
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            db_table = 'admissions_decision'

class AdmissionLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('documents_verified', 'Documents Verified'),
        ('challan_accepted', 'Challan Accepted'),
        ('challan_rejected', 'Challan Rejected'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('registered', 'Registered'),
    ]

    log_id = models.AutoField(primary_key=True)
    application = models.ForeignKey(
        AdmissionApplication, on_delete=models.CASCADE,
        related_name='logs'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
        related_name='admission_logs'
    )
    previous_status = models.CharField(max_length=30, null=True, blank=True)
    new_status = models.CharField(max_length=30, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'admissions_log'


class AdmissionSettings(models.Model):
    """Singleton-style global admission window (one active row)."""
    settings_id = models.AutoField(primary_key=True)
    is_open = models.BooleanField(
        default=True,
        help_text='When False, new applicants see Admission Closed after signup.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admission_settings'

    def __str__(self):
        return 'Admissions Open' if self.is_open else 'Admissions Closed'