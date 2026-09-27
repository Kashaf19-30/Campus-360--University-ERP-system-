import axios from 'axios';

/** API base URL — set VITE_API_URL in Frontend/.env for production deploys. */
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const getAuthHeader = (token) => ({
  headers: { Authorization: `Bearer ${token}` }
});

const TOKEN_KEY = 'token';

const getStoredToken = () => sessionStorage.getItem(TOKEN_KEY);

let unauthorizedHandler = null;
let tokenUpdateHandler = null;
let refreshPromise = null;

const isAuthRefreshRequest = (config) => {
  const url = config?.url || '';
  return url.includes('/auth/refresh/');
};

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

export const setTokenUpdateHandler = (handler) => {
  tokenUpdateHandler = handler;
};

const refreshAccessToken = async () => {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const token = getStoredToken();
    if (!token) return null;
    try {
      const response = await axios.post(`${BASE_URL}/auth/refresh/`, {}, {
        headers: { Authorization: `Bearer ${token}` },
        _skipAuthRefresh: true,
      });
      const newToken = response.data?.token;
      if (newToken) {
        sessionStorage.setItem(TOKEN_KEY, newToken);
        if (tokenUpdateHandler) tokenUpdateHandler(newToken);
        return newToken;
      }
    } catch {
      // refresh failed — caller handles logout
    }
    return null;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
};

axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (!original || original._skipAuthRefresh) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401) {
      if (isAuthRefreshRequest(original)) {
        if (unauthorizedHandler) unauthorizedHandler();
        return Promise.reject(error);
      }

      if (!original._authRetry) {
        original._authRetry = true;
        const newToken = await refreshAccessToken();
        if (newToken) {
          original.headers = original.headers || {};
          original.headers.Authorization = `Bearer ${newToken}`;
          return axios(original);
        }
        if (unauthorizedHandler) unauthorizedHandler();
      }
    }
    return Promise.reject(error);
  },
);

export const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  if (data?.students) return data.students;
  if (data?.enrollments) return data.enrollments;
  return data?.results || [];
};

export const apiGet = async (url, token) => {
  const response = await axios.get(`${BASE_URL}${url}`, getAuthHeader(token));
  return response.data;
};

export const apiPost = async (url, data, token) => {
  const response = await axios.post(`${BASE_URL}${url}`, data, getAuthHeader(token));
  return response.data;
};

export const apiPut = async (url, data, token) => {
  const response = await axios.put(`${BASE_URL}${url}`, data, getAuthHeader(token));
  return response.data;
};

export const apiDelete = async (url, token) => {
  const response = await axios.delete(`${BASE_URL}${url}`, getAuthHeader(token));
  return response.data;
};

export default axios;
