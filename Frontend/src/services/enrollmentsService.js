import { apiGet, apiPost } from './api';

const BASE = '/enrollments';

/** Visible course rows (regular + approved repeat) for the current semester enrollment payload. */
export const flattenActiveEnrollments = (data) => {
    const enrollments = Array.isArray(data) ? data : (data?.enrollments || []);
    return enrollments.flatMap(e =>
        (e.course_registrations || [])
            .filter(r => r.status === 'registered')
            .map(r => ({
                ...r,
                semester_name: r.semester_label || r.semester_name || (r.curriculum_semester != null ? `Semester ${r.curriculum_semester}` : e.semester_label || e.semester_name),
            }))
    );
};

export const listEnrollments = (token, params = '') => apiGet(`${BASE}/${params}`, token);
export const myEnrollments = (token) => apiGet(`${BASE}/me/`, token);
export const getMyFailedCourses = (token) => apiGet(`${BASE}/repeat-requests/failed/`, token);
export const submitRepeatRequests = (courseIds, token) =>
  apiPost(`${BASE}/repeat-requests/`, { course_ids: courseIds }, token);
export const listRepeatRequests = (token, params = '') =>
  apiGet(`${BASE}/repeat-requests/admin${params}`, token);
export const reviewRepeatRequest = (requestId, action, token, remarks = '') =>
  apiPost(`${BASE}/repeat-requests/${requestId}/review/`, { action, remarks }, token);

export const getSemesterProgress = (token, curriculumSemester) =>
  apiGet(`${BASE}/academic-progress/semester/?curriculum_semester=${curriculumSemester}`, token);

export const getRepeatProgress = (token, curriculumSemester) =>
  apiGet(`${BASE}/academic-progress/repeat/?curriculum_semester=${curriculumSemester}`, token);

export const promoteSemesterBatch = (token, curriculumSemester) =>
  apiPost(`${BASE}/academic-progress/promote/`, { curriculum_semester: curriculumSemester }, token);

export const getMyAcademicStatus = (token) =>
  apiGet(`${BASE}/academic-progress/my-status/`, token);

export const getTeacherAcademicWarnings = (token) =>
  apiGet(`${BASE}/academic-progress/teacher-warnings/`, token);
