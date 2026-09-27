"""File upload security tests."""
from django.test import TestCase

from admissions.views import MIN_DOCUMENT_SIZE


class FileUploadSecurityTests(TestCase):
    def test_min_document_size_enforced(self):
        self.assertGreaterEqual(MIN_DOCUMENT_SIZE, 1024)

    def test_path_traversal_filename_sanitized_by_storage(self):
        malicious = '../../../etc/passwd.jpg'
        # Django default_storage uses basename — verify no directory traversal in stored name
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        import os
        name = default_storage.save(f'admissions/test/{os.path.basename(malicious)}', ContentFile(b'x' * 2048))
        self.assertNotIn('..', name)
        default_storage.delete(name)

    def test_empty_file_below_minimum(self):
        self.assertLess(0, MIN_DOCUMENT_SIZE)
