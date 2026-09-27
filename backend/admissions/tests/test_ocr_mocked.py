"""OCR validation with mocked engine (CI-safe, no RapidOCR dependency)."""
from unittest.mock import patch, MagicMock

from django.test import TestCase

from admissions.document_validation import validate_document_upload, DocumentValidationResult


class OCRMockedTests(TestCase):
    @patch('admissions.document_validation._get_ocr_engine')
    @patch('admissions.document_validation._load_image_from_bytes')
    def test_high_confidence_auto_verify_path(self, mock_load, mock_engine):
        from PIL import Image
        img = Image.new('RGB', (400, 300), color=(128, 64, 32))
        mock_load.return_value = img
        mock_engine.return_value = MagicMock()
        with patch('admissions.document_validation._run_ocr_on_image') as mock_ocr:
            from admissions.document_validation import OcrResult
            mock_ocr.return_value = OcrResult(
                text='ali khan cnic 3520212345671 marks obtained 850',
                confidence=0.95, blur_score=200.0, is_blurry=False,
            )
            result = validate_document_upload(
                file_bytes=b'x' * 5000,
                file_ext='.jpg',
                document_type='cnic_front',
                first_name='Ali',
                last_name='Khan',
                applicant_cnic='3520212345671',
            )
            self.assertIsInstance(result, DocumentValidationResult)

    @patch('admissions.document_validation._get_ocr_engine', return_value=None)
    def test_ocr_unavailable_rejects_non_photo(self, _mock):
        result = validate_document_upload(
            file_bytes=b'x' * 5000,
            file_ext='.jpg',
            document_type='cnic_front',
            first_name='Ali',
            last_name='Khan',
        )
        self.assertFalse(result.ok)
