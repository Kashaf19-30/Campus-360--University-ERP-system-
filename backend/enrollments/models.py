from django.db import models


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('withdrawn', 'Withdrawn'),
    ]

    enrollment_id                = models.AutoField(primary_key=True)
    student                      = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='enrollments')
    semester                     = models.ForeignKey('academics.Semester', on_delete=models.RESTRICT, related_name='enrollments')
    enrollment_date              = models.DateField(auto_now_add=True)
    status                       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    total_credit_hours_registered = models.IntegerField(default=0)
    created_at                   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'enrollment'
        unique_together = ['student', 'semester']

    def __str__(self):
        return f"{self.student.registration_number} — {self.semester.semester_name}"


class CourseRegistration(models.Model):
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('dropped', 'Dropped'),
        ('withdrawn', 'Withdrawn'),
        ('completed', 'Completed'),
    ]
    REGISTRATION_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('repeat', 'Repeat'),
        ('prerequisite_repeat', 'Prerequisite Repeat'),
    ]

    registration_id = models.AutoField(primary_key=True)
    enrollment      = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='course_registrations')
    course          = models.ForeignKey('academics.Course', on_delete=models.RESTRICT, related_name='registrations')
    offering        = models.ForeignKey('academics.CourseOffering', on_delete=models.RESTRICT, related_name='registrations')
    student         = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='course_registrations')
    registration_date = models.DateField(auto_now_add=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    registration_type = models.CharField(
        max_length=30, choices=REGISTRATION_TYPE_CHOICES, default='regular',
    )
    grade_points    = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_registration'
        unique_together = ['enrollment', 'course']

    def __str__(self):
        return f"{self.student.registration_number} — {self.course.course_code}"


class RepeatCourseRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    request_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='repeat_requests',
    )
    semester = models.ForeignKey(
        'academics.Semester', on_delete=models.RESTRICT, related_name='repeat_requests',
    )
    course = models.ForeignKey(
        'academics.Course', on_delete=models.RESTRICT, related_name='repeat_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_repeat_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'repeat_course_request'
        unique_together = ['student', 'semester', 'course']

    def __str__(self):
        return f"{self.student.registration_number} repeat {self.course.course_code} ({self.status})"