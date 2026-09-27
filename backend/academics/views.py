from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import ProtectedError
from accounts.permissions import IsAdmin, require_any_permission, IsSuperuser
from accounts.audit import log_audit
from .models import Department, DegreeProgram, Semester, Course, ProgramCourse, CoursePrerequisite, AcademicPolicy
from .serializers import (
    DepartmentSerializer, DegreeProgramSerializer,
    SemesterSerializer, CourseSerializer, ProgramCourseSerializer,
    ProgramCourseCreateSerializer, AcademicPolicySerializer,
)


# ── DEPARTMENTS ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_department', 'academics.view_program',
    'admissions.view_application', 'faculty.view_faculty', 'students.view_student',
)])
def list_departments(request):
    departments = Department.objects.all().order_by('department_name')
    if request.query_params.get('active_only') == '1':
        departments = departments.filter(is_active=True)
    elif request.user.user_type != 'admin':
        departments = departments.filter(is_active=True)
    return Response(DepartmentSerializer(departments, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_department(request):
    serializer = DepartmentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def department_detail(request, department_id):
    try:
        department = Department.objects.get(department_id=department_id)
    except Department.DoesNotExist:
        return Response({'error': 'Department not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(DepartmentSerializer(department).data)

    if request.method == 'PUT':
        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if department.programs.exists():
        return Response(
            {'error': 'Cannot delete department with linked programs. Remove programs first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    blockers = []
    if department.courses.exists():
        blockers.append(f'{department.courses.count()} course(s)')
    if department.faculty_members.exists():
        blockers.append(f'{department.faculty_members.count()} faculty member(s)')
    if blockers:
        return Response(
            {'error': f'Cannot delete department with linked {" and ".join(blockers)}. Remove them first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        department.delete()
    except ProtectedError:
        return Response(
            {'error': 'Cannot delete department because other records still reference it.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    log_audit(request, 'delete', 'department', department_id)
    return Response({'message': 'Department deleted.'}, status=status.HTTP_200_OK)


# ── DEGREE PROGRAMS ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_program', 'admissions.submit_application',
    'enrollments.view_enrollment', 'fees.view_fees', 'fees.manage_fees',
)])
def list_programs(request):
    programs = DegreeProgram.objects.select_related('department').all()
    if request.user.user_type != 'admin' and request.query_params.get('all') != '1':
        programs = programs.filter(is_active=True)
    dept = request.query_params.get('department')
    if dept:
        programs = programs.filter(department__department_id=dept)
    return Response(DegreeProgramSerializer(programs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_program(request):
    data = request.data.copy()
    data['program_type'] = 'morning'
    serializer = DegreeProgramSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def program_detail(request, program_id):
    try:
        program = DegreeProgram.objects.select_related('department').get(program_id=program_id)
    except DegreeProgram.DoesNotExist:
        return Response({'error': 'Program not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(DegreeProgramSerializer(program).data)

    if request.method == 'PUT':
        data = request.data.copy()
        data.pop('program_type', None)
        serializer = DegreeProgramSerializer(program, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    program.delete()
    return Response({'message': 'Program deleted.'}, status=status.HTTP_200_OK)


# ── SEMESTERS ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_program', 'academics.view_offering',
    'enrollments.view_enrollment', 'attendance.view_attendance',
    'fees.view_fees', 'fees.manage_fees',
)])
def list_semesters(request):
    semesters = Semester.objects.all().order_by('-academic_year', '-semester_type')
    return Response(SemesterSerializer(semesters, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperuser])
def create_semester(request):
    serializer = SemesterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def semester_detail(request, semester_id):
    try:
        semester = Semester.objects.get(semester_id=semester_id)
    except Semester.DoesNotExist:
        return Response({'error': 'Semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not (request.user.is_superuser or request.user.user_type == 'admin'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(SemesterSerializer(semester).data)

    if not request.user.is_superuser:
        return Response(
            {
                'error': (
                    'Academic terms are configured at setup via '
                    'python manage.py seed_erp_data — not from the admin dashboard.'
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SemesterSerializer(semester, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_program', 'academics.view_offering',
    'enrollments.view_enrollment', 'attendance.view_attendance',
)])
def get_current_semester(request):
    try:
        semester = Semester.objects.get(is_current=True)
        return Response(SemesterSerializer(semester).data)
    except Semester.DoesNotExist:
        return Response({'error': 'No current semester set.'}, status=status.HTTP_404_NOT_FOUND)


# ── COURSES ───────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_course', 'enrollments.view_enrollment',
    'academics.view_offering', 'examinations.view_examination',
)])
def list_courses(request):
    courses = Course.objects.select_related('department').filter(is_active=True)
    dept = request.query_params.get('department')
    program = request.query_params.get('program')
    if dept:
        courses = courses.filter(department__department_id=dept)
    if program:
        course_ids = ProgramCourse.objects.filter(
            program__program_id=program
        ).values_list('course_id', flat=True)
        courses = courses.filter(course_id__in=course_ids)
    return Response(CourseSerializer(courses, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_course(request):
    serializer = CourseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def course_detail(request, course_id):
    try:
        course = Course.objects.select_related('department').get(course_id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CourseSerializer(course).data)

    if request.method == 'PUT':
        serializer = CourseSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    course.is_active = False
    course.save(update_fields=['is_active'])
    return Response({'message': 'Course deactivated.'}, status=status.HTTP_200_OK)


# ── PROGRAM COURSES ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'system.admin_access', 'academics.view_course', 'academics.view_program', 'enrollments.view_enrollment',
)])
def list_program_courses(request, program_id):
    courses = ProgramCourse.objects.select_related(
        'course', 'course__department', 'program'
    ).filter(program__program_id=program_id).order_by('semester_number', 'course__course_code')
    sem = request.query_params.get('semester')
    if sem:
        courses = courses.filter(semester_number=sem)
    return Response(ProgramCourseSerializer(courses, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def add_program_course(request):
    serializer = ProgramCourseCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        program = DegreeProgram.objects.select_related('department').get(program_id=data['program'])
    except DegreeProgram.DoesNotExist:
        return Response({'error': 'Invalid program.'}, status=status.HTTP_400_BAD_REQUEST)

    department_id = data.get('department') or program.department_id
    try:
        department = Department.objects.get(department_id=department_id)
    except Department.DoesNotExist:
        return Response({'error': 'Invalid department.'}, status=status.HTTP_400_BAD_REQUEST)

    course, _ = Course.objects.update_or_create(
        course_code=data['course_code'],
        defaults={
            'department': department,
            'course_name': data['course_name'],
            'credit_hours': data['credit_hours'],
            'theory_credit_hours': data['theory_credit_hours'],
            'lab_credit_hours': data['lab_credit_hours'],
            'course_type': data['course_type'],
            'is_active': True,
        },
    )

    is_core = data['course_type'] == 'core'
    pc, created = ProgramCourse.objects.update_or_create(
        program=program,
        course=course,
        semester_number=data['semester_number'],
        defaults={'is_core': is_core},
    )

    prereq_codes = data.get('prerequisite_codes') or []
    if prereq_codes:
        CoursePrerequisite.objects.filter(course=course).delete()
        for code in prereq_codes:
            if code.endswith('+ CH') or code.endswith('+ credit hours'):
                continue
            if '+' in code and 'CH' in code.upper():
                try:
                    min_ch = int(code.split('+')[0].strip())
                    CoursePrerequisite.objects.get_or_create(
                        course=course,
                        prerequisite_type='credit_hours',
                        min_credit_hours=min_ch,
                        defaults={'prerequisite_course': None},
                    )
                except ValueError:
                    pass
                continue
            prereq_course = Course.objects.filter(course_code=code).first()
            if prereq_course:
                CoursePrerequisite.objects.get_or_create(
                    course=course,
                    prerequisite_type='course',
                    prerequisite_course=prereq_course,
                    defaults={'min_credit_hours': None},
                )

    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(ProgramCourseSerializer(pc).data, status=status_code)


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def remove_program_course(request, program_course_id):
    try:
        pc = ProgramCourse.objects.get(program_course_id=program_course_id)
    except ProgramCourse.DoesNotExist:
        return Response({'error': 'Program course mapping not found.'}, status=status.HTTP_404_NOT_FOUND)
    pc.delete()
    return Response({'message': 'Program course removed.'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAdmin])
def academic_policy(request):
    from .policy_utils import get_academic_policy
    policy = get_academic_policy()

    if request.method == 'GET':
        return Response(AcademicPolicySerializer(policy).data)

    serializer = AcademicPolicySerializer(policy, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        log_audit(request, 'update_academic_policy', 'academic_policy', policy.policy_id, new_value=serializer.data)
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
