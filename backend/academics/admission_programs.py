"""
Canonical list of degree programs offered for admissions.
Used by the seed_admission_programs management command.
"""

ADMISSION_DEPARTMENTS = [
    {
        'department_code': 'FCIT',
        'department_name': 'Faculty of Computing & Information Technology',
        'programs': [
            {'program_name': 'BS Computer Science', 'program_code': 'BSCS', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Software Engineering', 'program_code': 'BSSE', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Artificial Intelligence', 'program_code': 'BSAI', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Information Technology', 'program_code': 'BSIT', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Data Science', 'program_code': 'BSDS', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Cyber Security', 'program_code': 'BSCYS', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Bioinformatics', 'program_code': 'BSBIOINF', 'degree_level': 'BS', 'duration_years': 4},
        ],
    },
    {
        'department_code': 'FENG',
        'department_name': 'Faculty of Engineering',
        'programs': [
            {'program_name': 'Computer Engineering', 'program_code': 'CEN', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'Electrical Engineering', 'program_code': 'EE', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'Civil Engineering', 'program_code': 'CE', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'Mechanical Engineering', 'program_code': 'ME', 'degree_level': 'BS', 'duration_years': 4},
        ],
    },
    {
        'department_code': 'FMHS',
        'department_name': 'Faculty of Medical & Health Sciences',
        'programs': [
            {'program_name': 'MBBS', 'program_code': 'MBBS', 'degree_level': 'BS', 'duration_years': 5},
            {'program_name': 'BDS', 'program_code': 'BDS', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'Pharm-D', 'program_code': 'PHARMD', 'degree_level': 'ADP', 'duration_years': 5},
            {'program_name': 'DPT', 'program_code': 'DPT', 'degree_level': 'BS', 'duration_years': 5},
            {'program_name': 'BS Biotechnology', 'program_code': 'BSBIOT', 'degree_level': 'BS', 'duration_years': 4},
        ],
    },
    {
        'department_code': 'FBMS',
        'department_name': 'Faculty of Business & Management Sciences',
        'programs': [
            {'program_name': 'BBA', 'program_code': 'BBA', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Accounting & Finance', 'program_code': 'BSAF', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Economics', 'program_code': 'BSECO', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Commerce', 'program_code': 'BSCOM', 'degree_level': 'BS', 'duration_years': 4},
        ],
    },
    {
        'department_code': 'FASE',
        'department_name': 'Faculty of Arts, Social Sciences & Education',
        'programs': [
            {'program_name': 'BS Psychology', 'program_code': 'BSPSY', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS English', 'program_code': 'BSENG', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Education', 'program_code': 'BSEDU', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS International Relations', 'program_code': 'BSIR', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Media Studies', 'program_code': 'BSMS', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Sociology', 'program_code': 'BSSOC', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Mathematics', 'program_code': 'BSMATH', 'degree_level': 'BS', 'duration_years': 4},
            {'program_name': 'BS Statistics', 'program_code': 'BSSTAT', 'degree_level': 'BS', 'duration_years': 4},
        ],
    },
]

DEFAULT_PROGRAM_FIELDS = {
    'total_semesters': 8,
    'total_credit_hours': 130,
    'program_type': 'morning',
    'is_active': True,
    'accepting_admissions': True,
}
