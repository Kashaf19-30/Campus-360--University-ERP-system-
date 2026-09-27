from django.db import models
from django.conf import settings


class Department(models.Model):
    department_id   = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=100, unique=True)
    department_code = models.CharField(max_length=20, unique=True)
    hod             = models.ForeignKey(
        'faculty.Faculty',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='headed_department'
    )
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'department'

    def __str__(self):
        return f"{self.department_code} — {self.department_name}"


class DegreeProgram(models.Model):
    DEGREE_LEVEL_CHOICES = [
        ('BS', 'BS'), 
        ('MS', 'MS'), 
        ('PhD', 'PhD'), 
        ('ADP', 'ADP'),
    ]
    PROGRAM_TYPE_CHOICES = [
        ('morning', 'Morning'), 
        ('evening', 'Evening'),
        ('self_support', 'Self Support'), 
        ('distance_learning', 'Distance Learning'),
    ]

    program_id           = models.AutoField(primary_key=True)
    department           = models.ForeignKey(Department, on_delete=models.RESTRICT, related_name='programs')
    program_name         = models.CharField(max_length=200)
    program_code         = models.CharField(max_length=20, unique=True)
    degree_level         = models.CharField(max_length=10, choices=DEGREE_LEVEL_CHOICES)
    duration_years       = models.IntegerField()
    total_semesters      = models.IntegerField()
    total_credit_hours   = models.IntegerField()
    program_type         = models.CharField(max_length=30, choices=PROGRAM_TYPE_CHOICES, default='morning')
    is_active            = models.BooleanField(default=True)
    accepting_admissions = models.BooleanField(default=True)
    description          = models.TextField(blank=True)
    fee_per_semester     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'degree_program'

    def __str__(self):
        return f"{self.program_code} — {self.program_name}"


class Semester(models.Model):
    SEMESTER_TYPE_CHOICES = [
        ('fall', 'Fall'), 
        ('spring', 'Spring'), 
        ('summer', 'Summer'),
    ]

    semester_id             = models.AutoField(primary_key=True)
    semester_name           = models.CharField(max_length=50, unique=True)
    academic_year           = models.IntegerField()
    semester_type           = models.CharField(max_length=20, choices=SEMESTER_TYPE_CHOICES)
    start_date              = models.DateField()
    end_date                = models.DateField()
    mid_term_cutoff_date    = models.DateField(null=True, blank=True, help_text='After this, pre-mid + mid-term marks lock')
    marks_grace_end_date    = models.DateField(null=True, blank=True, help_text='Default: end_date + 7 days')
    is_current              = models.BooleanField(default=False)
    created_at              = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'semester'

    def __str__(self):
        return self.semester_name


class Course(models.Model):
    COURSE_TYPE_CHOICES = [
        ('core', 'Core'),
        ('elective', 'Elective'),
        ('university_requirement', 'University Requirement'),
    ]

    course_id           = models.AutoField(primary_key=True)
    department          = models.ForeignKey(Department, on_delete=models.RESTRICT, related_name='courses')
    course_code         = models.CharField(max_length=20, unique=True)
    course_name         = models.CharField(max_length=200)
    credit_hours        = models.IntegerField()
    theory_credit_hours = models.IntegerField(default=0)
    lab_credit_hours    = models.IntegerField(default=0)
    course_type         = models.CharField(max_length=30, choices=COURSE_TYPE_CHOICES)
    description         = models.TextField(blank=True)
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course'

    def __str__(self):
        return f"{self.course_code} — {self.course_name}"


class ProgramCourse(models.Model):
    program_course_id = models.AutoField(primary_key=True)
    program           = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='program_courses')
    course            = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='program_courses')
    semester_number   = models.IntegerField()
    is_core           = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'program_course'
        unique_together = ['program', 'course', 'semester_number']

    def __str__(self):
        return f"{self.program.program_code} — {self.course.course_code} (Sem {self.semester_number})"


class CoursePrerequisite(models.Model):
    PREREQUISITE_TYPE_CHOICES = [
        ('course', 'Course'),
        ('credit_hours', 'Minimum Credit Hours'),
    ]

    prerequisite_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='prerequisites',
    )
    prerequisite_type = models.CharField(
        max_length=20, choices=PREREQUISITE_TYPE_CHOICES, default='course',
    )
    prerequisite_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True,
        related_name='required_for_courses',
    )
    min_credit_hours = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_prerequisite'
        unique_together = [
            ['course', 'prerequisite_type', 'prerequisite_course'],
            ['course', 'prerequisite_type', 'min_credit_hours'],
        ]

    def __str__(self):
        if self.prerequisite_type == 'credit_hours':
            return f"{self.course.course_code} requires {self.min_credit_hours}+ CH"
        return f"{self.course.course_code} requires {self.prerequisite_course.course_code}"


class ProgramCoursePrerequisite(models.Model):
    """Program-scoped prerequisites (supports OR groups via or_group)."""
    prerequisite_id = models.AutoField(primary_key=True)
    program = models.ForeignKey(
        DegreeProgram, on_delete=models.CASCADE, related_name='course_prerequisites',
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='program_prerequisites',
    )
    prerequisite_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True,
        related_name='required_for_program_courses',
    )
    min_credit_hours = models.IntegerField(null=True, blank=True)
    or_group = models.PositiveSmallIntegerField(
        default=0,
        help_text='Same or_group on one course = OR; different groups = AND',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'program_course_prerequisite'

    def __str__(self):
        if self.min_credit_hours:
            return f"{self.program.program_code}/{self.course.course_code}: {self.min_credit_hours}+ CH"
        return f"{self.program.program_code}/{self.course.course_code}: {self.prerequisite_course.course_code}"


class CourseOffering(models.Model):
    """Teaching assignment: course + semester + faculty (replaces legacy Section)."""
    OFFERING_TYPE_CHOICES = [
        ('theory', 'Theory'),
        ('lab', 'Lab'),
        ('theory_lab_combined', 'Theory + Lab Combined'),
    ]

    offering_id        = models.AutoField(primary_key=True)
    course             = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='offerings')
    semester           = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='offerings')
    curriculum_semester = models.IntegerField(
        default=1,
        help_text='Program curriculum semester this offering serves (user-facing semester number).',
    )
    repeat_offering = models.BooleanField(
        default=False,
        help_text='True = repeat/improvement section (separate from regular batch).',
    )
    cohort_sequence = models.PositiveIntegerField(
        default=1,
        help_text='Intake/class sequence when the same course+session+teacher is taught again to a new cohort.',
    )
    faculty            = models.ForeignKey('faculty.Faculty', on_delete=models.RESTRICT, related_name='course_offerings')
    offering_type      = models.CharField(max_length=30, choices=OFFERING_TYPE_CHOICES, default='theory')
    enrolled_count     = models.IntegerField(default=0)
    is_active          = models.BooleanField(default=True)
    marks_locked       = models.BooleanField(default=False)
    marks_unlock_until = models.DateTimeField(null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_offering'
        unique_together = [
            'course', 'semester', 'faculty', 'curriculum_semester', 'repeat_offering', 'cohort_sequence',
        ]

    def __str__(self):
        return f"{self.course.course_code} — {self.semester.semester_name} ({self.faculty})"


class AcademicPolicy(models.Model):
    """Singleton-style institution academic rules (one active row)."""
    policy_id = models.AutoField(primary_key=True)
    min_sgpa_pass = models.DecimalField(
        max_digits=3, decimal_places=2, default=2.0,
        help_text='Minimum SGPA for semester pass standing (independent of individual course fails).',
    )
    min_sgpa_probation = models.DecimalField(
        max_digits=3, decimal_places=2, default=2.0,
        help_text='Minimum SGPA to avoid semester fail; below min_sgpa_pass but above this yields probation.',
    )
    min_cgpa_graduation = models.DecimalField(
        max_digits=3, decimal_places=2, default=2.0,
        help_text='Minimum CGPA required to graduate.',
    )
    max_consecutive_probation = models.IntegerField(
        default=2,
        help_text='Consecutive probation semesters before dismissal review is flagged.',
    )
    max_course_attempts = models.IntegerField(
        default=3,
        help_text='Maximum attempts allowed per course (future enforcement).',
    )
    min_attendance_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=75.0,
        help_text='Minimum attendance % before shortage warnings are sent.',
    )
    max_semester_credit_hours = models.IntegerField(
        default=21,
        help_text='Maximum credit hours a student may register in one semester.',
    )
    max_repeat_credit_hours = models.IntegerField(
        default=21,
        help_text='Maximum credit hours for admin-approved repeat requests.',
    )
    auto_enroll_failed_prerequisites = models.BooleanField(
        default=True,
        help_text='When a course is blocked, auto-enroll failed prerequisite courses as repeats.',
    )
    allow_concurrent_prerequisite_enrollment = models.BooleanField(
        default=True,
        help_text='If credit cap allows, enroll blocked course alongside its in-progress prerequisite repeat.',
    )
    soft_prerequisite_enrollment = models.BooleanField(
        default=True,
        help_text='Enroll curriculum courses with prerequisite warnings instead of deferring (keeps batch together).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'academic_policy'

    def __str__(self):
        return 'Academic Policy'
