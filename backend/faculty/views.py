from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsTeacher, require_permission
from academics.models import ProgramCourse, DegreeProgram, Course
from .models import Designation, Faculty, EmployeeProfile, FacultyCourseAssignment
from .serializers import (
    DesignationSerializer, FacultySerializer, FacultyCreateSerializer,
    EmployeeProfileSerializer, FacultyCourseAssignmentSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_designations(request):
    return Response(DesignationSerializer(Designation.objects.all(), many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_designation(request):
    serializer = DesignationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('faculty.view_faculty')])
def list_faculty(request):
    faculty = Faculty.objects.select_related(
        'user', 'department', 'designation', 'program'
    ).all().order_by('employee_code')
    dept = request.query_params.get('department')
    if dept:
        faculty = faculty.filter(department__department_id=dept)
    status_filter = request.query_params.get('status')
    if status_filter:
        faculty = faculty.filter(status=status_filter)
    return Response(FacultySerializer(faculty, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_faculty(request):
    serializer = FacultyCreateSerializer(data=request.data)
    if serializer.is_valid():
        faculty = serializer.save()
        return Response(FacultySerializer(faculty).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def faculty_detail(request, faculty_id):
    try:
        faculty = Faculty.objects.select_related(
            'user', 'department', 'designation', 'program'
        ).get(faculty_id=faculty_id)
    except Faculty.DoesNotExist:
        return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(FacultySerializer(faculty).data)

    if request.method == 'PUT':
        allowed = {
            'status', 'designation', 'department', 'program', 'qualification', 'specialization',
            'office_floor', 'office_hours', 'employment_type',
        }
        data = {k: v for k, v in request.data.items() if k in allowed}
        serializer = FacultySerializer(faculty, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(FacultySerializer(faculty).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    from academics.models import CourseOffering
    if CourseOffering.objects.filter(faculty=faculty).exists():
        return Response(
            {'error': 'Cannot delete faculty assigned to courses. Reassign offerings first or mark inactive.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    faculty.status = 'inactive'
    faculty.save(update_fields=['status'])
    faculty.user.is_active = False
    faculty.user.save(update_fields=['is_active'])
    return Response({'message': 'Faculty member deactivated.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_faculty_profile(request):
    if request.user.user_type != 'teacher':
        return Response({'error': 'Only teacher accounts can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        faculty = Faculty.objects.select_related('user', 'department', 'designation', 'program').get(user=request.user)
        return Response(FacultySerializer(faculty).data)
    except Faculty.DoesNotExist:
        return Response({'error': 'No faculty record found for this account.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def employee_profile(request):
    user = request.user
    if user.user_type != 'teacher':
        return Response({'error': 'Only teachers can access this.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        faculty = Faculty.objects.get(user=user)
    except Faculty.DoesNotExist:
        return Response({'error': 'No faculty record found.'}, status=status.HTTP_404_NOT_FOUND)

    profile, _ = EmployeeProfile.objects.get_or_create(
        employee_id=faculty.faculty_id, employee_type='faculty'
    )

    if request.method == 'GET':
        return Response(EmployeeProfileSerializer(profile).data)

    serializer = EmployeeProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsTeacher])
def complete_teacher_onboarding(request):
    """Teacher completes profile after admin creates credentials."""
    try:
        faculty = Faculty.objects.select_related('user', 'department', 'designation').get(user=request.user)
    except Faculty.DoesNotExist:
        return Response({'error': 'No faculty record found.'}, status=status.HTTP_404_NOT_FOUND)

    required = ['qualification', 'specialization']
    for field in required:
        val = request.data.get(field, getattr(faculty, field, ''))
        if not str(val).strip():
            return Response({field: 'This field is required to complete onboarding.'}, status=status.HTTP_400_BAD_REQUEST)

    faculty.qualification = request.data.get('qualification', faculty.qualification)
    faculty.specialization = request.data.get('specialization', faculty.specialization)
    faculty.profile_completed = True
    faculty.save()

    profile, _ = EmployeeProfile.objects.get_or_create(
        employee_id=faculty.faculty_id, employee_type='faculty'
    )

    cnic = str(request.data.get('cnic', '')).strip()
    phone = str(request.data.get('phone_number', '')).strip()
    if cnic and (len(cnic) != 13 or not cnic.isdigit()):
        return Response({'cnic': 'CNIC must be exactly 13 digits.'}, status=status.HTTP_400_BAD_REQUEST)
    if phone and (len(phone) != 11 or not phone.isdigit()):
        return Response({'phone_number': 'Phone must be exactly 11 digits.'}, status=status.HTTP_400_BAD_REQUEST)

    emp_fields = [
        'cnic', 'date_of_birth', 'gender', 'phone_number',
        'emergency_contact_name', 'emergency_contact_phone',
        'emergency_contact_relation', 'current_address', 'permanent_address',
    ]
    for f in emp_fields:
        if request.data.get(f):
            setattr(profile, f, request.data[f])
    profile.save()

    return Response({
        'message': 'Profile completed successfully.',
        'faculty': FacultySerializer(faculty).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('faculty.view_faculty')])
def list_unassigned_program_courses(request):
    """Courses in a program that have no active teacher assignment."""
    program_id = request.query_params.get('program')
    if not program_id:
        return Response({'error': 'program query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
    program = DegreeProgram.objects.filter(program_id=program_id).first()
    if not program:
        return Response({'error': 'Invalid program.'}, status=status.HTTP_404_NOT_FOUND)

    assigned_course_ids = FacultyCourseAssignment.objects.filter(
        program=program, is_active=True,
    ).values_list('course_id', flat=True)

    pcs = ProgramCourse.objects.filter(program=program).exclude(
        course_id__in=assigned_course_ids,
    ).select_related('course').order_by('semester_number', 'course__course_code')

    data = [{
        'course_id': pc.course_id,
        'course_code': pc.course.course_code,
        'course_name': pc.course.course_name,
        'semester_number': pc.semester_number,
        'credit_hours': pc.course.credit_hours,
    } for pc in pcs]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('faculty.view_faculty')])
def list_faculty_course_assignments(request):
    qs = FacultyCourseAssignment.objects.filter(is_active=True).select_related(
        'faculty__user', 'program__department', 'course',
    ).order_by('faculty__employee_code', 'program__program_code', 'course__course_code')

    faculty_id = request.query_params.get('faculty')
    program_id = request.query_params.get('program')
    if faculty_id:
        qs = qs.filter(faculty__faculty_id=faculty_id)
    if program_id:
        qs = qs.filter(program__program_id=program_id)

    return Response(FacultyCourseAssignmentSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('faculty.view_faculty')])
def faculty_workload_summary(request):
    """Per-teacher course list with lecture count (one per program offering of same course)."""
    workload = {}
    for f in Faculty.objects.filter(status='active').select_related(
        'user', 'department', 'program',
    ).order_by('employee_code'):
        workload[f.faculty_id] = {
            'faculty_id': f.faculty_id,
            'employee_code': f.employee_code,
            'faculty_name': f.user.username,
            'department_name': f.department.department_name,
            'home_program': f.program.program_code if f.program_id else '',
            'lecture_count': 0,
            'courses': [],
        }

    assignments = list(
        FacultyCourseAssignment.objects.filter(is_active=True).select_related(
            'faculty__user', 'program', 'course',
        ).order_by('faculty__employee_code', 'course__course_code', 'program__program_code')
    )

    from academics.models import ProgramCourse
    program_ids = {a.program_id for a in assignments}
    course_ids = {a.course_id for a in assignments}
    semester_lookup = {}
    if program_ids and course_ids:
        for pc in ProgramCourse.objects.filter(
            program_id__in=program_ids, course_id__in=course_ids,
        ):
            semester_lookup[(pc.program_id, pc.course_id)] = pc.semester_number

    for a in assignments:
        row = workload.get(a.faculty_id)
        if not row:
            continue
        row['lecture_count'] += 1
        row['courses'].append({
            'assignment_id': a.assignment_id,
            'course_code': a.course.course_code,
            'course_name': a.course.course_name,
            'program_code': a.program.program_code,
            'program_name': a.program.program_name,
            'semester_number': semester_lookup.get((a.program_id, a.course_id)),
        })

    rows = sorted(workload.values(), key=lambda r: r['employee_code'])
    return Response({'workload': rows, 'total_teachers': len(rows)})


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_faculty_course_assignment(request):
    faculty_id = request.data.get('faculty_id')
    program_id = request.data.get('program_id')
    course_id = request.data.get('course_id')

    if not all([faculty_id, program_id, course_id]):
        return Response(
            {'error': 'faculty_id, program_id, and course_id are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    faculty = Faculty.objects.filter(faculty_id=faculty_id).first()
    program = DegreeProgram.objects.filter(program_id=program_id).first()
    course = Course.objects.filter(course_id=course_id).first()
    if not faculty or not program or not course:
        return Response({'error': 'Invalid faculty, program, or course.'}, status=status.HTTP_400_BAD_REQUEST)

    if not ProgramCourse.objects.filter(program=program, course=course).exists():
        return Response(
            {'error': f'{course.course_code} is not part of {program.program_code} curriculum.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from faculty.assignment_utils import assign_faculty_to_course
    try:
        assignment, created = assign_faculty_to_course(
            faculty, program, course, assigned_by=request.user,
        )
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        FacultyCourseAssignmentSerializer(assignment).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def remove_faculty_course_assignment(request, assignment_id):
    try:
        assignment = FacultyCourseAssignment.objects.get(assignment_id=assignment_id)
    except FacultyCourseAssignment.DoesNotExist:
        return Response({'error': 'Assignment not found.'}, status=status.HTTP_404_NOT_FOUND)

    assignment.is_active = False
    assignment.save(update_fields=['is_active'])
    return Response({'message': 'Teacher course assignment removed.'})
