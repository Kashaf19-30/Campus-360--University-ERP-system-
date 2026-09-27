import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listFaculty, getFaculty, updateFaculty, deleteFaculty } from '../../../services/facultyService';
import { listDepartments } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, getStatusBadgeClass } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { UserIcon, XIcon, TrashIcon } from '../../Icons';

const EMPLOYMENT_OPTIONS = [
    { value: 'permanent', label: 'Permanent' },
    { value: 'visiting', label: 'Visiting' },
    { value: 'contract', label: 'Contract' },
    { value: 'contractual', label: 'Contractual' },
];

const FacultyListingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [selectedDept, setSelectedDept] = useState('');
    const [loading, setLoading] = useState(true);
    const [selectedFaculty, setSelectedFaculty] = useState(null);
    const [detail, setDetail] = useState(null);
    const [editForm, setEditForm] = useState({ office_floor: '', office_hours: '', employment_type: 'permanent' });
    const [detailLoading, setDetailLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const data = await listFaculty(token, selectedDept);
            setItems(normalizeList(data));
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => { if (token) load(); }, [token, selectedDept]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } =
        useTableFilter(items, ['employee_code', 'username', 'department_name', 'program_name']);

    const openDetail = async (item) => {
        setSelectedFaculty(item);
        setDetailLoading(true);
        try {
            const d = await getFaculty(item.faculty_id, token);
            setDetail(d);
            setEditForm({
                office_floor: d.office_floor || '',
                office_hours: d.office_hours || '',
                employment_type: d.employment_type || 'permanent',
            });
        } catch (e) {
            showToast('Failed to load faculty details', 'error');
            setSelectedFaculty(null);
        } finally {
            setDetailLoading(false);
        }
    };

    const handleSaveProfile = async () => {
        if (!selectedFaculty) return;
        setSaving(true);
        try {
            const updated = await updateFaculty(selectedFaculty.faculty_id, editForm, token);
            setDetail(updated);
            showToast('Faculty profile updated');
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update profile');
        } finally {
            setSaving(false);
        }
    };

    const closeModal = () => {
        setSelectedFaculty(null);
        setDetail(null);
    };

    const toggleStatus = async (item, e) => {
        e.stopPropagation();
        const newStatus = item.status === 'active' ? 'inactive' : 'active';
        try {
            await updateFaculty(item.faculty_id, { status: newStatus }, token);
            showToast(`Status updated to ${newStatus}`);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update status');
        }
    };

    const handleDelete = async (item, e) => {
        e.stopPropagation();
        if (!confirm(`Delete faculty member ${item.employee_code}?`)) return;
        try {
            await deleteFaculty(item.faculty_id, token);
            showToast('Faculty member deleted');
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Delete failed');
        }
    };

    if (loading) return <LoadingSpinner message="Loading faculty..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > FACULTY" title="Faculty Management" />
            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search faculty..." className="search-input" value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                    <select className="field-input field-select" value={selectedDept} onChange={e => { setSelectedDept(e.target.value); setPage(1); }}
                        style={{ maxWidth: '240px' }}>
                        <option value="">All Departments</option>
                        {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                    </select>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th><th>Employee ID</th><th>Name</th><th>Department</th>
                                <th>Program</th><th>Designation</th><th>Status</th><th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={8} icon={<UserIcon size={20} />} title="No faculty found" />
                            ) : paginated.map((item, i) => (
                                <tr key={item.faculty_id} style={{ cursor: 'pointer' }} onClick={() => openDetail(item)}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td><span className="app-number">{item.employee_code || '—'}</span></td>
                                    <td>{item.username || '—'}</td>
                                    <td>{item.department_name || '—'}</td>
                                    <td>{item.program_name || '—'}</td>
                                    <td>{item.designation_title || '—'}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'ACTIVE'}</span></td>
                                    <td onClick={e => e.stopPropagation()}>
                                        <button className="action-btn" onClick={(e) => toggleStatus(item, e)}>
                                            {item.status === 'active' ? 'Deactivate' : 'Activate'}
                                        </button>
                                        <button className="action-btn danger" onClick={(e) => handleDelete(item, e)}><TrashIcon size={14} /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal
                isOpen={!!selectedFaculty}
                render={() => (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '640px', width: '95%' }}>
                        <div className="modal-header">
                            <h3>Faculty Profile — {selectedFaculty.employee_code}</h3>
                            <button className="close-btn" onClick={closeModal}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            {detailLoading ? <LoadingSpinner message="Loading..." /> : detail ? (
                                <div style={{ display: 'grid', gap: '8px' }}>
                                    <p><strong>Name:</strong> {detail.username}</p>
                                    <p><strong>Email:</strong> {detail.email}</p>
                                    <p><strong>Department:</strong> {detail.department_name}</p>
                                    <p><strong>Program:</strong> {detail.program_name || '—'}</p>
                                    <p><strong>Designation:</strong> {detail.designation_title}</p>
                                    <p><strong>Qualification:</strong> {detail.qualification}</p>
                                    <p><strong>Specialization:</strong> {detail.specialization || '—'}</p>
                                    <p><strong>Status:</strong> {detail.status}</p>

                                    <hr />
                                    <h4 style={{ margin: '8px 0' }}>Office & Employment</h4>
                                    <div className="field-group">
                                        <label className="field-label">Employment Type</label>
                                        <select className="field-input field-select" value={editForm.employment_type}
                                            onChange={e => setEditForm({ ...editForm, employment_type: e.target.value })}>
                                            {EMPLOYMENT_OPTIONS.map(o => (
                                                <option key={o.value} value={o.value}>{o.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="field-group">
                                        <label className="field-label">Office Floor</label>
                                        <input className="field-input" value={editForm.office_floor}
                                            onChange={e => setEditForm({ ...editForm, office_floor: e.target.value })} />
                                    </div>
                                    <div className="field-group">
                                        <label className="field-label">Office Hours</label>
                                        <input className="field-input" value={editForm.office_hours}
                                            onChange={e => setEditForm({ ...editForm, office_hours: e.target.value })} />
                                    </div>

                                    {detail.employee_profile && (<>
                                        <hr />
                                        <p><strong>CNIC:</strong> {detail.employee_profile.cnic || '—'}</p>
                                        <p><strong>Phone:</strong> {detail.employee_profile.phone_number || '—'}</p>
                                        <p><strong>DOB:</strong> {detail.employee_profile.date_of_birth || '—'}</p>
                                        <p><strong>Address:</strong> {detail.employee_profile.current_address || '—'}</p>
                                    </>)}
                                </div>
                            ) : null}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={closeModal}>Close</button>
                            <button className="btn-primary" onClick={handleSaveProfile} disabled={saving || detailLoading}>
                                {saving ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </div>
                </div>
                )}
            />
        </div>
    );
};

export default FacultyListingPage;
