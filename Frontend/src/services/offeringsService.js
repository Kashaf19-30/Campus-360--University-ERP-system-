import { apiGet, apiPost } from './api';

const BASE = '/academics/offerings';

export const getMyOfferings = (token, params = '') =>
    apiGet(`${BASE}/me/${params ? `?${params}` : ''}`, token);

/** Active enrolled courses eligible for marks entry (not completed/locked). */
export const getMyOfferingsForMarks = (token) =>
    apiGet(`${BASE}/me/?marks_eligible=1`, token);

export const submitFinalMarks = (offeringId, token) =>
    apiPost(`${BASE}/${offeringId}/submit-marks/`, {}, token);

export const getOfferingStudents = (offeringId, token, attendanceDate = '', forMarks = false) => {
  const params = new URLSearchParams();
  if (attendanceDate) params.set('attendance_date', attendanceDate);
  if (forMarks) params.set('for_marks', '1');
  const qs = params.toString() ? `?${params.toString()}` : '';
  return apiGet(`${BASE}/${offeringId}/students/${qs}`, token);
};

/** @deprecated use getMyOfferings */
export const getMySections = getMyOfferings;
/** @deprecated use getOfferingStudents */
export const getSectionStudents = getOfferingStudents;
