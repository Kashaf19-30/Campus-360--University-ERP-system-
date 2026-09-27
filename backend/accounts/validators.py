import re

CNIC_DIGITS_RE = re.compile(r'^\d{13}$')


def validate_cnic(value: str, field_name: str = 'CNIC') -> str:
    """Return normalized 13-digit CNIC or raise ValueError."""
    if value is None:
        raise ValueError(f'{field_name} is required.')
    cleaned = re.sub(r'\D', '', str(value).strip())
    if not CNIC_DIGITS_RE.match(cleaned):
        raise ValueError(f'{field_name} must be exactly 13 digits.')
    return cleaned
