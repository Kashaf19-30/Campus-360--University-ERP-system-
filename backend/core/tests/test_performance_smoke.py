"""Performance smoke tests — critical endpoints must respond within threshold."""
import time

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions, make_user, grant_permissions


class PerformanceSmokeTests(Campus360APITestCase):
    THRESHOLD_SEC = 3.0

    def setUp(self):
        admin = make_user('perf_admin@test.edu', 'perf_admin', 'admin')
        grant_permissions(admin, ['system.admin_access'], role_name='Admin')
        self.auth_as(admin)

    def _timed_get(self, path):
        start = time.perf_counter()
        r = self.client.get(path)
        elapsed = time.perf_counter() - start
        return r, elapsed

    def test_departments_list_performance(self):
        r, elapsed = self._timed_get('/api/academics/departments/')
        self.assertLess(elapsed, self.THRESHOLD_SEC, f'departments took {elapsed:.2f}s')
        self.assertIn(r.status_code, (200, 403))

    def test_admission_programs_performance(self):
        applicant = make_user('perf_app@test.edu', 'perf_app', 'applicant')
        grant_permissions(applicant, [
            'admissions.view_own_application', 'admissions.submit_application',
        ], role_name='Applicant')
        self.auth_as(applicant)
        r, elapsed = self._timed_get('/api/admissions/programs/')
        self.assertLess(elapsed, self.THRESHOLD_SEC)
        self.assertEqual(r.status_code, 200)

    def test_dashboard_stats_performance(self):
        r, elapsed = self._timed_get('/api/dashboard/stats/')
        self.assertLess(elapsed, self.THRESHOLD_SEC)
