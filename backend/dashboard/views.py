from django.db.models import Count, Sum

from rest_framework.decorators import api_view, permission_classes

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response



from accounts.permissions import IsAdmin

from academics.models import Semester, CourseOffering

from students.models import Student

from enrollments.models import CourseRegistration

from faculty.models import Faculty, FacultyCourseAssignment

from complaints.models import Complaint

from fees.models import Challan





@api_view(['GET'])

@permission_classes([IsAuthenticated, IsAdmin])

def dashboard_stats(request):

    """Aggregated statistics for admin dashboard charts."""

    semester_id = request.query_params.get('semester')

    current_semester = None

    if semester_id:

        current_semester = Semester.objects.filter(semester_id=semester_id).first()

    if not current_semester:

        current_semester = Semester.objects.filter(is_current=True).first()



    active_students = Student.objects.filter(status='active')



    students_by_program = list(

        active_students.values('program_id', 'program__program_name', 'program__program_code')

        .annotate(count=Count('student_id'))

        .order_by('-count')

    )

    students_by_program = [

        {

            'program_id': row['program_id'],

            'program_name': row['program__program_name'],

            'program_code': row['program__program_code'],

            'count': row['count'],

        }

        for row in students_by_program

    ]



    students_by_semester = list(

        active_students.values('current_semester')

        .annotate(count=Count('student_id'))

        .order_by('current_semester')

    )

    students_by_semester = [

        {'semester': row['current_semester'], 'count': row['count']}

        for row in students_by_semester

    ]



    reg_qs = CourseRegistration.objects.filter(status='registered')

    if current_semester:

        reg_qs = reg_qs.filter(enrollment__semester=current_semester)



    enrollments_by_course = list(

        reg_qs.values('course_id', 'course__course_code', 'course__course_name')

        .annotate(count=Count('registration_id'))

        .order_by('-count')[:15]

    )

    enrollments_by_course = [

        {

            'course_id': row['course_id'],

            'course_code': row['course__course_code'],

            'course_name': row['course__course_name'],

            'count': row['count'],

        }

        for row in enrollments_by_course

    ]



    offering_qs = CourseOffering.objects.filter(is_active=True)

    if current_semester:

        offering_qs = offering_qs.filter(semester=current_semester)



    enrolled_by_faculty = {

        row['faculty_id']: row['total_enrolled'] or 0

        for row in offering_qs.values('faculty_id').annotate(total_enrolled=Sum('enrolled_count'))

        if row['faculty_id']

    }

    assignments_by_faculty = {

        row['faculty_id']: row['course_count']

        for row in FacultyCourseAssignment.objects.filter(is_active=True)

        .values('faculty_id')

        .annotate(course_count=Count('assignment_id'))

    }



    faculty_load = []

    for f in Faculty.objects.filter(status='active').select_related('user', 'department').order_by('employee_code'):

        faculty_load.append({

            'faculty_id': f.faculty_id,

            'faculty_name': f.user.username if f.user_id else 'Unassigned',

            'employee_code': f.employee_code or '',

            'semester_id': current_semester.semester_id if current_semester else None,

            'semester_name': current_semester.semester_name if current_semester else '—',

            'course_count': assignments_by_faculty.get(f.faculty_id, 0),

            'total_enrolled': enrolled_by_faculty.get(f.faculty_id, 0),

        })



    summary = {

        'students': active_students.count(),

        'faculty': Faculty.objects.filter(status='active').count(),

        'course_assignments': FacultyCourseAssignment.objects.filter(is_active=True).count(),

        'course_offerings': offering_qs.count(),

        'enrollments': reg_qs.count(),

        'complaints_open': Complaint.objects.exclude(status__in=['resolved', 'rejected', 'closed']).count(),

        'challans_pending': Challan.objects.filter(

            status__in=['pending', 'overdue'],

        ).count(),

    }



    return Response({

        'semester': {

            'semester_id': current_semester.semester_id if current_semester else None,

            'semester_name': current_semester.semester_name if current_semester else None,

        },

        'summary': summary,

        'students_by_program': students_by_program,

        'students_by_semester': students_by_semester,

        'enrollments_by_course': enrollments_by_course,

        'faculty_load': faculty_load,

    })

