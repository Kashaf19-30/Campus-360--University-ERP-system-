import { apiGet, apiPost, apiPut, apiDelete } from './api';

const BASE = '/academics';

export const listDepartments = (token, params = '') =>
  apiGet(`${BASE}/departments/${params}`, token);
export const createDepartment = (data, token) => apiPost(`${BASE}/departments/create/`, data, token);
export const getDepartment = (id, token) => apiGet(`${BASE}/departments/${id}/`, token);
export const updateDepartment = (id, data, token) => apiPut(`${BASE}/departments/${id}/`, data, token);
export const deleteDepartment = (id, token) => apiDelete(`${BASE}/departments/${id}/`, token);

export const listPrograms = (token, departmentId = '') => {
  const qs = departmentId ? `?department=${departmentId}` : '';
  return apiGet(`${BASE}/programs/${qs}`, token);
};
export const createProgram = (data, token) => apiPost(`${BASE}/programs/create/`, data, token);
export const getProgram = (id, token) => apiGet(`${BASE}/programs/${id}/`, token);
export const updateProgram = (id, data, token) => apiPut(`${BASE}/programs/${id}/`, data, token);
export const deleteProgram = (id, token) => apiDelete(`${BASE}/programs/${id}/`, token);

export const listSemesters = (token) => apiGet(`${BASE}/semesters/`, token);
export const getCurrentSemester = (token) => apiGet(`${BASE}/semesters/current/`, token);
export const createSemester = (data, token) => apiPost(`${BASE}/semesters/create/`, data, token);
export const updateSemester = (id, data, token) => apiPut(`${BASE}/semesters/${id}/`, data, token);

export const listCourses = (token, params = '') => apiGet(`${BASE}/courses/${params}`, token);
export const listProgramCourses = (programId, token, semester = '') => {
  const qs = semester ? `?semester=${semester}` : '';
  return apiGet(`${BASE}/programs/${programId}/courses/${qs}`, token);
};
export const addProgramCourse = (data, token) => apiPost(`${BASE}/program-courses/add/`, data, token);
export const removeProgramCourse = (id, token) => apiDelete(`${BASE}/program-courses/${id}/`, token);

export const getAcademicPolicy = (token) => apiGet(`${BASE}/policy/`, token);
export const updateAcademicPolicy = (data, token) => apiPut(`${BASE}/policy/`, data, token);
