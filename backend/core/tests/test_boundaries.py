"""Boundary value tests for validators and serializers."""
from django.test import TestCase

from accounts.validators import validate_cnic
from admissions.document_validation import _name_match_score, BLUR_LAPLACIAN_MIN


class BoundaryTests(TestCase):
    def test_cnic_min_boundary_13_digits(self):
        self.assertEqual(len(validate_cnic('3' * 13)), 13)

    def test_cnic_max_boundary_13_digits(self):
        self.assertEqual(validate_cnic('9' * 13), '9' * 13)

    def test_cnic_below_min_12_digits(self):
        with self.assertRaises(ValueError):
            validate_cnic('1' * 12)

    def test_cnic_above_max_14_digits(self):
        with self.assertRaises(ValueError):
            validate_cnic('1' * 14)

    def test_name_match_empty_tokens(self):
        self.assertEqual(_name_match_score('hello', '', ''), 0.0)

    def test_name_match_perfect(self):
        score = _name_match_score('ali khan student', 'Ali', 'Khan')
        self.assertGreaterEqual(score, 0.5)

    def test_blur_threshold_positive(self):
        self.assertGreater(BLUR_LAPLACIAN_MIN, 0)
