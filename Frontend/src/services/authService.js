import axios from 'axios';
import { BASE_URL } from './api';

export const loginUser = async (email, password) => {
    const response = await axios.post(`${BASE_URL}/auth/login/`, {
        email: email,
        password: password
    });
    return response.data;
};

export const registerUser = async (username, email, password, confirmPassword, profile = {}) => {
    const response = await axios.post(`${BASE_URL}/auth/register/`, {
        username: username,
        email: email,
        password: password,
        confirm_password: confirmPassword,
        first_name: profile.firstName || '',
        last_name: profile.lastName || '',
        gender: profile.gender || '',
        date_of_birth: profile.dob || null,
        cnic: profile.cnic || null,
        phone: profile.phone || '',
    });
    return response.data;
};

export const getCurrentUser = async (token) => {
    const response = await axios.get(`${BASE_URL}/auth/me/`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });
    return response.data;
};

export const logoutUser = async (token) => {
    const response = await axios.post(`${BASE_URL}/auth/logout/`, {}, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

export const changePassword = async (oldPassword, newPassword, token) => {
    const response = await axios.post(`${BASE_URL}/auth/change-password/`, {
        old_password: oldPassword,
        new_password: newPassword,
    }, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

export const requestPasswordReset = async (email) => {
    const response = await axios.post(`${BASE_URL}/auth/password-reset/request/`, { email });
    return response.data;
};

export const confirmPasswordReset = async (token, newPassword) => {
    const response = await axios.post(`${BASE_URL}/auth/password-reset/confirm/`, {
        token,
        new_password: newPassword,
        confirm_password: newPassword,
    });
    return response.data;
};

export const refreshAuthToken = async (token) => {
    const response = await axios.post(`${BASE_URL}/auth/refresh/`, {}, {
        headers: { Authorization: `Bearer ${token}` },
        _skipAuthRefresh: true,
    });
    return response.data;
};

export const changeUserType = async (userId, userType, token) => {
    const response = await axios.post(`${BASE_URL}/users/change-type/`, {
        user_id: userId,
        user_type: userType,
    }, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};
