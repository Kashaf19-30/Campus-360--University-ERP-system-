import { apiGet, apiPost, apiPut, apiDelete } from './api';

const BASE = '/attendance';

export const listAttendance = (token, params = '') => apiGet(`${BASE}/${params ? '?' + params : ''}`, token);
export const markAttendance = (data, token) => apiPost(`${BASE}/mark/`, data, token);
export const nextLectureNumber = (offeringId, token) => apiGet(`${BASE}/next-lecture/?offering_id=${offeringId}`, token);
export const myAttendanceSummary = (token, offeringId = '') => {
  const params = new URLSearchParams();
  if (offeringId) params.set('offering', offeringId);
  const qs = params.toString();
  return apiGet(`${BASE}/summary/me/${qs ? '?' + qs : ''}`, token);
};
export const listAttendanceSummaries = (token, params = '') => apiGet(`${BASE}/summary/${params ? '?' + params : ''}`, token);
export const submitLeave = (data, token) => apiPost(`${BASE}/leaves/submit/`, data, token);
export const myLeaves = (token) => apiGet(`${BASE}/leaves/me/`, token);
export const deleteLeave = (id, token) => apiDelete(`${BASE}/leaves/${id}/`, token);
export const teacherLeaves = (token) => apiGet(`${BASE}/leaves/teacher/`, token);
export const reviewLeave = (id, data, token) => apiPost(`${BASE}/leaves/${id}/review/`, data, token);