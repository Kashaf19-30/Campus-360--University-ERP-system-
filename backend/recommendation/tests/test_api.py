"""AI recommendation API authorization and workflow tests."""
from django.test import TestCase

from accounts.tests.base import Campus360APITestCase, make_user
from academics.models import Department, DegreeProgram
from recommendation.models import (
    RecommendationProfile, SubjectMark, DegreeEligibility, TrendScore,
)


class RecommendationAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
            is_active=True, accepting_admissions=True,
        )
        DegreeEligibility.objects.create(background='FSc Pre-Engineering', degree=self.program)
        TrendScore.objects.create(background='FSc Pre-Engineering', degree=self.program, score=7)
        self.applicant = self.create_applicant()
        self.student = self.create_student_user()

    def test_student_cannot_update_recommendation_profile(self):
        self.auth_as(self.student)
        response = self.client.put(
            '/api/recommendations/profile/update/',
            {'educational_background': 'FSc Pre-Engineering'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_results(self):
        response = self.client.get('/api/recommendations/results/')
        self.assertEqual(response.status_code, 401)

    def test_applicant_can_update_profile(self):
        self.auth_as(self.applicant)
        response = self.client.put(
            '/api/recommendations/profile/update/',
            {
                'educational_background': 'FSc Pre-Engineering',
                'marks': [
                    {'subject_name': 'Physics', 'marks_obtained': 180, 'total_marks': 200},
                    {'subject_name': 'Mathematics', 'marks_obtained': 170, 'total_marks': 200},
                ],
                'interest_names': ['Programming & Technology'],
                'goal_names': ['High Salary'],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        profile = RecommendationProfile.objects.get(user=self.applicant)
        self.assertEqual(profile.educational_background, 'FSc Pre-Engineering')
        self.assertEqual(profile.marks.count(), 2)

    def test_results_require_profile_data(self):
        self.auth_as(self.applicant)
        response = self.client.get('/api/recommendations/results/')
        self.assertEqual(response.status_code, 400)

    def test_results_return_recommendations_after_profile_complete(self):
        self.auth_as(self.applicant)
        self.client.put(
            '/api/recommendations/profile/update/',
            {
                'educational_background': 'FSc Pre-Engineering',
                'marks': [{'subject_name': 'Physics', 'marks_obtained': 180, 'total_marks': 200}],
                'interest_names': ['Programming & Technology'],
            },
            format='json',
        )
        response = self.client.get('/api/recommendations/results/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)
        self.assertIn('program_name', response.data[0])
        self.assertIn('match_score', response.data[0])

    def test_student_cannot_fetch_results(self):
        self.auth_as(self.student)
        response = self.client.get('/api/recommendations/results/')
        self.assertEqual(response.status_code, 403)
