"""CNIC and input validator tests."""
from django.test import TestCase

from accounts.validators import validate_cnic


class CnicValidatorTests(TestCase):
    def test_valid_cnic_normalized(self):
        self.assertEqual(validate_cnic('35202-1234567-1'), '3520212345671')

    def test_valid_cnic_digits_only(self):
        self.assertEqual(validate_cnic('3520212345671'), '3520212345671')

    def test_rejects_short_cnic(self):
        with self.assertRaises(ValueError):
            validate_cnic('123456789012')

    def test_rejects_long_cnic(self):
        with self.assertRaises(ValueError):
            validate_cnic('35202123456712')

    def test_rejects_letters(self):
        with self.assertRaises(ValueError):
            validate_cnic('35202ABC4567-1')

    def test_rejects_none(self):
        with self.assertRaises(ValueError):
            validate_cnic(None)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            validate_cnic('')
