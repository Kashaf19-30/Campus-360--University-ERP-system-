from django.db import models

from django.conf import settings





class Designation(models.Model):

    designation_id    = models.AutoField(primary_key=True)

    designation_title = models.CharField(max_length=100, unique=True)

    designation_level = models.IntegerField(null=True, blank=True)

    job_description   = models.TextField(blank=True)

    created_at        = models.DateTimeField(auto_now_add=True)



    class Meta:

        db_table = 'designation'



    def __str__(self):

        return self.designation_title





class Faculty(models.Model):

    EMPLOYMENT_TYPE_CHOICES = [

        ('permanent', 'Permanent'),

        ('visiting', 'Visiting'),

        ('contract', 'Contract'),

        ('contractual', 'Contractual'),

    ]

    STATUS_CHOICES = [

        ('active', 'Active'),

        ('inactive', 'Inactive'),

        ('on_leave', 'On Leave'),

        ('resigned', 'Resigned'),

        ('retired', 'Retired'),

    ]



    faculty_id       = models.AutoField(primary_key=True)

    user             = models.OneToOneField(

        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile'

    )

    department       = models.ForeignKey(

        'academics.Department', on_delete=models.RESTRICT, related_name='faculty_members'

    )

    program          = models.ForeignKey(

        'academics.DegreeProgram', on_delete=models.SET_NULL,

        null=True, blank=True, related_name='faculty_members'

    )

    designation      = models.ForeignKey(

        Designation, on_delete=models.RESTRICT, related_name='faculty_members'

    )

    employee_code    = models.CharField(max_length=50, unique=True)

    qualification    = models.CharField(max_length=100)

    specialization   = models.CharField(max_length=200, blank=True)

    joining_date     = models.DateField()

    employment_type  = models.CharField(max_length=30, choices=EMPLOYMENT_TYPE_CHOICES)

    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    office_floor     = models.CharField(max_length=20, blank=True)

    office_hours     = models.CharField(max_length=100, blank=True)

    profile_completed = models.BooleanField(default=False)

    created_at       = models.DateTimeField(auto_now_add=True)

    updated_at       = models.DateTimeField(auto_now=True)



    class Meta:

        db_table = 'faculty'



    def __str__(self):

        return f"{self.employee_code} — {self.user.username}"





class EmployeeProfile(models.Model):

    profile_id              = models.AutoField(primary_key=True)

    employee_id             = models.IntegerField()

    employee_type           = models.CharField(max_length=10, default='faculty')

    cnic                    = models.CharField(max_length=15, unique=True, blank=True, default='')

    date_of_birth           = models.DateField(null=True, blank=True)

    gender                  = models.CharField(max_length=10, blank=True)

    nationality             = models.CharField(max_length=50, default='Pakistani')

    phone_number            = models.CharField(max_length=20, blank=True, default='')

    emergency_contact_name  = models.CharField(max_length=100, blank=True, default='')

    emergency_contact_phone = models.CharField(max_length=20, blank=True, default='')

    emergency_contact_relation = models.CharField(max_length=50, blank=True, default='')

    current_address         = models.TextField(blank=True, default='')

    permanent_address       = models.TextField(blank=True)

    updated_at              = models.DateTimeField(auto_now=True)



    class Meta:

        db_table = 'employee_profile'

        unique_together = ['employee_id', 'employee_type']



    def __str__(self):

        return f"Faculty profile — ID {self.employee_id}"





class FacultyCourseAssignment(models.Model):

    """Teacher assigned to teach a course within a specific program (not globally)."""

    assignment_id = models.AutoField(primary_key=True)

    faculty = models.ForeignKey(

        Faculty, on_delete=models.CASCADE, related_name='course_assignments',

    )

    program = models.ForeignKey(

        'academics.DegreeProgram', on_delete=models.CASCADE,

        related_name='faculty_course_assignments',

    )

    course = models.ForeignKey(

        'academics.Course', on_delete=models.CASCADE,

        related_name='faculty_assignments',

    )

    assigned_by = models.ForeignKey(

        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,

        null=True, blank=True, related_name='faculty_assignments_created',

    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)



    class Meta:

        db_table = 'faculty_course_assignment'

        unique_together = ['program', 'course']



    def __str__(self):

        return f"{self.faculty.employee_code} — {self.program.program_code}/{self.course.course_code}"


