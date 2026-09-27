import { apiGet, apiPost } from './api';

const BASE = '/fees';

export const getFinanceDashboard = (token, params = '') =>
  apiGet(`${BASE}/finance/dashboard${params}`, token);

export const listChallans = (token, params = '') =>
  apiGet(`${BASE}/challans${params}`, token);

export const markAdmissionPaid = (applicationId, paid, token) =>
  apiPost(`${BASE}/finance/admissions/${applicationId}/mark-paid/`, { paid }, token);

export const markChallanPaid = (challanId, paid, token) =>
  apiPost(`${BASE}/finance/challans/${challanId}/mark-paid/`, { paid }, token);
