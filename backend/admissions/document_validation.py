"""
OCR-based document validation for admission uploads.

- Blur detection (Laplacian variance)
- Name matching on CNIC and marksheets
- Confidence scoring from RapidOCR
- Auto-verify when confidence is high and checks pass
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from PIL import Image, ImageStat

_OCR_ENGINE = None
_OCR_UNAVAILABLE = False

# Blur: Laplacian variance below this => too blurry to read
BLUR_LAPLACIAN_MIN = 85.0

# OCR confidence thresholds (0–1)
HIGH_CONFIDENCE_AUTO = 0.82   # auto-verify document / challan
MIN_CONFIDENCE_READ = 0.50    # below => treat as unreadable / blurry

MIN_OCR_TEXT_LEN = {
    'cnic_front': 8,
    'cnic_back': 8,
    'domicile': 12,
    'matric_marksheet': 10,
    'matric_certificate': 10,
    'inter_marksheet': 10,
    'inter_certificate': 10,
    'paid_challan': 15,
}

PHOTO_TYPES = {'photograph'}

NAME_VALIDATED_TYPES = {
    'cnic_front', 'domicile',
    'matric_marksheet', 'matric_certificate',
    'inter_marksheet', 'inter_certificate',
}

# CNIC back typically shows address / fingerprints — no applicant name to match.
CNIC_BACK_AUTO_PASS_TYPES = {'cnic_back'}

MARKSHEET_TYPES = {
    'matric_marksheet', 'matric_certificate',
    'inter_marksheet', 'inter_certificate',
}

CNIC_TYPES = {'cnic_front', 'cnic_back'}


@dataclass
class OcrResult:
    text: str = ''
    confidence: float = 0.0
    line_confidences: list[float] = field(default_factory=list)
    blur_score: float = 0.0
    is_blurry: bool = False


@dataclass
class DocumentValidationResult:
    ok: bool
    error: str = ''
    ocr_text: str = ''
    confidence: float = 0.0
    auto_verified: bool = False
    blur_score: float = 0.0
    name_match_score: float = 0.0

    @property
    def remarks(self) -> str:
        parts = []
        if self.confidence:
            parts.append(f'conf={self.confidence:.2f}')
        if self.blur_score:
            parts.append(f'blur={self.blur_score:.0f}')
        if self.name_match_score:
            parts.append(f'name={self.name_match_score:.2f}')
        if self.auto_verified:
            parts.append('auto_verified')
        if self.ocr_text:
            parts.append(f'text={self.ocr_text[:180]}')
        return 'OCR: ' + '; '.join(parts)


def _get_ocr_engine():
    global _OCR_ENGINE, _OCR_UNAVAILABLE
    if _OCR_UNAVAILABLE:
        return None
    if _OCR_ENGINE is None:
        try:
            from rapidocr import RapidOCR
            _OCR_ENGINE = RapidOCR()
        except Exception:
            _OCR_UNAVAILABLE = True
            return None
    return _OCR_ENGINE


def _parse_ocr_output(ocr_out) -> tuple[list[str], list[float]]:
    lines: list[str] = []
    confidences: list[float] = []
    if not ocr_out:
        return lines, confidences

    # rapidocr v3 returns RapidOCROutput with txts/scores.
    if hasattr(ocr_out, 'txts') and hasattr(ocr_out, 'scores'):
        for text, conf in zip(ocr_out.txts or [], ocr_out.scores or []):
            text = str(text).strip()
            if not text:
                continue
            lines.append(text)
            confidences.append(float(conf) if conf is not None else 0.75)
        return lines, confidences

    # Legacy rapidocr_onnxruntime: list of [box, text, conf].
    for item in ocr_out:
        if not item or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        lines.append(text)
        conf = float(item[2]) if len(item) > 2 and item[2] is not None else 0.75
        confidences.append(conf)
    return lines, confidences


def _load_image_from_bytes(file_bytes: bytes, file_ext: str, page_index: int = 0) -> Optional[Image.Image]:
    ext = file_ext.lower().lstrip('.')
    if ext == 'pdf':
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype='pdf')
            if doc.page_count == 0 or page_index >= doc.page_count:
                doc.close()
                return None
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            doc.close()
            return img
        except Exception:
            return None
    if page_index > 0:
        return None
    try:
        return Image.open(io.BytesIO(file_bytes)).convert('RGB')
    except Exception:
        return None


def _pdf_page_count(file_bytes: bytes) -> int:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype='pdf')
        count = doc.page_count
        doc.close()
        return count
    except Exception:
        return 0


def _blur_score(image: Image.Image) -> float:
    try:
        import cv2
        import numpy as np
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        # Fallback: low std dev often correlates with blur
        return float(ImageStat.Stat(image.convert('L')).stddev[0]) * 3


def _image_blank_stats(image: Image.Image) -> dict:
    gray = image.convert('L')
    stat = ImageStat.Stat(gray)
    pixels = list(gray.getdata())
    total = len(pixels) or 1
    return {
        'std_dev': stat.stddev[0],
        'white_ratio': sum(1 for p in pixels if p > 245) / total,
        'black_ratio': sum(1 for p in pixels if p < 10) / total,
        'width': image.width,
        'height': image.height,
    }


def _run_ocr_on_image(image: Image.Image) -> OcrResult:
    blur = _blur_score(image)
    result = OcrResult(blur_score=blur, is_blurry=blur < BLUR_LAPLACIAN_MIN)

    engine = _get_ocr_engine()
    if engine is None:
        return result

    try:
        import numpy as np
        arr = np.array(image)
        ocr_out = engine(arr)
        if isinstance(ocr_out, tuple):
            ocr_out = ocr_out[0]
        lines, confidences = _parse_ocr_output(ocr_out)
        if not lines:
            return result
        result.text = ' '.join(lines).lower()
        result.line_confidences = confidences
        result.confidence = sum(confidences) / len(confidences) if confidences else 0.0
    except Exception:
        pass
    return result


def run_ocr(file_bytes: bytes, file_ext: str, max_pages: int = 1) -> OcrResult:
    """OCR one or more pages; merge text and average confidence."""
    combined_text = []
    all_conf = []
    blur_scores = []

    pages = max_pages if file_ext.lower().lstrip('.') == 'pdf' else 1
    if pages > 1:
        pages = min(pages, _pdf_page_count(file_bytes) or 1)

    for i in range(pages):
        image = _load_image_from_bytes(file_bytes, file_ext, page_index=i)
        if image is None:
            continue
        page_result = _run_ocr_on_image(image)
        blur_scores.append(page_result.blur_score)
        if page_result.text:
            combined_text.append(page_result.text)
        all_conf.extend(page_result.line_confidences)

    avg_conf = sum(all_conf) / len(all_conf) if all_conf else 0.0
    avg_blur = sum(blur_scores) / len(blur_scores) if blur_scores else 0.0

    return OcrResult(
        text=' '.join(combined_text).lower(),
        confidence=avg_conf,
        line_confidences=all_conf,
        blur_score=avg_blur,
        is_blurry=avg_blur < BLUR_LAPLACIAN_MIN if blur_scores else False,
    )


def is_blank_or_invalid_image(image: Image.Image, document_type: str) -> tuple[bool, str]:
    stats = _image_blank_stats(image)
    if stats['width'] < 80 or stats['height'] < 80:
        return True, 'Image is too small. Upload a clear, full document photo.'

    if document_type in PHOTO_TYPES:
        if stats['std_dev'] < 18:
            return True, 'Photograph appears blank or uniform. Upload a clear face photo.'
        if stats['white_ratio'] > 0.97 or stats['black_ratio'] > 0.97:
            return True, 'Photograph appears blank. Use a proper camera photo.'
        return False, ''

    if stats['std_dev'] < 10:
        return True, 'Document appears blank or completely uniform.'
    if stats['white_ratio'] > 0.985 and stats['std_dev'] < 20:
        return True, 'Document appears to be a blank white page.'
    if stats['black_ratio'] > 0.985:
        return True, 'Document appears to be a blank black image.'
    return False, ''


def _normalize_digits(text: str) -> str:
    return re.sub(r'[^0-9]', '', text)


def _name_tokens(first_name: str, last_name: str, father_name: str = '') -> list[str]:
    tokens = []
    for raw in (first_name, last_name, father_name):
        for part in (raw or '').lower().split():
            cleaned = re.sub(r'[^a-z]', '', part)
            if len(cleaned) >= 3:
                tokens.append(cleaned)
    # dedupe preserving order
    seen = set()
    unique = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _name_match_score(ocr_text: str, first_name: str, last_name: str, father_name: str = '') -> float:
    """Fraction of name tokens found; CNIC/marksheets require first + last name."""
    tokens = _name_tokens(first_name, last_name, father_name)
    if not tokens:
        return 0.0
    text = ocr_text.lower()
    text_compact = re.sub(r'[^a-z0-9]', '', text)
    matched = sum(1 for t in tokens if t in text or t in text_compact)
    score = matched / len(tokens)

    first = re.sub(r'[^a-z]', '', (first_name or '').lower())
    last = re.sub(r'[^a-z]', '', (last_name or '').lower())
    if first and last:
        first_ok = first in text_compact or first in text
        last_ok = last in text_compact or last in text
        if not (first_ok and last_ok):
            return min(score, 0.49)
    return score


def _cnic_in_text(ocr_text: str, cnic: str) -> bool:
    if not cnic:
        return False
    digits = _normalize_digits(cnic)
    ocr_digits = _normalize_digits(ocr_text)
    if not digits or not ocr_digits:
        return False
    return digits in ocr_digits or digits[-5:] in ocr_digits


def _amount_in_text(text: str, amount: Decimal) -> bool:
    if not text:
        return False
    int_part = str(int(amount))
    normalized = _normalize_digits(text)
    return int_part in normalized


def _token_in_text(text: str, token: str) -> bool:
    if not token or not text:
        return False
    token_clean = re.sub(r'[\s\-_]', '', token.lower())
    text_clean = re.sub(r'[\s\-_]', '', text.lower())
    return token_clean in text_clean


def _blur_reject_message(document_type: str) -> str:
    label = document_type.replace('_', ' ')
    return (
        f'This {label} appears blurry or out of focus. '
        'Please re-upload a clear, sharp photo or scan where all text is readable.'
    )


def _low_confidence_message(document_type: str) -> str:
    return (
        f'Could not read this {document_type.replace("_", " ")} clearly. '
        'The image may be blurry or too dark. Please re-upload a clearer document.'
    )


def _should_auto_verify(confidence: float, checks_passed: bool) -> bool:
    return checks_passed and confidence >= HIGH_CONFIDENCE_AUTO


def validate_document_upload(
    file_bytes: bytes,
    file_ext: str,
    document_type: str,
    *,
    challan_number: str = '',
    expected_amount: Optional[Decimal] = None,
    applicant_name: str = '',
    first_name: str = '',
    last_name: str = '',
    father_name: str = '',
    applicant_cnic: str = '',
) -> DocumentValidationResult:
    """Validate upload; returns structured result with auto_verified flag."""
    if not first_name and not last_name and applicant_name:
        parts = applicant_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

    if document_type == 'paid_challan':
        return _validate_paid_challan(
            file_bytes, file_ext,
            challan_number=challan_number,
            expected_amount=expected_amount or Decimal('0'),
            first_name=first_name, last_name=last_name, father_name=father_name,
            applicant_cnic=applicant_cnic,
        )

    image = _load_image_from_bytes(file_bytes, file_ext)
    if image is None:
        return DocumentValidationResult(False, 'Could not read the uploaded file. Use PDF, JPG, or PNG.')

    blank, blank_msg = is_blank_or_invalid_image(image, document_type)
    if blank:
        return DocumentValidationResult(False, blank_msg)

    blur = _blur_score(image)
    if blur < BLUR_LAPLACIAN_MIN and document_type not in PHOTO_TYPES:
        return DocumentValidationResult(False, _blur_reject_message(document_type), blur_score=blur)

    if document_type in PHOTO_TYPES:
        if blur < BLUR_LAPLACIAN_MIN * 0.7:
            return DocumentValidationResult(
                False,
                'Photograph appears blurry. Please re-upload a clear, in-focus photo.',
                blur_score=blur,
            )
        return DocumentValidationResult(
            True,
            ocr_text='photograph: ok',
            blur_score=blur,
            auto_verified=True,
        )

    if document_type in CNIC_BACK_AUTO_PASS_TYPES:
        ocr = run_ocr(file_bytes, file_ext, max_pages=1)
        if ocr.is_blurry:
            return DocumentValidationResult(
                False,
                _blur_reject_message(document_type),
                blur_score=ocr.blur_score,
            )
        if applicant_cnic and not _cnic_in_text(ocr.text, applicant_cnic):
            return DocumentValidationResult(
                False,
                (
                    'CNIC number on the back side does not match your profile CNIC. '
                    'Please re-upload the correct CNIC back scan.'
                ),
                ocr_text=ocr.text[:300],
                confidence=ocr.confidence,
                blur_score=ocr.blur_score or blur,
            )
        return DocumentValidationResult(
            ok=True,
            ocr_text=ocr.text[:500] if ocr.text else 'cnic_back: cnic verified',
            confidence=ocr.confidence,
            auto_verified=True,
            blur_score=ocr.blur_score or blur,
        )

    max_pages = 2 if document_type in MARKSHEET_TYPES else 1
    ocr = run_ocr(file_bytes, file_ext, max_pages=max_pages)

    if ocr.is_blurry:
        return DocumentValidationResult(False, _blur_reject_message(document_type), blur_score=ocr.blur_score)

    min_len = MIN_OCR_TEXT_LEN.get(document_type, 8)
    if not ocr.text or len(ocr.text) < min_len:
        if _get_ocr_engine() is None:
            return DocumentValidationResult(
                False,
                'Document verification is unavailable. Please try again later or contact support.',
                blur_score=ocr.blur_score,
            )
        return DocumentValidationResult(
            False,
            _low_confidence_message(document_type),
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    if ocr.confidence < MIN_CONFIDENCE_READ:
        return DocumentValidationResult(
            False,
            _low_confidence_message(document_type),
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    name_score = 0.0
    if document_type in NAME_VALIDATED_TYPES:
        name_score = _name_match_score(ocr.text, first_name, last_name, father_name)
        min_name = 0.67 if document_type in CNIC_TYPES else 0.5
        if name_score < min_name:
            expected = f'{first_name} {last_name}'.strip()
            return DocumentValidationResult(
                False,
                (
                    f'Name on this document does not match your profile ({expected}). '
                    'Upload the correct document with your name clearly visible, or update your profile if the name is wrong.'
                ),
                ocr_text=ocr.text[:300],
                confidence=ocr.confidence,
                blur_score=ocr.blur_score,
                name_match_score=name_score,
            )
        if document_type in CNIC_TYPES and applicant_cnic and not _cnic_in_text(ocr.text, applicant_cnic):
            return DocumentValidationResult(
                False,
                (
                    'CNIC number on this document does not match your profile CNIC. '
                    'Please re-upload the correct CNIC scan.'
                ),
                ocr_text=ocr.text[:300],
                confidence=ocr.confidence,
                blur_score=ocr.blur_score,
                name_match_score=name_score,
            )

    checks_ok = True
    auto = checks_ok

    return DocumentValidationResult(
        ok=True,
        ocr_text=ocr.text[:500],
        confidence=ocr.confidence,
        auto_verified=auto,
        blur_score=ocr.blur_score,
        name_match_score=name_score,
    )


def _validate_paid_challan(
    file_bytes: bytes,
    file_ext: str,
    *,
    challan_number: str,
    expected_amount: Decimal,
    first_name: str,
    last_name: str,
    father_name: str,
    applicant_cnic: str,
) -> DocumentValidationResult:
    image = _load_image_from_bytes(file_bytes, file_ext)
    if image is None:
        return DocumentValidationResult(False, 'Could not read the uploaded file. Use PDF, JPG, or PNG.')

    blank, blank_msg = is_blank_or_invalid_image(image, 'paid_challan')
    if blank:
        return DocumentValidationResult(False, blank_msg)

    ocr = run_ocr(file_bytes, file_ext, max_pages=1)
    if ocr.is_blurry:
        return DocumentValidationResult(False, _blur_reject_message('paid_challan'), blur_score=ocr.blur_score)

    if not ocr.text:
        return DocumentValidationResult(
            False,
            _low_confidence_message('paid_challan'),
            blur_score=ocr.blur_score,
        )

    if ocr.confidence < MIN_CONFIDENCE_READ:
        return DocumentValidationResult(
            False,
            _low_confidence_message('paid_challan'),
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    if len(ocr.text) < MIN_OCR_TEXT_LEN['paid_challan']:
        return DocumentValidationResult(
            False,
            'Challan has too little readable text. Please re-upload a clearer photo of the paid challan.',
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    if not _token_in_text(ocr.text, challan_number):
        return DocumentValidationResult(
            False,
            f'Challan number {challan_number} was not found. Upload the paid challan issued for this application.',
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    if not _amount_in_text(ocr.text, expected_amount):
        return DocumentValidationResult(
            False,
            f'Expected fee Rs. {expected_amount:,.0f} was not found on the challan. Upload the correct paid challan.',
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
        )

    name_score = _name_match_score(ocr.text, first_name, last_name, father_name)
    cnic_ok = _cnic_in_text(ocr.text, applicant_cnic) if applicant_cnic else False
    if name_score < 0.34 and not cnic_ok:
        return DocumentValidationResult(
            False,
            'Paid challan does not show your name or CNIC. Upload the challan issued in your name.',
            ocr_text=ocr.text[:300],
            confidence=ocr.confidence,
            blur_score=ocr.blur_score,
            name_match_score=name_score,
        )

    checks_ok = (
        _token_in_text(ocr.text, challan_number)
        and _amount_in_text(ocr.text, expected_amount)
        and (name_score >= 0.34 or cnic_ok)
    )
    # Challan is never auto-verified — OCR validates content only; admin must accept/reject.
    _ = checks_ok

    return DocumentValidationResult(
        ok=True,
        ocr_text=ocr.text[:500],
        confidence=ocr.confidence,
        auto_verified=False,
        blur_score=ocr.blur_score,
        name_match_score=name_score,
    )
