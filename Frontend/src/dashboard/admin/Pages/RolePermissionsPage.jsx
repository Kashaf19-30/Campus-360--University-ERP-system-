import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listRoles, listPermissions, getRolePermissionsDetail, updateRolePermissions,
} from '../../../services/rbacService';
import { normalizeList } from '../../../services/api';
import { PageHeader, LoadingSpinner } from '../../shared/helpers';
import { ShieldIcon } from '../../Icons';

const EDITABLE_ROLES = new Set(['Teacher', 'Student', 'Applicant']);
const BLOCKED_LABELS = new Set([
    'system.admin_access',
    'system.view_audit_log',
    'system.manage_role_permissions',
    'accounts.create_credentials',
]);

/** Permissions shown in workflow view (role-relevant only). */
const WORKFLOW_PERMISSIONS = {
    Teacher: [
        'academics.view_offering',
        'examinations.view_examination', 'examinations.enter_marks', 'examinations.view_marks',
        'examinations.request_marks_edit',
        'attendance.view_attendance', 'attendance.mark_attendance',
        'complaints.use_thread_complaint', 'complaints.view_complaint',
        'announcements.view_announcement',
        'faculty.view_own_profile',
    ],
    Student: [
        'enrollments.view_own_enrollment',
        'examinations.view_own_results', 'examinations.view_own_grades',
        'attendance.view_own_attendance',
        'fees.view_own_fees',
        'complaints.view_own_complaint', 'complaints.create_complaint',
        'announcements.view_announcement',
        'students.view_own_profile',
    ],
    Applicant: [
        'admissions.submit_application', 'admissions.view_own_application',
    ],
};

const RolePermissionsPage = () => {
    const { token } = useAuth();
    const [roles, setRoles] = useState([]);
    const [allPermissions, setAllPermissions] = useState([]);
    const [selectedRoleId, setSelectedRoleId] = useState('');
    const [roleDetail, setRoleDetail] = useState(null);
    const [selected, setSelected] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [loadingRole, setLoadingRole] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [showAdvanced, setShowAdvanced] = useState(false);

    useEffect(() => {
        if (!token) return;
        setLoading(true);
        Promise.all([listRoles(token), listPermissions(token)])
            .then(([rolesData, permsData]) => {
                const roleList = normalizeList(rolesData);
                setRoles(roleList);
                setAllPermissions(normalizeList(permsData));
                const firstEditable = roleList.find((r) => EDITABLE_ROLES.has(r.role_name));
                if (firstEditable) setSelectedRoleId(String(firstEditable.role_id));
            })
            .catch((e) => setError(e.response?.data?.error || 'Failed to load RBAC data'))
            .finally(() => setLoading(false));
    }, [token]);

    useEffect(() => {
        if (!token || !selectedRoleId) return;
        setLoadingRole(true);
        setMessage('');
        setError('');
        getRolePermissionsDetail(token, selectedRoleId)
            .then((detail) => {
                setRoleDetail(detail);
                setSelected(new Set((detail.permissions || []).map((p) => p.permission_name)));
            })
            .catch((e) => setError(e.response?.data?.error || 'Failed to load role permissions'))
            .finally(() => setLoadingRole(false));
    }, [token, selectedRoleId]);

    const grouped = useMemo(() => {
        const roleName = roleDetail?.role_name;
        const workflowSet = roleName && !showAdvanced
            ? new Set(WORKFLOW_PERMISSIONS[roleName] || [])
            : null;

        const map = {};
        for (const p of allPermissions) {
            if (workflowSet && !workflowSet.has(p.permission_name)) continue;
            const mod = p.module_name || 'other';
            if (!map[mod]) map[mod] = [];
            map[mod].push(p);
        }
        return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
    }, [allPermissions, roleDetail?.role_name, showAdvanced]);

    const workflowCount = roleDetail?.role_name
        ? (WORKFLOW_PERMISSIONS[roleDetail.role_name] || []).length
        : 0;

    const isEditable = roleDetail?.editable !== false && EDITABLE_ROLES.has(roleDetail?.role_name);

    const toggle = (name) => {
        if (!isEditable || BLOCKED_LABELS.has(name)) return;
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(name)) next.delete(name);
            else next.add(name);
            return next;
        });
    };

    const handleSave = async () => {
        if (!isEditable) return;
        setSaving(true);
        setMessage('');
        setError('');
        try {
            const names = [...selected].filter((n) => !BLOCKED_LABELS.has(n));
            await updateRolePermissions(token, selectedRoleId, names);
            setMessage(`Permissions saved for ${roleDetail.role_name}. Users must re-login to pick up changes.`);
        } catch (e) {
            setError(e.response?.data?.error || 'Failed to save permissions');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading roles and permissions..." />;

    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > ROLE PERMISSIONS" title="Role Permissions" />

            <div className="form-card" style={{ marginBottom: 20 }}>
                <div className="section-header">
                    <div className="section-header-icon"><ShieldIcon /></div>
                    <div>
                        <h2 className="section-title">Manage role access</h2>
                        <p style={{ color: '#666', margin: '4px 0 0 0' }}>
                            Admin role always has full access and cannot be edited.
                            Privileged permissions (system admin, audit log, credentials) cannot be assigned to other roles.
                        </p>
                    </div>
                </div>

                <div className="field-group" style={{ maxWidth: 360, marginTop: 16 }}>
                    <label className="field-label">Select role</label>
                    <select
                        className="field-input field-select"
                        value={selectedRoleId}
                        onChange={(e) => setSelectedRoleId(e.target.value)}
                    >
                        {roles.map((r) => (
                            <option key={r.role_id} value={r.role_id}>
                                {r.role_name}{r.role_name === 'Admin' ? ' (read-only)' : ''}
                            </option>
                        ))}
                    </select>
                </div>

                {roleDetail?.role_name && EDITABLE_ROLES.has(roleDetail.role_name) && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={showAdvanced}
                            onChange={(e) => setShowAdvanced(e.target.checked)}
                        />
                        <span>Show all permissions ({allPermissions.length} total — workflow view shows {workflowCount})</span>
                    </label>
                )}

                {error && <p style={{ color: '#ef4444', marginTop: 12 }}>{error}</p>}
                {message && <p style={{ color: '#16a34a', marginTop: 12 }}>{message}</p>}
            </div>

            {loadingRole ? (
                <LoadingSpinner message="Loading role permissions..." />
            ) : roleDetail?.role_name === 'Admin' ? (
                <div className="form-card">
                    <p style={{ color: '#666' }}>
                        The Admin role has all {allPermissions.length} permissions and cannot be modified here.
                    </p>
                </div>
            ) : (
                <>
                    {grouped.map(([module, perms]) => (
                        <div key={module} className="form-card" style={{ marginBottom: 16 }}>
                            <h3 style={{ textTransform: 'capitalize', marginBottom: 12 }}>{module}</h3>
                            <div className="two-column-grid">
                                {perms.map((p) => {
                                    const blocked = BLOCKED_LABELS.has(p.permission_name);
                                    const checked = selected.has(p.permission_name);
                                    return (
                                        <label
                                            key={p.permission_id}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'flex-start',
                                                gap: 8,
                                                opacity: blocked ? 0.5 : 1,
                                                cursor: isEditable && !blocked ? 'pointer' : 'not-allowed',
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                disabled={!isEditable || blocked}
                                                onChange={() => toggle(p.permission_name)}
                                            />
                                            <span>
                                                <strong>{p.permission_name}</strong>
                                                {p.description && (
                                                    <span style={{ display: 'block', fontSize: 12, color: '#666' }}>
                                                        {p.description}
                                                    </span>
                                                )}
                                                {blocked && (
                                                    <span style={{ display: 'block', fontSize: 11, color: '#ef4444' }}>
                                                        Admin-only — cannot assign
                                                    </span>
                                                )}
                                            </span>
                                        </label>
                                    );
                                })}
                            </div>
                        </div>
                    ))}

                    {isEditable && (
                        <div className="form-actions">
                            <button type="button" className="btn-save" disabled={saving} onClick={handleSave}>
                                {saving ? 'Saving...' : `Save ${roleDetail?.role_name} permissions`}
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default RolePermissionsPage;
