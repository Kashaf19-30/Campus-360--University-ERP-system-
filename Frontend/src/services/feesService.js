import axios from 'axios';
import { apiGet, apiPost, apiDelete, BASE_URL, getAuthHeader } from './api';

const BASE = '/fees';

export const listFeeStructures = (token, params = '') => apiGet(`${BASE}/structures${params}`, token);
export const createFeeStructure = (data, token) => apiPost(`${BASE}/structures/create/`, data, token);
export const deleteFeeStructure = (structureId, token) => apiDelete(`${BASE}/structures/${structureId}/`, token);

export const myChallans = (token) => apiGet(`${BASE}/challans/me/`, token);
export const downloadMyChallan = async (challanId, token) => {
  const response = await axios.get(`${BASE_URL}${BASE}/challans/me/${challanId}/download/`, {
    ...getAuthHeader(token),
    responseType: 'blob',
  });
  return response;
};
