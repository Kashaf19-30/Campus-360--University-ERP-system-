from django.db import models
from django.conf import settings
from academics.models import DegreeProgram

User = settings.AUTH_USER_MODEL

BACKGROUND_CHOICES = [
    ('FSc Pre-Medical', 'FSc Pre-Medical'),
    ('FSc Pre-Engineering', 'FSc Pre-Engineering'),
    ('ICS Physics', 'ICS Physics'),
    ('ICS Statistics', 'ICS Statistics'),
    ('ICS Economics', 'ICS Economics'),
    ('ICom', 'ICom'),
    ('FA Arts / Humanities', 'FA Arts / Humanities'),
]


class RecommendationProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='recommendation_profile')
    educational_background = models.CharField(max_length=50, choices=BACKGROUND_CHOICES, blank=True)

    class Meta:
        db_table = 'recommendation_profile'

    def __str__(self):
        return f"{self.user.username} recommendation profile"


class SubjectMark(models.Model):
    profile = models.ForeignKey(RecommendationProfile, on_delete=models.CASCADE, related_name='marks')
    subject_name = models.CharField(max_length=100)
    marks_obtained = models.FloatField()
    total_marks = models.FloatField(default=200)

    class Meta:
        db_table = 'recommendation_subject_mark'
        unique_together = ('profile', 'subject_name')

    def percentage(self):
        if not self.total_marks:
            return 0.0
        return (self.marks_obtained / self.total_marks) * 100


class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'recommendation_interest'


class ProfileInterest(models.Model):
    profile = models.ForeignKey(RecommendationProfile, on_delete=models.CASCADE, related_name='interests')
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE)

    class Meta:
        db_table = 'recommendation_profile_interest'
        unique_together = ('profile', 'interest')


class CareerGoal(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'recommendation_career_goal'


class ProfileGoal(models.Model):
    profile = models.ForeignKey(RecommendationProfile, on_delete=models.CASCADE, related_name='goals')
    goal = models.ForeignKey(CareerGoal, on_delete=models.CASCADE)

    class Meta:
        db_table = 'recommendation_profile_goal'
        unique_together = ('profile', 'goal')


class DegreeEligibility(models.Model):
    background = models.CharField(max_length=50, choices=BACKGROUND_CHOICES)
    degree = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='eligible_backgrounds')

    class Meta:
        db_table = 'recommendation_degree_eligibility'
        unique_together = ('background', 'degree')


class TrendScore(models.Model):
    background = models.CharField(max_length=50, choices=BACKGROUND_CHOICES)
    degree = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='recommendation_trends')
    score = models.IntegerField(help_text='Score between 0 and 10')

    class Meta:
        db_table = 'recommendation_trend_score'
        unique_together = ('background', 'degree')


class RecommendationResult(models.Model):
    profile = models.ForeignKey(RecommendationProfile, on_delete=models.CASCADE, related_name='recommendations')
    program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE)
    match_score = models.FloatField()
    reasons = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recommendation_result'
        ordering = ['-match_score']
