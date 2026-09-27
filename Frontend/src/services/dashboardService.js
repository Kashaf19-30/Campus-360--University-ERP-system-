import { apiGet } from './api';

const BASE = '/dashboard';

export const getDashboardStats = (token, params = '') => apiGet(`${BASE}/stats${params}`, token);
