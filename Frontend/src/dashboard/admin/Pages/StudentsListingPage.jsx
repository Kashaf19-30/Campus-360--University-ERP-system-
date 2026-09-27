import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listStudents, getStudent, adminUpdateStudentProfile, adminDownloadStudentDocument } from '../../../services/studentsService';
import { listDepartments, listPrograms } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, getStatusBadgeClass, formatDate } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { UserIcon, XIcon } from '../../Icons';

const ProfileField = ({ label, value }) => (
    <p><strong>{label}:</strong> {value ?? '—'}</p>
);

const StudentsListingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [count, setCount] = useState(0);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [selectedDept, setSelectedDept] = useState('');
    const [selectedProgram, setSelectedProgram] = useState('');
    const [loading, setLoading] = useState(true);
    const [detail, setDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [profileForm, setProfileForm] = useState({});
    const [savingProfile, setSavingProfile] = useState(false);

    const downloadDoc = async (doc) => {
        if (!detail?.student_id) return;
        try {
            const res = await adminDownloadStudentDocument(detail.student_id, doc.document_id, token);
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', doc.file_name || 'document');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (e) {
            alert('Failed to download document');
        }
    };
    const buildParams = () => {
        const p = new URLSearchParams();
        if (selectedDept) p.set('department', selectedDept);
        if (selectedProgram) p.set('program', selectedProgram);
        const qs = p.toString();
        return qs ? `?${qs}` : '';
    };

    const load = async () => {
        setLoading(true);
        try {
            const data = await listStudents(token, buildParams());
            setItems(Array.isArray(data.students) ? data.students : normalizeList(data));
            setCount(data.count ?? (Array.isArray(data.students) ? data.students.length : 0));
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !selectedDept) { setPrograms([]); return; }
        listPrograms(token, selectedDept).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, selectedDept]);

    useEffect(() => { if (token) load(); }, [token, selectedDept, selectedProgram]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } =
        useTableFilter(items, ['registration_number', 'username', 'program_name']);

    const openDetail = async (student) => {
        setDetailLoading(true);
        setDetail(null);
        try {
            const d = await getStudent(student.student_id, token);
            setDetail(d);
            setProfileForm({
                blood_group: d.profile?.blood_group || '',
                guardian_phone: d.profile?.guardian_phone || '',
                guardian_name: d.profile?.guardian_name || '',
                residential_address: d.profile?.residential_address || '',
                permanent_address: d.profile?.permanent_address || '',
                profile_locked: d.profile?.profile_locked || false,
            });
        } catch (e) {
            showToast('Failed to load student details', 'error');
        } finally {
            setDetailLoading(false);
        }
    };

    const saveProfile = async () => {
        if (!detail) return;
        setSavingProfile(true);
        try {
            await adminUpdateStudentProfile(detail.student_id, profileForm, token);
            showToast('Profile updated');
            openDetail({ student_id: detail.student_id });
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to update profile');
        } finally {
            setSavingProfile(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading students..." />;

    const profile = detail?.profile;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > STUDENTS" title="Students Management" />

            <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <select className="field-input field-select" value={selectedDept} onChange={e => { setSelectedDept(e.target.value); setSelectedProgram(''); setPage(1); }}>
                    <option value="">All Departments</option>
                    {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                </select>
                <select className="field-input field-select" value={selectedProgram} onChange={e => { setSelectedProgram(e.target.value); setPage(1); }} disabled={!selectedDept}>
                    <option value="">All Programs</option>
                    {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                </select>
                <div className="stat-pill" style={{ alignSelf: 'center', padding: '8px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    Strength: <strong>{count}</strong>
                </div>
            </div>

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search students..." className="search-input" value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr><th>Sr#</th><th>Registration No.</th><th>Name</th><th>Program</th><th>Semester</th><th>Batch</th><th>Status</th><th>Action</th></tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={8} icon={<UserIcon size={20} />} title="No students found" />
                            ) : paginated.map((item, i) => (
                                <tr key={item.student_id}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td><span className="app-number" style={{ fontWeight: 600 }}>{item.registration_number || '—'}</span></td>
                                    <td>{item.username || '—'}</td>
                                    <td>{item.program_name || '—'}</td>
                                    <td>{item.current_semester || 1}</td>
                                    <td>{item.batch_year || '—'}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'ACTIVE'}</span></td>
                                    <td><button className="action-btn view-btn" onClick={() => openDetail(item)}>View Profile</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal isOpen={!!(detail || detailLoading)} render={() => (
                <div className="modal-overlay" onClick={() => setDetail(null)}>
                    <div className="glass-modal glass-modal-lg" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h3>Student Profile</h3>
                                {detail?.registration_number && (
                                    <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                        Registration No.: <span className="app-number" style={{ fontWeight: 700 }}>{detail.registration_number}</span>
                                    </p>
                                )}
                            </div>
                            <button className="close-btn" onClick={() => setDetail(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            {detailLoading ? <LoadingSpinner message="Loading..." /> : detail ? (
                                <>
                                    <h4 style={{ marginBottom: '8px' }}>Academic Information</h4>
                                    <div style={{ display: 'grid', gap: '6px', marginBottom: '16px' }}>
                                        <ProfileField label="Registration No." value={detail.registration_number} />
                                        <ProfileField label="Name" value={detail.username} />
                                        <ProfileField label="Email" value={detail.email} />
                                        <ProfileField label="Department" value={detail.department_name} />
                                        <ProfileField label="Program" value={detail.program_name} />
                                        <ProfileField label="Semester" value={detail.current_semester} />
                                        <ProfileField label="Batch" value={detail.batch_year} />
                                        <ProfileField label="CGPA" value={detail.cgpa} />
                                        <ProfileField label="Credit Hours" value={detail.total_credit_hours_completed} />
                                        <ProfileField label="Admission Date" value={formatDate(detail.admission_date)} />
                                        <ProfileField label="Status" value={detail.status?.toUpperCase()} />
                                    </div>

                                    {profile && (<>
                                        <h4 style={{ marginBottom: '8px' }}>Student Profile</h4>
                                        <div style={{ display: 'grid', gap: '10px', marginBottom: '16px' }}>
                                            <label className="field-label">
                                                <input type="checkbox" checked={!!profileForm.profile_locked}
                                                    onChange={e => setProfileForm(p => ({ ...p, profile_locked: e.target.checked }))} />
                                                {' '}Profile locked (student cannot edit)
                                            </label>
                                            <div className="field-group">
                                                <label className="field-label">Blood Group</label>
                                                <input className="field-input" value={profileForm.blood_group || ''}
                                                    onChange={e => setProfileForm(p => ({ ...p, blood_group: e.target.value }))} />
                                            </div>
                                            <div className="field-group">
                                                <label className="field-label">Guardian Name</label>
                                                <input className="field-input" value={profileForm.guardian_name || ''}
                                                    onChange={e => setProfileForm(p => ({ ...p, guardian_name: e.target.value }))} />
                                            </div>
                                            <div className="field-group">
                                                <label className="field-label">Guardian Phone</label>
                                                <input className="field-input" value={profileForm.guardian_phone || ''}
                                                    onChange={e => setProfileForm(p => ({ ...p, guardian_phone: e.target.value }))} />
                                            </div>
                                            <div className="field-group">
                                                <label className="field-label">Residential Address</label>
                                                <textarea className="field-input" rows={2} value={profileForm.residential_address || ''}
                                                    onChange={e => setProfileForm(p => ({ ...p, residential_address: e.target.value }))} />
                                            </div>
                                            <button type="button" className="btn-save" disabled={savingProfile} onClick={saveProfile}>
                                                {savingProfile ? 'Saving...' : 'Save Profile'}
                                            </button>
                                        </div>
                                    </>)}

                                    {detail.applicant_profile && (<>
                                        <h4 style={{ marginBottom: '8px' }}>Applicant Details</h4>
                                        <div style={{ display: 'grid', gap: '6px', marginBottom: '16px' }}>
                                            <ProfileField label="Full Name" value={`${detail.applicant_profile.first_name || ''} ${detail.applicant_profile.last_name || ''}`.trim()} />
                                            <ProfileField label="CNIC" value={detail.applicant_profile.cnic} />
                                            <ProfileField label="Phone" value={detail.applicant_profile.phone} />
                                            <ProfileField label="Email" value={detail.applicant_profile.email} />
                                        </div>
                                    </>)}

                                    {detail.academic_records?.length > 0 && (<>
                                        <h4 style={{ marginBottom: '8px' }}>Academic Records</h4>
                                        <ul style={{ marginBottom: '16px' }}>
                                            {detail.academic_records.map((r, idx) => (
                                                <li key={r.record_id || idx}>
                                                    {r.degree_level || r.qualification}: {r.institution_name} — {r.obtained_marks}/{r.total_marks}
                                                </li>
                                            ))}
                                        </ul>
                                    </>)}

                                    {detail.applicant_documents?.length > 0 && (<>
                                        <h4 style={{ marginBottom: '8px' }}>Submitted Documents</h4>
                                        <ul>
                                            {detail.applicant_documents.map(d => (
                                                <li key={d.document_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                                                    <span>{d.document_type_display || d.document_type}: {d.file_name}</span>
                                                    <button type="button" className="btn-secondary small" onClick={() => downloadDoc(d)}>Download</button>
                                                </li>
                                            ))}
                                        </ul>
                                    </>)}
                                </>
                            ) : null}
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export default StudentsListingPage;
