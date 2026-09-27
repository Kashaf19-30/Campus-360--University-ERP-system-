import { apiGet, apiPost, apiPut, apiDelete } from './api';

const BASE = '/complaints';

export const listCategories = (token) => apiGet(`${BASE}/categories/`, token);
export const createCategory = (data, token) => apiPost(`${BASE}/categories/create/`, data, token);

export const submitComplaint = (data, token) => apiPost(`${BASE}/submit/`, data, token);
export const myComplaints = (token) => apiGet(`${BASE}/me/`, token);
export const listAllComplaints = (token) => apiGet(`${BASE}/`, token);
export const getComplaint = (id, token) => apiGet(`${BASE}/${id}/`, token);
export const updateComplaint = (id, data, token) => apiPut(`${BASE}/${id}/`, data, token);
export const deleteComplaint = (id, token) => apiDelete(`${BASE}/${id}/`, token);
export const adminUpdateComplaintStatus = (id, data, token) => apiPost(`${BASE}/${id}/admin-status/`, data, token);
export const listActiveComplaints = (token) => apiGet(`${BASE}/?active=true`, token);
export const getComplaintThread = (id, token) => apiGet(`${BASE}/${id}/thread/`, token);
export const postComplaintMessage = (id, data, token) => apiPost(`${BASE}/${id}/thread/`, data, token);
export const submitFeedback = (id, data, token) => apiPost(`${BASE}/${id}/feedback/submit/`, data, token);
