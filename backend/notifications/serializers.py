from rest_framework import serializers
from .models import NotificationType, Notification, Announcement


class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = '__all__'
        read_only_fields = ['type_id']


class NotificationSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='notification_type.type_name', read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['notification_id', 'created_at', 'recipient']


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    target_program_name = serializers.CharField(
        source='target_program.program_name', read_only=True
    )
    target_course_code = serializers.CharField(
        source='target_offering.course.course_code', read_only=True,
    )
    target_course_name = serializers.CharField(
        source='target_offering.course.course_name', read_only=True,
    )

    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ['announcement_id', 'published_date', 'created_at', 'updated_at', 'created_by']