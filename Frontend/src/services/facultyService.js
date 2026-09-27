import { apiGet, apiPost, apiPut, apiDelete } from './api';

const BASE = '/faculty';

export const listDesignations = (token) => apiGet(`${BASE}/designations/`, token);

export const listFaculty = (token, departmentId = '') => {
  const qs = departmentId ? `?department=${departmentId}` : '';
  return apiGet(`${BASE}${qs}`, token);
};

export const getFaculty = (id, token) => apiGet(`${BASE}/${id}/`, token);

export const updateFaculty = (id, data, token) => apiPut(`${BASE}/${id}/`, data, token);

export const deleteFaculty = (id, token) => apiDelete(`${BASE}/${id}/`, token);

export const getMyFacultyProfile = (token) => apiGet(`${BASE}/me/`, token);

export const completeTeacherOnboarding = (data, token) =>
  apiPost(`${BASE}/onboarding/complete/`, data, token);

export const listFacultyCourseAssignments = (token, params = '') =>
  apiGet(`${BASE}/course-assignments${params}`, token);

export const listUnassignedProgramCourses = (programId, token) =>
  apiGet(`${BASE}/course-assignments/unassigned/?program=${programId}`, token);

export const createFacultyCourseAssignment = (data, token) =>
  apiPost(`${BASE}/course-assignments/create/`, data, token);

export const removeFacultyCourseAssignment = (assignmentId, token) =>
  apiDelete(`${BASE}/course-assignments/${assignmentId}/`, token);

export const getFacultyWorkload = (token) =>
  apiGet(`${BASE}/workload/`, token);
