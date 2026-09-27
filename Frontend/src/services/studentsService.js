import axios from 'axios';
import { apiGet, apiPost, apiPut, getAuthHeader, BASE_URL } from './api';

const BASE = '/students';

export const listStudents = (token, params = '') => apiGet(`${BASE}/${params}`, token);
export const getStudent = (id, token) => apiGet(`${BASE}/${id}/`, token);
export const updateStudentStatus = (id, data, token) => apiPut(`${BASE}/${id}/status/`, data, token);
export const listAcademicStanding = (token, params = '') => apiGet(`${BASE}/academic-standing${params}`, token);
export const listGraduationCandidates = (token) => apiGet(`${BASE}/graduation-candidates/`, token);
export const getDegreeAudit = (studentId, token) => apiGet(`${BASE}/${studentId}/degree-audit/`, token);
export const myDegreeAudit = (token) => apiGet(`${BASE}/me/degree-audit/`, token);
export const confirmGraduation = (studentId, token) => apiPost(`${BASE}/${studentId}/confirm-graduation/`, {}, token);
export const getTranscript = (studentId, token) => apiGet(`${BASE}/${studentId}/transcript/`, token);
export const myTranscript = (token) => apiGet(`${BASE}/me/transcript/`, token);
export const manualPromoteStudent = (id, data, token) => apiPost(`${BASE}/${id}/promote/`, data, token);
export const repeatSemester = (id, token) => apiPost(`${BASE}/${id}/repeat/`, {}, token);
export const confirmDismissal = (id, token) => apiPost(`${BASE}/${id}/confirm-dismissal/`, {}, token);
export const clearDismissalReview = (id, token) => apiPost(`${BASE}/${id}/clear-review/`, {}, token);
export const getMyStudentProfile = (token) => apiGet(`${BASE}/me/`, token);
export const updateMyStudentProfile = (data, token) => apiPut(`${BASE}/me/profile/`, data, token);
export const adminUpdateStudentProfile = (studentId, data, token) =>
  apiPut(`${BASE}/${studentId}/profile/`, data, token);
export const adminDownloadStudentDocument = (studentId, docId, token) =>
  axios.get(`${BASE_URL}${BASE}/${studentId}/documents/${docId}/download/`, {
    ...getAuthHeader(token),
    responseType: 'blob',
  });
export const myDegreeProgress = (token) => apiGet(`${BASE}/me/degree-progress/`, token);
