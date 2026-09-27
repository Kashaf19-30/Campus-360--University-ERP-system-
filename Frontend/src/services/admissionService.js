// src/services/admissionService.js
import axios from 'axios';
import { BASE_URL } from './api';

const ADMISSIONS_URL = `${BASE_URL}/admissions`;

const getAuthHeader = (token) => ({
  headers: { Authorization: `Bearer ${token}` }
});

const EMPTY_APPLICANT_PROFILE = (username = '') => ({
  firstName: '', lastName: '', fatherName: '', cnic: '', gender: '', cellPhone: '', dob: '',
  religion: '', nationality: 'Pakistani', maritalStatus: '', username,
  profileImage: null, disability: false,
  residence: { perm_country: '', perm_state: '', perm_city: '', perm_address: '' },
  emergency: { name: '', relation: '', phone: '' },
  guardian: { name: '', cnic: '', relation: '' },
});

const mapApplicantProfile = (data, currentUsername = '') => ({
  id: data.id,
  firstName: data.first_name || '',
  lastName: data.last_name || '',
  fatherName: data.father_name || '',
  cnic: data.cnic || '',
  gender: data.gender || '',
  cellPhone: data.phone || '',
  dob: data.date_of_birth || '',
  religion: data.religion || '',
  nationality: data.nationality || 'Pakistani',
  maritalStatus: data.marital_status || '',
  username: data.username || currentUsername,
  profileImage: data.profile_image || null,
  disability: data.disability || false,
  residence: {
    perm_country: data.perm_country || '',
    perm_state: data.perm_state || '',
    perm_city: data.perm_city || '',
    perm_address: data.perm_address || '',
  },
  emergency: {
    name: data.emergency_name || '',
    relation: data.emergency_relation || '',
    phone: data.emergency_phone || '',
  },
  guardian: {
    name: data.guardian_name || '',
    cnic: data.guardian_cnic || '',
    relation: data.guardian_relation || '',
  },
});

export const getApplicantProfile = async (token, currentUsername = '') => {
  try {
    const response = await axios.get(`${ADMISSIONS_URL}/profile/`, getAuthHeader(token));
    const data = response.data || {};
    if (data.id) localStorage.setItem('applicantProfileId', data.id);
    return mapApplicantProfile(data, currentUsername);
  } catch (error) {
    if (error.response?.status === 404) {
      return EMPTY_APPLICANT_PROFILE(currentUsername);
    }
    console.error('Failed to fetch applicant profile:', error);
    throw error;
  }
};

export const prepareProfileForBackend = (profileData) => {
  const residence = profileData.residence || {};
  const emergency = profileData.emergency || {};
  const guardian = profileData.guardian || {};

  const payload = {
    first_name: profileData.firstName || '',
    last_name: profileData.lastName || '',
    father_name: profileData.fatherName || '',
    cnic: profileData.cnic || '',
    gender: profileData.gender || '',
    phone: profileData.cellPhone || '',
    date_of_birth: profileData.dob || null,
    religion: profileData.religion || '',
    nationality: profileData.nationality || 'Pakistani',
    marital_status: profileData.maritalStatus || '',
    perm_country: residence.perm_country || '',
    perm_state: residence.perm_state || '',
    perm_city: residence.perm_city || '',
    perm_address: residence.perm_address || '',
    emergency_name: emergency.name || '',
    emergency_relation: emergency.relation || '',
    emergency_phone: emergency.phone || '',
    guardian_name: guardian.name || '',
    guardian_cnic: guardian.cnic || '',
    guardian_relation: guardian.relation || '',
  };
  if (profileData.profileImage && String(profileData.profileImage).startsWith('data:image')) {
    payload.profile_image = profileData.profileImage;
  }
  return payload;
};

export const saveApplicantProfile = async (profileData, token) => {
  const response = await axios.post(`${ADMISSIONS_URL}/profile/`, profileData, getAuthHeader(token));
  return response.data;
};

export const addAcademicRecord = async (recordData, token) => {
  const response = await axios.post(`${ADMISSIONS_URL}/academic/`, recordData, getAuthHeader(token));
  return response.data;
};

export const getAcademicRecords = async (token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/academic/list/`, getAuthHeader(token));
  return response.data;
};

export const deleteAcademicRecord = async (recordId, token) => {
  const response = await axios.delete(`${ADMISSIONS_URL}/academic/${recordId}/`, getAuthHeader(token));
  return response.data;
};

export const getAdmissionPrograms = async (token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/programs/`, getAuthHeader(token));
  const data = response.data;
  const list = Array.isArray(data) ? data : (data?.results || []);
  return list.map((p) => ({
    program_id: p.program_id ?? p.id,
    program_name: p.program_name || p.name || '',
    program_code: p.program_code || '',
    department_name: p.department_name || p.department?.department_name || '',
    degree_level: p.degree_level,
    duration_years: p.duration_years,
    accepting_admissions: p.accepting_admissions,
  })).filter((p) => p.program_id != null && p.program_name);
};

export const submitApplication = async (applicationData, token) => {
  const response = await axios.post(`${ADMISSIONS_URL}/application/`, applicationData, getAuthHeader(token));
  return response.data;
};

export const getMyApplications = async (token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/application/`, getAuthHeader(token));
  return response.data;
};

export const deleteApplication = async (applicationId, token) => {
  const response = await axios.delete(`${ADMISSIONS_URL}/application/${applicationId}/`, getAuthHeader(token));
  return response.data;
};

export const getMyDocuments = async (token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/documents/`, getAuthHeader(token));
  return response.data;
};

export const uploadDocument = async (documentData, token) => {
  const formData = new FormData();
  formData.append('file', documentData.file);
  formData.append('document_type', documentData.document_type);

  const response = await axios.post(`${ADMISSIONS_URL}/documents/upload/`, formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const deleteDocument = async (documentId, token) => {
  const response = await axios.delete(`${ADMISSIONS_URL}/documents/${documentId}/`, getAuthHeader(token));
  return response.data;
};

export const adminListApplications = async (token, filters = {}) => {
  const response = await axios.get(`${ADMISSIONS_URL}/admin/applications/`, {
    ...getAuthHeader(token),
    params: filters,
  });
  return response.data;
};

export const adminGetApplicationDetail = async (applicationId, token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/admin/applications/${applicationId}/`, getAuthHeader(token));
  return response.data;
};

export const adminMakeDecision = async (applicationId, decisionData, token) => {
  const response = await axios.post(
    `${ADMISSIONS_URL}/admin/applications/${applicationId}/decide/`,
    decisionData,
    getAuthHeader(token),
  );
  return response.data;
};

export const adminDownloadDocument = async (applicationId, docId, token) => {
  const response = await axios.get(
    `${ADMISSIONS_URL}/admin/applications/${applicationId}/documents/${docId}/download/`,
    { ...getAuthHeader(token), responseType: 'blob' },
  );
  return response;
};

export const adminDeleteApplication = async (applicationId, token) => {
  const response = await axios.delete(
    `${ADMISSIONS_URL}/admin/applications/${applicationId}/delete/`,
    getAuthHeader(token),
  );
  return response.data;
};

export const isApplicationLocked = (applications) => {
  const lockedStatuses = ['pending', 'challan_pending', 'under_review', 'documents_pending', 'approved', 'rejected', 'registered'];
  const apps = Array.isArray(applications) ? applications : [];
  return apps.some(app => lockedStatuses.includes(app.status));
};

export const getApplicationChallanPending = (applications) => {
  const apps = Array.isArray(applications) ? applications : [];
  return apps.find(app => app.status === 'challan_pending');
};

export const downloadAdmissionChallan = async (token, format = 'pdf') => {
  const response = await axios.get(`${ADMISSIONS_URL}/challan/download/`, {
    ...getAuthHeader(token),
    params: format === 'json' ? { format: 'json' } : {},
    responseType: format === 'pdf' ? 'blob' : 'json',
  });
  return response;
};

export const hasRejectedApplication = (applications) => {
  const apps = Array.isArray(applications) ? applications : [];
  return apps.some(app => app.status === 'rejected');
};

export const getPublicAdmissionSettings = async () => {
  const response = await axios.get(`${ADMISSIONS_URL}/settings/`);
  return response.data;
};

export const adminGetAdmissionSettings = async (token) => {
  const response = await axios.get(`${ADMISSIONS_URL}/admin/settings/`, getAuthHeader(token));
  return response.data;
};

export const adminUpdateAdmissionSettings = async (payload, token) => {
  const response = await axios.patch(`${ADMISSIONS_URL}/admin/settings/`, payload, getAuthHeader(token));
  return response.data;
};
