import { apiGet, apiPut } from './api';

export const listRoles = (token) => apiGet('/roles/', token);

export const listPermissions = (token) => apiGet('/permissions/', token);

export const listRolePermissions = (token, roleId) => {
    const qs = roleId ? `?role_id=${roleId}` : '';
    return apiGet(`/role-permissions/${qs}`, token);
};

export const getRolePermissionsDetail = (token, roleId) =>
    apiGet(`/roles/${roleId}/permissions/`, token);

export const updateRolePermissions = (token, roleId, permissionNames) =>
    apiPut(`/roles/${roleId}/permissions/`, { permission_names: permissionNames }, token);
