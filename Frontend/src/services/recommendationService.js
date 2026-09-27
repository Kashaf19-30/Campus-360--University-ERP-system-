import { apiGet, apiPut } from './api';

const BASE = '/recommendations';

export const submitRecommendationProfile = (payload, token) =>
  apiPut(`${BASE}/profile/update/`, payload, token);

export const fetchRecommendations = (token) =>
  apiGet(`${BASE}/results/`, token);
