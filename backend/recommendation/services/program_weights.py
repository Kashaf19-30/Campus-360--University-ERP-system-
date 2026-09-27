"""Default subject weight maps for degree recommendation scoring."""

CS_CODES = {'BSCS', 'BSSE', 'BSAI', 'BSIT', 'BSDS', 'BSCYS', 'BSBIOINF'}
ENGINEERING_CODES = {'CEN', 'EE', 'CE', 'ME'}
MEDICAL_CODES = {'MBBS', 'BDS', 'PHARMD', 'DPT', 'BSBIOT'}
BUSINESS_CODES = {'BBA', 'BSAF', 'BSECO', 'BSCOM'}
ARTS_CODES = {'BSPSY', 'BSENG', 'BSEDU', 'BSIR', 'BSMS', 'BSSOC', 'BSMATH', 'BSSTAT'}

WEIGHT_TEMPLATES = {
    'cs': {
        'Mathematics': 0.30, 'Computer Science': 0.35, 'Physics': 0.15,
        'English': 0.10, 'Urdu': 0.10,
    },
    'engineering': {
        'Mathematics': 0.35, 'Physics': 0.30, 'Chemistry': 0.20,
        'English': 0.08, 'Urdu': 0.07,
    },
    'medical': {
        'Biology': 0.40, 'Chemistry': 0.30, 'Physics': 0.15,
        'English': 0.08, 'Urdu': 0.07,
    },
    'business': {
        'Accounting': 0.30, 'Business Studies': 0.25, 'Economics': 0.25,
        'English': 0.12, 'Urdu': 0.08,
    },
    'arts': {
        'English': 0.25, 'Urdu': 0.20, 'Psychology': 0.20,
        'Sociology': 0.15, 'History': 0.10, 'Education': 0.10,
    },
}


def _template_for_program(program):
    code = (program.program_code or '').upper()
    if code in CS_CODES:
        return 'cs'
    if code in ENGINEERING_CODES:
        return 'engineering'
    if code in MEDICAL_CODES:
        return 'medical'
    if code in BUSINESS_CODES:
        return 'business'
    if code in ARTS_CODES:
        return 'arts'
    name = (program.program_name or '').lower()
    if any(k in name for k in ('computer', 'software', 'artificial', 'data', 'information', 'cyber')):
        return 'cs'
    if 'engineering' in name:
        return 'engineering'
    if any(k in name for k in ('mbbs', 'medical', 'pharm', 'dpt', 'biotech')):
        return 'medical'
    if any(k in name for k in ('bba', 'business', 'commerce', 'accounting', 'economics')):
        return 'business'
    return 'arts'


def get_program_subject_weights(program):
    stored = getattr(program, 'subject_weights', None) or {}
    if stored:
        return stored
    return WEIGHT_TEMPLATES.get(_template_for_program(program), WEIGHT_TEMPLATES['arts'])
