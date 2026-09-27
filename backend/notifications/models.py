from django.db import models
from django.conf import settings


class NotificationType(models.Model):
    type_id     = models.AutoField(primary_key=True)
    type_name   = models.CharField(max_length=50, unique=True)
    template    = models.TextField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'notification_type'

    def __str__(self):
        return self.type_name


class Notification(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('normal', 'Normal'),
        ('high', 'High'), ('urgent', 'Urgent'),
    ]
    SENT_VIA_CHOICES = [
        ('system', 'System'), ('email', 'Email'),
        ('sms', 'SMS'), ('all', 'All'),
    ]

    notification_id      = models.AutoField(primary_key=True)
    notification_type    = models.ForeignKey(NotificationType, on_delete=models.RESTRICT, related_name='notifications')
    recipient            = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    title                = models.CharField(max_length=200)
    message              = models.TextField()
    priority             = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    sent_via             = models.CharField(max_length=20, choices=SENT_VIA_CHOICES, default='system')
    is_read              = models.BooleanField(default=False)
    read_at              = models.DateTimeField(null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-created_at']


class Announcement(models.Model):
    ANNOUNCEMENT_TYPE_CHOICES = [
        ('academic', 'Academic'), ('event', 'Event'), ('holiday', 'Holiday'),
        ('examination', 'Examination'), ('admission', 'Admission'), ('general', 'General'),
    ]
    TARGET_AUDIENCE_CHOICES = [
        ('all', 'All'), ('students', 'Students'), ('faculty', 'Faculty'),
        ('staff', 'Staff'), ('specific_program', 'Specific Program'),
        ('course_offering', 'Course Offering'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ]

    announcement_id   = models.AutoField(primary_key=True)
    title             = models.CharField(max_length=200)
    content           = models.TextField()
    announcement_type = models.CharField(max_length=50, choices=ANNOUNCEMENT_TYPE_CHOICES)
    target_audience   = models.CharField(max_length=50, choices=TARGET_AUDIENCE_CHOICES, default='all')
    target_program    = models.ForeignKey(
        'academics.DegreeProgram', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='announcements'
    )
    target_semester   = models.ForeignKey(
        'academics.Semester', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='announcements'
    )
    target_offering   = models.ForeignKey(
        'academics.CourseOffering', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='announcements',
    )
    priority          = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    is_active         = models.BooleanField(default=True)
    published_date    = models.DateTimeField(auto_now_add=True)
    expires_date      = models.DateTimeField(null=True, blank=True)
    created_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='announcements'
    )
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcement'
        ordering = ['-created_at']