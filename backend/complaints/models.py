from django.db import models
from django.conf import settings


class ComplaintCategory(models.Model):
    category_id   = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    description   = models.TextField(blank=True)

    class Meta:
        db_table = 'complaint_category'

    def __str__(self):
        return self.category_name


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), ('resolved', 'Resolved'),
        ('closed', 'Closed'), ('rejected', 'Rejected'),
    ]

    complaint_id = models.AutoField(primary_key=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints'
    )
    category     = models.ForeignKey(ComplaintCategory, on_delete=models.RESTRICT, related_name='complaints')
    subject      = models.CharField(max_length=200)
    description  = models.TextField()
    status       = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    admin_response = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'complaint'

    def __str__(self):
        return f"{self.subject} — {self.status}"


class ComplaintLog(models.Model):
    ACTION_CHOICES = [
        ('submitted', 'Submitted'), ('assigned', 'Assigned'),
        ('updated', 'Updated'), ('resolved', 'Resolved'),
        ('closed', 'Closed'), ('rejected', 'Rejected'),
    ]

    log_id          = models.AutoField(primary_key=True)
    complaint       = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='logs')
    action_type     = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='complaint_actions'
    )
    previous_status = models.CharField(max_length=30, blank=True)
    new_status      = models.CharField(max_length=30, blank=True)
    remarks         = models.TextField(blank=True)
    timestamp       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'complaint_log'


class CommunicationThread(models.Model):
    thread_id  = models.AutoField(primary_key=True)
    complaint  = models.OneToOneField(
        Complaint, on_delete=models.CASCADE,
        null=True, blank=True, related_name='thread'
    )
    subject    = models.CharField(max_length=200)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='threads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'communication_thread'


class Message(models.Model):
    message_id  = models.AutoField(primary_key=True)
    thread      = models.ForeignKey(CommunicationThread, on_delete=models.CASCADE, related_name='messages')
    sender      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='messages'
    )
    message_text = models.TextField()
    sent_at      = models.DateTimeField(auto_now_add=True)
    is_read      = models.BooleanField(default=False)

    class Meta:
        db_table = 'message'


class Feedback(models.Model):
    feedback_id  = models.AutoField(primary_key=True)
    complaint    = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='feedback')
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback'
    )
    rating       = models.IntegerField(null=True, blank=True)
    comments     = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'complaint_feedback'
