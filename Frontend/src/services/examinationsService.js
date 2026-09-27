import { apiGet, apiPost, apiPut, apiDelete } from './api';

const BASE = '/examinations';

export const listExamTypes = (token) => apiGet(`${BASE}/exam-types/`, token);
export const createExamType = (data, token) => apiPost(`${BASE}/exam-types/create/`, data, token);

export const listExaminations = (token, params = '') => {
  const qs = params ? (params.startsWith('?') ? params : `?${params}`) : '';
  return apiGet(`${BASE}/${qs}`, token);
};
export const getSemesterAssessmentStatus = (token, semesterId) =>
  apiGet(`${BASE}/semester/status/?semester_id=${semesterId}`, token);
export const initializeSemesterAssessments = (data, token) =>
  apiPost(`${BASE}/semester/initialize/`, data, token);
export const createExamination = (data, token) => apiPost(`${BASE}/create/`, data, token);
export const getExamination = (id, token) => apiGet(`${BASE}/${id}/`, token);
export const updateExamination = (id, data, token) => apiPut(`${BASE}/${id}/`, data, token);
export const deleteExamination = (id, token) => apiDelete(`${BASE}/${id}/`, token);

export const getMarksLockStatus = (params, token) => {
  const qs = new URLSearchParams(params).toString();
  return apiGet(`${BASE}/marks-lock-status/?${qs}`, token);
};

export const listMarksEditRequests = (token, status = 'pending') => {
  const qs = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiGet(`${BASE}/marks-edit-requests${qs}`, token);
};
export const requestMarksEdit = (data, token) => apiPost(`${BASE}/marks-edit-requests/create/`, data, token);
export const reviewMarksEditRequest = (id, data, token) => apiPost(`${BASE}/marks-edit-requests/${id}/review/`, data, token);

export const listMarks = (examId, token) => apiGet(`${BASE}/${examId}/marks/`, token);
export const enterMarks = (examId, data, token) => apiPost(`${BASE}/${examId}/marks/enter/`, data, token);
export const updateMarks = (marksId, data, token) => apiPut(`${BASE}/marks/${marksId}/`, data, token);

export const myFinalGrades = (token) => apiGet(`${BASE}/final-grades/me/`, token);
export const myAssessmentMarks = (token) => apiGet(`${BASE}/marks/me/`, token);
export const myResults = (token) => apiGet(`${BASE}/results/me/`, token);
export const generateSemesterResults = (data, token) => apiPost(`${BASE}/results/generate/`, data, token);
export const listResults = (token) => apiGet(`${BASE}/results/`, token);
export const publishResult = (id, token) => apiPost(`${BASE}/results/${id}/publish/`, {}, token);
export const publishSemesterResults = (data, token) => apiPost(`${BASE}/results/publish-semester/`, data, token);
export const approveResult = (id, token) => apiPost(`${BASE}/results/${id}/approve/`, {}, token);
export const computeOfferingGrades = (offeringId, token) => apiPost(`${BASE}/offerings/${offeringId}/compute-grades/`, {}, token);
export const unlockOfferingMarks = (offeringId, data, token) => apiPost(`${BASE}/offerings/${offeringId}/unlock-marks/`, data, token);
export const lockOfferingMarks = (offeringId, token) => apiPost(`${BASE}/offerings/${offeringId}/lock-marks/`, {}, token);
export const revokeMarksEditRequest = (id, token) => apiPost(`${BASE}/marks-edit-requests/${id}/revoke/`, {}, token);
export const createContinuousAssessment = (data, token) => apiPost(`${BASE}/continuous-assessments/create/`, data, token);
export const listOfferingEditRequests = (token, status = 'pending') => {
  const qs = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiGet(`${BASE}/offering-edit-requests/${qs}`, token);
};
export const requestOfferingMarksEdit = (data, token) => apiPost(`${BASE}/offering-edit-requests/`, data, token);
export const reviewOfferingMarksEdit = (id, data, token) =>
  apiPost(`${BASE}/offering-edit-requests/${id}/review/`, data, token);
