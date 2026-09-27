from django.db import models
from django.conf import settings


class ExamType(models.Model):
    MARKS_PERIOD_CHOICES = [
        ('pre_mid', 'Pre Mid (A1, A2, Q1)'),
        ('mid_term', 'Mid Term'),
        ('post_mid', 'Post Mid (A3, Q2)'),
        ('final', 'Final Term'),
    ]

    exam_type_id        = models.AutoField(primary_key=True)
    type_name           = models.CharField(max_length=50, unique=True)
    weightage_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    marks_period        = models.CharField(max_length=20, choices=MARKS_PERIOD_CHOICES, default='pre_mid')
    description         = models.TextField(blank=True)

    class Meta:
        db_table = 'exam_type'

    def __str__(self):
        return self.type_name


class Examination(models.Model):
    ASSESSMENT_CATEGORY_CHOICES = [
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('presentation', 'Presentation / Project'),
        ('mid_term', 'Mid Term'),
        ('final', 'Final Term'),
    ]

    exam_id      = models.AutoField(primary_key=True)
    course       = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='examinations')
    semester     = models.ForeignKey('academics.Semester', on_delete=models.RESTRICT, related_name='examinations')
    offering     = models.ForeignKey('academics.CourseOffering', on_delete=models.CASCADE, related_name='examinations')
    exam_type    = models.ForeignKey(ExamType, on_delete=models.RESTRICT, related_name='examinations')
    assessment_category = models.CharField(max_length=20, choices=ASSESSMENT_CATEGORY_CHOICES, default='quiz')
    exam_name    = models.CharField(max_length=200)
    exam_date    = models.DateField(null=True, blank=True)
    total_marks  = models.DecimalField(max_digits=6, decimal_places=2)
    passing_marks = models.DecimalField(max_digits=6, decimal_places=2)
    weight_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Weight toward final grade. Mid=30, Final=40, continuous categories max 10% each.',
    )
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_examinations'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'examination'

    def __str__(self):
        return f"{self.exam_name} — {self.course.course_code}"


class Grade(models.Model):
    grade_id      = models.AutoField(primary_key=True)
    grade_letter  = models.CharField(max_length=5, unique=True)
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade_points  = models.DecimalField(max_digits=3, decimal_places=2)
    status        = models.CharField(max_length=10, choices=[('pass', 'Pass'), ('fail', 'Fail')])
    description   = models.TextField(blank=True)

    class Meta:
        db_table = 'grade_scale'

    def __str__(self):
        return f"{self.grade_letter} ({self.grade_points})"


class Marks(models.Model):
    marks_id      = models.AutoField(primary_key=True)
    exam          = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='marks')
    student       = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='marks')
    registration  = models.ForeignKey(
        'enrollments.CourseRegistration', on_delete=models.CASCADE, related_name='marks'
    )
    obtained_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_absent     = models.BooleanField(default=False)
    remarks       = models.TextField(blank=True)
    entered_by    = models.ForeignKey(
        'faculty.Faculty', on_delete=models.RESTRICT, related_name='entered_marks'
    )
    entered_at    = models.DateTimeField(auto_now_add=True)
    modified_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='modified_marks'
    )
    modified_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'marks'
        unique_together = ['exam', 'student']


class FinalGrade(models.Model):
    STATUS_CHOICES = [
        ('pass', 'Pass'), ('fail', 'Fail'),
        ('incomplete', 'Incomplete'), ('withdrawn', 'Withdrawn'),
    ]

    final_grade_id      = models.AutoField(primary_key=True)
    registration        = models.OneToOneField(
        'enrollments.CourseRegistration', 
        on_delete=models.CASCADE, 
        related_name='final_grade'
    )
    student             = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='final_grades')
    course              = models.ForeignKey('academics.Course', on_delete=models.RESTRICT, related_name='final_grades')
    semester            = models.ForeignKey('academics.Semester', on_delete=models.RESTRICT, related_name='final_grades')
    total_obtained_marks = models.DecimalField(max_digits=6, decimal_places=2)
    total_marks         = models.DecimalField(max_digits=6, decimal_places=2)
    percentage          = models.DecimalField(max_digits=5, decimal_places=2)
    grade               = models.ForeignKey(Grade, on_delete=models.RESTRICT, related_name='final_grades')
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES)
    verified_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_grades'
    )
    verified_at         = models.DateTimeField(null=True, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'final_grade'


class Result(models.Model):
    STATUS_CHOICES = [
        ('pass', 'Pass'), ('fail', 'Fail'),
        ('incomplete', 'Incomplete'), ('probation', 'Probation'),
    ]

    result_id                   = models.AutoField(primary_key=True)
    student                     = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='results')
    semester                    = models.ForeignKey('academics.Semester', on_delete=models.RESTRICT, related_name='results')
    sgpa                        = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    cgpa                        = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    total_credit_hours_attempted = models.IntegerField(null=True, blank=True)
    total_credit_hours_earned   = models.IntegerField(null=True, blank=True)
    status                      = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_published                = models.BooleanField(default=False)
    promotion_applied           = models.BooleanField(default=False)
    promotion_pending           = models.BooleanField(
        default=False,
        help_text='Admin approved promotion; awaiting target semester fee payment.',
    )
    pending_promotion_semester  = models.IntegerField(
        null=True, blank=True,
        help_text='Curriculum semester number student will move to once fee is paid.',
    )
    published_date              = models.DateField(null=True, blank=True)
    published_by                = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='published_results'
    )
    created_at                  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'result'
        unique_together = ['student', 'semester']


class ResultApproval(models.Model):
    approval_id   = models.AutoField(primary_key=True)
    result        = models.OneToOneField(Result, on_delete=models.CASCADE, related_name='approval')
    approved_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='approved_results'
    )
    approval_date = models.DateField(auto_now_add=True)
    remarks       = models.TextField(blank=True)

    class Meta:
        db_table = 'result_approval'


class MarksEditPermission(models.Model):
    REQUEST_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    permission_id = models.AutoField(primary_key=True)
    offering = models.ForeignKey('academics.CourseOffering', on_delete=models.CASCADE, related_name='marks_edit_permissions')
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='marks_edit_permissions',
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='granted_marks_permissions'
    )
    granted_to = models.ForeignKey(
        'faculty.Faculty', on_delete=models.CASCADE, related_name='marks_edit_permissions'
    )
    examination = models.ForeignKey(
        'examinations.Examination', on_delete=models.CASCADE,
        null=True, blank=True, related_name='edit_permissions',
        help_text='Specific exam this approval applies to',
    )
    request_status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marks_edit_permission'


class OfferingMarksEditRequest(models.Model):
    """Teacher requests to edit marks for a completed course until final re-submission."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    request_id = models.AutoField(primary_key=True)
    offering = models.ForeignKey(
        'academics.CourseOffering', on_delete=models.CASCADE,
        related_name='marks_edit_requests',
    )
    faculty = models.ForeignKey(
        'faculty.Faculty', on_delete=models.CASCADE,
        related_name='offering_edit_requests',
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_offering_edit_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'offering_marks_edit_request'

    def __str__(self):
        return f'{self.offering_id} edit request ({self.status})'