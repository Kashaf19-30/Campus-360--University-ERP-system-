"""Smoke-test every API route — must not return 500."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from core.tests.endpoint_registry import PUBLIC_GET, PUBLIC_POST, AUTH_GET, AUTH_GET_WITH_ID, AUTH_POST


class APISmokeTests(Campus360APITestCase):
    def setUp(self):
        self.admin = make_user('smoke_admin@test.edu', 'smoke_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access'], role_name='Admin')
        self.auth_as(self.admin)

    def _assert_not_server_error(self, response, label):
        self.assertNotEqual(
            response.status_code, 500,
            f'{label} returned 500: {getattr(response, "data", response.content[:200])}',
        )

    def test_public_get_endpoints(self):
        self.client.credentials()
        for path in PUBLIC_GET:
            r = self.client.get(path)
            self._assert_not_server_error(r, f'GET {path}')

    def test_public_post_endpoints(self):
        self.client.credentials()
        for method, path, body in PUBLIC_POST:
            r = self.client.post(path, body, format='json')
            self._assert_not_server_error(r, f'{method} {path}')

    def test_authenticated_get_endpoints(self):
        for path in AUTH_GET:
            r = self.client.get(path)
            self._assert_not_server_error(r, f'GET {path}')

    def test_authenticated_get_with_id_endpoints(self):
        for path in AUTH_GET_WITH_ID:
            r = self.client.get(path)
            self._assert_not_server_error(r, f'GET {path}')

    def test_authenticated_post_endpoints(self):
        for method, path, body in AUTH_POST:
            if method == 'PUT':
                r = self.client.put(path, body, format='json')
            else:
                r = self.client.post(path, body, format='json')
            self._assert_not_server_error(r, f'{method} {path}')

    def test_unauthenticated_protected_returns_401(self):
        self.client.credentials()
        for path in AUTH_GET[:10]:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 401, path)
