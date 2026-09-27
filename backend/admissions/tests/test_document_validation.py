"""OCR/document validation unit tests (no live OCR required)."""
from decimal import Decimal

from django.test import TestCase
from PIL import Image

from admissions.document_validation import (
    _name_match_score,
    _cnic_in_text,
    _amount_in_text,
    is_blank_or_invalid_image,
    validate_document_upload,
    BLUR_LAPLACIAN_MIN,
)


class NameMatchingTests(TestCase):
    def test_full_name_match(self):
        text = 'name: ali khan father: ahmed khan'
        score = _name_match_score(text, 'Ali', 'Khan', 'Ahmed')
        self.assertGreaterEqual(score, 0.66)

    def test_missing_last_name_capped(self):
        text = 'ali ahmed'
        score = _name_match_score(text, 'Ali', 'Khan', '')
        self.assertLessEqual(score, 0.49)

    def test_cnic_digits_found(self):
        self.assertTrue(_cnic_in_text('cnic 35202-1234567-1', '3520212345671'))

    def test_challan_amount_found(self):
        self.assertTrue(_amount_in_text('fee paid 15000 rupees', Decimal('15000')))


class BlankImageTests(TestCase):
    def _solid_image(self, color, size=(400, 300)):
        return Image.new('RGB', size, color)

    def test_blank_white_document_rejected(self):
        img = self._solid_image('white')
        is_blank, msg = is_blank_or_invalid_image(img, 'cnic_front')
        self.assertTrue(is_blank)
        self.assertIn('blank', msg.lower())

    def test_tiny_image_rejected(self):
        img = self._solid_image('white', size=(50, 50))
        is_blank, msg = is_blank_or_invalid_image(img, 'cnic_front')
        self.assertTrue(is_blank)
        self.assertIn('small', msg.lower())

    def test_varied_photo_not_blank(self):
        img = Image.new('RGB', (200, 200))
        pixels = img.load()
        for x in range(200):
            for y in range(200):
                pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
        is_blank, _ = is_blank_or_invalid_image(img, 'photograph')
        self.assertFalse(is_blank)


class ValidateDocumentUploadTests(TestCase):
    def test_rejects_too_small_file(self):
        tiny = b'x' * 100
        result = validate_document_upload(
            file_bytes=tiny,
            file_ext='.jpg',
            document_type='cnic_front',
            first_name='Ali',
            last_name='Khan',
            applicant_cnic='3520212345671',
        )
        self.assertFalse(result.ok)

    def test_blur_threshold_constant(self):
        self.assertGreater(BLUR_LAPLACIAN_MIN, 0)
