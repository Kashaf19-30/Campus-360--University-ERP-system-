"""AI recommendation engine unit tests."""
from django.test import TestCase

from accounts.models import User
from academics.models import Department, DegreeProgram
from recommendation.models import (
    RecommendationProfile, SubjectMark, Interest, CareerGoal,
    ProfileInterest, ProfileGoal, DegreeEligibility, TrendScore,
)
from recommendation.services.recommendation_engine import RecommendationEngine
from recommendation.services.subject_analyzer import calculate_subject_strength


class SubjectAnalyzerTests(TestCase):
    def test_perfect_marks_score_one(self):
        weights = {'Physics': 0.5, 'Mathematics': 0.5}
        marks = {'Physics': 100.0, 'Mathematics': 100.0}
        self.assertAlmostEqual(calculate_subject_strength(marks, weights), 1.0)

    def test_zero_marks_score_zero(self):
        weights = {'Physics': 1.0}
        marks = {'Physics': 0.0}
        self.assertAlmostEqual(calculate_subject_strength(marks, weights), 0.0)

    def test_missing_subject_treated_as_zero(self):
        weights = {'Physics': 0.5, 'Chemistry': 0.5}
        marks = {'Physics': 80.0}
        self.assertAlmostEqual(calculate_subject_strength(marks, weights), 0.4)


class RecommendationEngineTests(TestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='Computer Science')
        self.program = DegreeProgram.objects.create(
            department=dept,
            program_name='BS Computer Science',
            program_code='BSCS',
            degree_level='BS',
            duration_years=4,
            total_semesters=8,
            total_credit_hours=130,
            is_active=True,
            accepting_admissions=True,
        )
        user = User.objects.create_user(
            email='rec@test.edu', username='rec_user', password='pass', user_type='applicant',
        )
        self.profile = RecommendationProfile.objects.create(
            user=user, educational_background='FSc Pre-Engineering',
        )
        SubjectMark.objects.create(
            profile=self.profile, subject_name='Physics', marks_obtained=180, total_marks=200,
        )
        SubjectMark.objects.create(
            profile=self.profile, subject_name='Mathematics', marks_obtained=170, total_marks=200,
        )
        interest, _ = Interest.objects.get_or_create(name='Programming & Technology')
        ProfileInterest.objects.create(profile=self.profile, interest=interest)
        goal, _ = CareerGoal.objects.get_or_create(name='High Salary')
        ProfileGoal.objects.create(profile=self.profile, goal=goal)
        DegreeEligibility.objects.create(background='FSc Pre-Engineering', degree=self.program)
        TrendScore.objects.create(background='FSc Pre-Engineering', degree=self.program, score=8)

    def test_engine_returns_recommendations(self):
        engine = RecommendationEngine(self.profile)
        results = engine.get_recommendations(limit=5)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['program'].program_code, 'BSCS')
        self.assertGreater(results[0]['score'], 0)

    def test_engine_excludes_ineligible_programs(self):
        dept2 = Department.objects.create(department_code='MED', department_name='Medicine')
        med = DegreeProgram.objects.create(
            department=dept2, program_name='BS Medical', program_code='BSMED',
            degree_level='BS', duration_years=5, total_semesters=10, total_credit_hours=250,
            is_active=True, accepting_admissions=True,
        )
        engine = RecommendationEngine(self.profile)
        results = engine.get_recommendations(limit=20)
        codes = {r['program'].program_code for r in results}
        self.assertIn('BSCS', codes)
        self.assertNotIn('BSMED', codes)

    def test_engine_returns_empty_without_eligibility(self):
        DegreeEligibility.objects.all().delete()
        engine = RecommendationEngine(self.profile)
        self.assertEqual(engine.get_recommendations(), [])

    def test_scenario_weights_with_interests_and_goals(self):
        engine = RecommendationEngine(self.profile)
        weights = engine._get_scenario_weights()
        self.assertAlmostEqual(
            weights['subjects'] + weights['interests'] + weights['goals'] + weights['trend'],
            1.0,
        )
