from django.contrib import admin
from .models import ComplaintCategory, Complaint, ComplaintLog, CommunicationThread, Message, Feedback

admin.site.register(ComplaintCategory)
admin.site.register(Complaint)
admin.site.register(ComplaintLog)
admin.site.register(CommunicationThread)
admin.site.register(Message)
admin.site.register(Feedback)
