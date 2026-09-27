import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    adminListApplications,
    adminGetApplicationDetail,
    adminMakeDecision,
    adminDownloadDocument,
    adminDeleteApplication,
    adminGetAdmissionSettings,
    adminUpdateAdmissionSettings,
} from '../../../services/admissionService';
import { listDepartments, listPrograms } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import {
    PageHeader, useTableFilter, TablePagination, LoadingSpinner,
    EmptyRow, useToast, getStatusBadgeClass, formatDate,
} from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { FileTextIcon, EyeIcon, XIcon, CheckCircleIcon } from '../../Icons';

const TAB_FILTERS = [
    { value: '', label: 'All (fee confirmed)' },
    { value: 'pending', label: 'Pending Review' },
    { value: 'accepted', label: 'Accepted' },
    { value: 'rejected', label: 'Rejected' },
];

const DECIDED_STATUSES = new Set(['approved', 'rejected', 'registered']);

const DetailRow = ({ label, value }) => (
    <div className="review-detail-row">
        <span className="review-detail-label">{label}</span>
        <span className="review-detail-value">{value || '—'}</span>
    </div>
);

const AdmissionsReviewPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [tabFilter, setTabFilter] = useState('');
    const [selectedDept, setSelectedDept] = useState('');
    const [selectedProgram, setSelectedProgram] = useState('');
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [selectedApp, setSelectedApp] = useState(null);
    const [detail, setDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [decision, setDecision] = useState('approved');
    const [rejectionReason, setRejectionReason] = useState('');
    const [remarks, setRemarks] = useState('');
    const [selectedProgramId, setSelectedProgramId] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [admissionsOpen, setAdmissionsOpen] = useState(true);
    const [settingsSaving, setSettingsSaving] = useState(false);

    const loadSettings = async () => {
        try {
            const data = await adminGetAdmissionSettings(token);
            setAdmissionsOpen(data?.is_open !== false);
        } catch (e) {
            console.error(e);
        }
    };

    const handleToggleAdmissions = async () => {
        if (settingsSaving) return;
        const next = !admissionsOpen;
        setSettingsSaving(true);
        try {
            const data = await adminUpdateAdmissionSettings({ is_open: next }, token);
            setAdmissionsOpen(data?.is_open !== false);
            showToast(next ? 'Admissions opened' : 'Admissions closed');
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to update admission status');
        } finally {
            setSettingsSaving(false);
        }
    };

    const load = async ({ silent = false } = {}) => {
        if (!silent) setLoading(true);
        try {
            const filters = {};
            if (tabFilter) filters.tab = tabFilter;
            if (selectedDept) filters.department = selectedDept;
            if (selectedProgram) filters.program = selectedProgram;
            const data = await adminListApplications(token, filters);
            setItems(Array.isArray(data) ? data : []);
        } catch (e) {
            console.error(e);
            showToast('Failed to load applications', 'error');
        } finally {
            if (!silent) setLoading(false);
        }
    };

    useEffect(() => { 
        if (token) {
            load();
            loadSettings();
            listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
        }
    }, [token, tabFilter, selectedDept, selectedProgram]);

    useEffect(() => {
        if (!token || !selectedDept) { setPrograms([]); return; }
        listPrograms(token, selectedDept).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, selectedDept]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(
        items,
        ['application_number', 'applicant_name', 'applicant_email', 'program_name', 'status']
    );

    const refreshDetail = async (appId) => {
        const data = await adminGetApplicationDetail(appId, token);
        setDetail(data);
        const prefs = data.preferences || [];
        if (prefs.length === 1) {
            const only = prefs[0];
            setSelectedProgramId(String(only.program_id ?? only.program ?? ''));
        } else if (data.status === 'registered' && data.program) {
            setSelectedProgramId(String(data.program));
        } else {
            setSelectedProgramId('');
        }
        if (data.decision) {
            setDecision(data.decision.decision || 'approved');
            setRejectionReason(data.decision.rejection_reason || '');
            setRemarks(data.decision.remarks || '');
        }
        return data;
    };

    const openDetail = async (app) => {
        setSelectedApp(app);
        setDetail(null);
        setDetailLoading(true);
        setDecision('approved');
        setRejectionReason('');
        setRemarks('');
        setSelectedProgramId('');
        try {
            await refreshDetail(app.id);
        } catch (e) {
            showToast('Failed to load application details', 'error');
            setSelectedApp(null);
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setSelectedApp(null);
        setDetail(null);
    };

    const hasDecision = detail && DECIDED_STATUSES.has(detail.status);
    const isRegistered = detail?.status === 'registered';

    const handleDecision = async () => {
        if (!selectedApp) return;
        if (!remarks.trim()) {
            alert('Remarks are required.');
            return;
        }
        if (decision === 'rejected' && !rejectionReason.trim()) {
            alert('Please provide a rejection reason.');
            return;
        }
        if (decision === 'approved' && !selectedProgramId) {
            alert('Please select a final program from the applicant preferences.');
            return;
        }
        setSubmitting(true);
        try {
            const result = await adminMakeDecision(selectedApp.id, {
                decision,
                rejection_reason: rejectionReason,
                remarks,
                selected_program_id: selectedProgramId ? parseInt(selectedProgramId, 10) : undefined,
            }, token);
            if (decision === 'approved') {
                const enrolled = result?.enrolled_courses || [];
                const warnings = result?.enrollment_warnings || [];
                if (enrolled.length) {
                    showToast(`Approved — enrolled in: ${enrolled.join(', ')}`, 'success');
                } else if (warnings.length) {
                    showToast(`Approved, but course enrollment pending: ${warnings[0]}`, 'warning');
                } else {
                    showToast('Approved — student registered automatically.', 'success');
                }
                if (warnings.length > 1) {
                    console.warn('Enrollment warnings:', warnings);
                }
            } else {
                showToast(`Application ${decision}.`);
            }
            await refreshDetail(selectedApp.id);
            await load({ silent: true });
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to submit decision');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteRejected = async () => {
        if (!selectedApp || detail?.status !== 'rejected') return;
        if (!confirm('Permanently delete this rejected application?')) return;
        try {
            await adminDeleteApplication(selectedApp.id, token);
            showToast('Rejected application deleted');
            closeDetail();
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Delete failed');
        }
    };

    const handleDownloadDoc = async (docId, fileName) => {
        try {
            const response = await adminDownloadDocument(selectedApp.id, docId, token);
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', fileName);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (e) {
            alert('Failed to download document');
        }
    };

    if (loading) return <LoadingSpinner message="Loading applications..." />;

    const sortedPreferences = [...(detail?.preferences || [])].sort(
        (a, b) => (a.preference_order || 0) - (b.preference_order || 0)
    );

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ADMISSIONS" title="Admission Applications Review" />

            <div className="form-card" style={{ marginBottom: '16px', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>Admission Window</div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                        {admissionsOpen
                            ? 'New applicants can register and submit applications.'
                            : 'Registration and application submission are disabled while admissions are closed.'}
                    </div>
                </div>
                <button
                    type="button"
                    className={`btn-verify ${admissionsOpen ? 'btn-success' : ''}`}
                    onClick={handleToggleAdmissions}
                    disabled={settingsSaving}
                    style={{
                        minWidth: 160,
                        background: admissionsOpen ? undefined : '#64748b',
                    }}
                >
                    {settingsSaving ? 'Saving...' : admissionsOpen ? 'Close Admissions' : 'Open Admissions'}
                </button>
            </div>

            <div className="application-tabs" style={{ marginBottom: '12px' }}>
                {TAB_FILTERS.map(f => (
                    <button key={f.value} className={`app-tab ${tabFilter === f.value ? 'active' : ''}`}
                        onClick={() => setTabFilter(f.value)}>
                        {f.label}
                    </button>
                ))}
            </div>

            <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <select className="field-input field-select" value={selectedDept} onChange={e => { setSelectedDept(e.target.value); setSelectedProgram(''); }}>
                    <option value="">All Departments</option>
                    {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                </select>
                <select className="field-input field-select" value={selectedProgram} onChange={e => setSelectedProgram(e.target.value)} disabled={!selectedDept}>
                    <option value="">All Programs</option>
                    {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                </select>
            </div>

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input
                            type="text"
                            placeholder="Search applications..."
                            className="search-input"
                            value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }}
                        />
                    </div>
                </div>

                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th>
                                <th>App No</th>
                                <th>Applicant</th>
                                <th>Program</th>
                                <th>Submitted</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={7} icon={<FileTextIcon size={20} />} title="No applications found" subtitle="Applications appear after Finance confirms admission fee payment." />
                            ) : paginated.map((item, i) => (
                                <tr key={item.id}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td><span className="app-number">{item.application_number}</span></td>
                                    <td>
                                        <div>{item.applicant_name || '—'}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>{item.applicant_email}</div>
                                    </td>
                                    <td>{item.program_name || '—'}</td>
                                    <td>{formatDate(item.submitted_at)}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase()}</span></td>
                                    <td>
                                        <button className="action-btn view-btn" onClick={() => openDetail(item)} title="Review">
                                            <EyeIcon size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && (
                    <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />
                )}
            </div>

            <ModalPortal isOpen={!!selectedApp} render={() => (
                <div className="modal-overlay" onClick={closeDetail}>
                    <div className="glass-modal glass-modal-lg" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Application Review — {selectedApp?.application_number}</h3>
                            <button className="close-btn" onClick={closeDetail} type="button"><XIcon /></button>
                        </div>

                        {detailLoading ? (
                            <div className="modal-body modal-body-centered">
                                <div className="loading-spinner">Loading details...</div>
                            </div>
                        ) : detail ? (
                            <div className="modal-body">
                                <div className="review-modal-grid">
                                    <div>
                                        <h3 className="review-section-title">Application</h3>
                                        <DetailRow label="Status" value={detail.status} />
                                        <DetailRow label="Program" value={detail.program_name} />
                                        <DetailRow label="Admission Type" value={detail.admission_type} />
                                        <DetailRow label="Challan No" value={detail.admission_challan_number} />
                                        <DetailRow label="Challan Amount" value={detail.admission_challan_amount ? `Rs. ${detail.admission_challan_amount}` : '—'} />
                                        <DetailRow label="Challan Paid" value={detail.challan_paid ? 'Yes' : 'No'} />
                                        <DetailRow label="Submitted" value={formatDate(detail.submitted_at)} />
                                    </div>
                                    <div>
                                        <h3 className="review-section-title">Applicant Profile</h3>
                                        <DetailRow label="Name" value={`${detail.applicant?.first_name || ''} ${detail.applicant?.last_name || ''}`} />
                                        <DetailRow label="Email" value={detail.applicant?.email} />
                                        <DetailRow label="CNIC" value={detail.applicant?.cnic} />
                                        <DetailRow label="Phone" value={detail.applicant?.phone} />
                                        <DetailRow label="Gender" value={detail.applicant?.gender} />
                                        <DetailRow label="DOB" value={detail.applicant?.date_of_birth} />
                                        <DetailRow label="Address" value={
                                            [detail.applicant?.perm_city, detail.applicant?.perm_state, detail.applicant?.perm_country].filter(Boolean).join(', ')
                                        } />
                                        <DetailRow label="Guardian" value={detail.applicant?.guardian_name} />
                                    </div>
                                </div>

                                <h3 className="review-section-title-spaced">Program Preferences</h3>
                                <div className="data-table-wrapper" style={{ marginBottom: '16px' }}>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                {!isRegistered && decision === 'approved' && <th>Final</th>}
                                                <th>Order</th>
                                                <th>Program</th>
                                                <th>Department</th>
                                                <th>Code</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sortedPreferences.length === 0 ? (
                                                <tr><td colSpan={isRegistered || decision !== 'approved' ? 4 : 5} className="empty-row">No preferences listed</td></tr>
                                            ) : sortedPreferences.map((pref) => {
                                                const prefProgramId = String(pref.program_id ?? pref.program ?? '');
                                                const isSelected = prefProgramId === String(selectedProgramId);
                                                return (
                                                    <tr key={pref.id ?? `${prefProgramId}-${pref.preference_order}`} className={isSelected ? 'pref-row-selected' : undefined}>
                                                        {!isRegistered && decision === 'approved' && (
                                                            <td>
                                                                <input
                                                                    type="radio"
                                                                    name="final-program"
                                                                    checked={isSelected}
                                                                    disabled={isRegistered}
                                                                    onChange={() => {
                                                                        setSelectedProgramId(prefProgramId);
                                                                    }}
                                                                />
                                                            </td>
                                                        )}
                                                        <td>{pref.preference_order}{pref.preference_order === 1 ? 'st' : pref.preference_order === 2 ? 'nd' : pref.preference_order === 3 ? 'rd' : 'th'}</td>
                                                        <td><strong>{pref.program_name}</strong></td>
                                                        <td>{pref.department_name || '—'}</td>
                                                        <td>{pref.program_code || '—'}</td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                                {!isRegistered && decision === 'approved' && selectedProgramId && (
                                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                        Final program selected: <strong>{sortedPreferences.find(p => String(p.program_id ?? p.program) === String(selectedProgramId))?.program_name || detail.program_name}</strong>
                                    </p>
                                )}

                                <h3 className="review-section-title-spaced">Academic Records</h3>
                                <div className="data-table-wrapper">
                                    <table className="data-table">
                                        <thead>
                                            <tr><th>Level</th><th>Qualification</th><th>Institute</th><th>Obtained</th><th>Total</th><th>Years</th></tr>
                                        </thead>
                                        <tbody>
                                            {(detail.applicant?.academic_records || []).length === 0 ? (
                                                <tr><td colSpan={6} className="empty-row">No records</td></tr>
                                            ) : (detail.applicant?.academic_records || []).map(r => (
                                                <tr key={r.id}>
                                                    <td>{r.qualification_level}</td>
                                                    <td>{r.qualification}</td>
                                                    <td>{r.institute}</td>
                                                    <td>{r.obtained}</td>
                                                    <td>{r.total}</td>
                                                    <td>{r.start_year}–{r.end_year}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                 <h3 className="review-section-title-spaced">Documents</h3>
                                <div className="data-table-wrapper">
                                    <table className="data-table">
                                        <thead>
                                            <tr><th>Type</th><th>File</th><th>OCR Status</th><th>Download</th></tr>
                                        </thead>
                                        <tbody>
                                            {(detail.applicant?.documents || []).length === 0 ? (
                                                <tr><td colSpan={4} className="empty-row">No documents uploaded</td></tr>
                                            ) : (detail.applicant?.documents || []).map(doc => (
                                                <tr key={doc.document_id}>
                                                    <td>{doc.document_type_display || doc.document_type}</td>
                                                    <td>
                                                        <div>{doc.file_name}</div>
                                                        {doc.verification_remarks && (
                                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                                                                {doc.verification_remarks.slice(0, 120)}{doc.verification_remarks.length > 120 ? '…' : ''}
                                                            </div>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <span className={doc.is_verified ? 'status-badge status-approved' : 'status-badge status-pending'}>
                                                            {doc.is_verified ? 'OCR VERIFIED' : 'NOT UPLOADED'}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <button
                                                            className="action-btn view-btn"
                                                            onClick={() => handleDownloadDoc(doc.document_id, doc.file_name)}
                                                        >
                                                            Download
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div className="admin-actions-panel">
                                    <h3 className="review-section-title">Admin Actions</h3>

                                    {detail.status === 'challan_pending' && (
                                        <div className="decision-banner" style={{ marginBottom: '16px' }}>
                                            Awaiting fee payment at the finance office. Admin review starts after Finance marks the challan paid.
                                        </div>
                                    )}

                                    {detail.challan_paid && detail.status === 'under_review' && (
                                        <div className="decision-banner approved" style={{ marginBottom: '16px' }}>
                                            Fee confirmed by Finance — application is ready for review.
                                        </div>
                                    )}

                                    {hasDecision && (
                                        <div className={`decision-banner ${detail.status === 'registered' ? 'approved' : detail.status}`}>
                                            Decision recorded: <strong>{detail.status?.toUpperCase()}</strong>
                                            {detail.decision?.rejection_reason && ` — ${detail.decision.rejection_reason}`}
                                            {isRegistered && (
                                                <>
                                                    {' — Student registered successfully'}
                                                    {detail.program_name && (
                                                        <> — Program: <strong>{detail.program_name}</strong></>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    )}

                                    <div className="workflow-step-label">Step 1 — Final Program &amp; Decision</div>
                                    {decision === 'approved' && !selectedProgramId && !isRegistered && sortedPreferences.length > 0 && (
                                        <p style={{ color: 'var(--accent-warning)', fontSize: '0.875rem', marginBottom: '12px' }}>
                                            Select a final program using the radio buttons in the preferences table above before approving.
                                        </p>
                                    )}
                                    <div style={{ marginBottom: '16px', maxWidth: '320px' }}>
                                        <div className="field-group">
                                            <label className="field-label">Decision <span className="required">*</span></label>
                                            <select
                                                className="field-input field-select"
                                                value={decision}
                                                onChange={e => setDecision(e.target.value)}
                                                disabled={isRegistered}
                                            >
                                                <option value="approved">Approve</option>
                                                <option value="rejected">Reject</option>
                                            </select>
                                        </div>
                                    </div>

                                    {decision === 'rejected' && (
                                        <div className="field-group" style={{ marginBottom: '12px' }}>
                                            <label className="field-label">Rejection Reason</label>
                                            <textarea
                                                className="field-input"
                                                rows={2}
                                                value={rejectionReason}
                                                onChange={e => setRejectionReason(e.target.value)}
                                                placeholder="Reason for rejection (shown internally)"
                                                disabled={isRegistered}
                                            />
                                        </div>
                                    )}

                                    <div className="field-group" style={{ marginBottom: '16px' }}>
                                        <label className="field-label">Remarks</label>
                                        <textarea
                                            className="field-input"
                                            rows={2}
                                            value={remarks}
                                            onChange={e => setRemarks(e.target.value)}
                                            placeholder="Optional remarks"
                                            disabled={isRegistered}
                                        />
                                    </div>

                                    {!isRegistered && (
                                        <button type="button" className="btn-save" onClick={handleDecision} disabled={submitting} style={{ marginBottom: '12px' }}>
                                            {submitting ? 'Saving...' : hasDecision ? 'Update Decision' : 'Submit Decision'}
                                        </button>
                                    )}

                                    {detail.status === 'rejected' && (
                                        <button type="button" className="action-btn danger" onClick={handleDeleteRejected}>
                                            Delete Rejected Application
                                        </button>
                                    )}

                                    {decision === 'approved' && (
                                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
                                            Approving automatically creates the student record and enrolls them in semester 1 courses.
                                        </p>
                                    )}
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )} />
        </div>
    );
};

export default AdmissionsReviewPage;
