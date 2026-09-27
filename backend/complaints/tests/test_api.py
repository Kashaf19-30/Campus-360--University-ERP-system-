"""Complaints module API tests."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from complaints.models import ComplaintCategory, Complaint, Feedback


class ComplaintsAPITests(Campus360APITestCase):
    def setUp(self):
        self.category = ComplaintCategory.objects.create(category_name='General')
        self.student = make_user('cmp_stu@test.edu', 'cmp_stu', 'student')
        grant_permissions(self.student, [
            'complaints.create_complaint', 'complaints.view_own_complaint',
        ], role_name='Student')
        self.admin = make_user('cmp_admin@test.edu', 'cmp_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access', 'complaints.view_complaint'], role_name='Admin')
        self.complaint = Complaint.objects.create(
            submitted_by=self.student,
            category=self.category,
            subject='Hostel issue',
            description='Water supply problem in block B',
            status='resolved',
        )

    def test_student_can_list_own_complaints(self):
        self.auth_as(self.student)
        r = self.client.get('/api/complaints/me/')
        self.assertEqual(r.status_code, 200)

    def test_admin_can_list_all_complaints(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/complaints/')
        self.assertEqual(r.status_code, 200)

    def test_list_categories(self):
        self.auth_as(self.student)
        r = self.client.get('/api/complaints/categories/')
        self.assertEqual(r.status_code, 200)

    def test_student_can_submit_feedback_without_complaint_field(self):
        self.auth_as(self.student)
        r = self.client.post(
            f'/api/complaints/{self.complaint.complaint_id}/feedback/submit/',
            {'rating': 4, 'comments': 'Issue resolved quickly.'},
            format='json',
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(
            Feedback.objects.filter(complaint=self.complaint, user=self.student).exists()
        )
