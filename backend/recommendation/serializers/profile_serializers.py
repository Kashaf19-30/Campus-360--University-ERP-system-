from rest_framework import serializers
from recommendation.models import (
    RecommendationProfile, SubjectMark, ProfileInterest, ProfileGoal, Interest, CareerGoal,
)


class SubjectMarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectMark
        fields = ['subject_name', 'marks_obtained', 'total_marks']


class RecommendationProfileSerializer(serializers.ModelSerializer):
    marks = SubjectMarkSerializer(many=True, required=False)
    interests = serializers.SerializerMethodField()
    goals = serializers.SerializerMethodField()
    interest_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    goal_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = RecommendationProfile
        fields = [
            'id', 'user', 'educational_background', 'marks', 'interests', 'goals',
            'interest_names', 'goal_names',
        ]
        read_only_fields = ['user']

    def get_interests(self, obj):
        return [pi.interest.name for pi in obj.interests.all()]

    def get_goals(self, obj):
        return [pg.goal.name for pg in obj.goals.all()]

    def update(self, instance, validated_data):
        marks_data = validated_data.pop('marks', [])
        interest_names = validated_data.pop('interest_names', [])
        goal_names = validated_data.pop('goal_names', [])

        instance.educational_background = validated_data.get(
            'educational_background', instance.educational_background,
        )
        instance.save()

        instance.marks.all().delete()
        for mark_data in marks_data:
            SubjectMark.objects.create(profile=instance, **mark_data)

        instance.interests.all().delete()
        for name in interest_names:
            interest, _ = Interest.objects.get_or_create(name=name)
            ProfileInterest.objects.create(profile=instance, interest=interest)

        instance.goals.all().delete()
        for name in goal_names:
            goal, _ = CareerGoal.objects.get_or_create(name=name)
            ProfileGoal.objects.create(profile=instance, goal=goal)

        return instance
