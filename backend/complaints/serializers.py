from rest_framework import serializers
from .models import ComplaintCategory, Complaint, ComplaintLog, CommunicationThread, Message, Feedback


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = '__all__'
        read_only_fields = ['category_id']


class ComplaintLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintLog
        fields = '__all__'
        read_only_fields = ['log_id', 'timestamp']


class ComplaintSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    logs = ComplaintLogSerializer(many=True, read_only=True)
    has_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = ['complaint_id', 'submitted_at', 'submitted_by', 'status', 'admin_response', 'resolved_at']

    def get_has_feedback(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Feedback.objects.filter(complaint=obj, user=request.user).exists()

    def validate_subject(self, value):
        value = (value or '').strip()
        if len(value) < 3:
            raise serializers.ValidationError('Subject must be at least 3 characters.')
        if len(value) > 200:
            raise serializers.ValidationError('Subject cannot exceed 200 characters.')
        return value

    def validate_description(self, value):
        value = (value or '').strip()
        if len(value) < 10:
            raise serializers.ValidationError('Description must be at least 10 characters.')
        return value


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['message_id', 'sent_at', 'sender']


class CommunicationThreadSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = CommunicationThread
        fields = '__all__'
        read_only_fields = ['thread_id', 'created_at', 'created_by']


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ['feedback_id', 'submitted_at', 'user', 'complaint']

    def validate_rating(self, value):
        if value is None:
            return value
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value
