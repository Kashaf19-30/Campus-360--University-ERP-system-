import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listResults, publishResult, approveResult,
    generateSemesterResults, publishSemesterResults,
    listOfferingEditRequests, reviewOfferingMarksEdit,
} from '../../../services/examinationsService';
import { listSemesters } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, formatDate, getStatusBadgeClass, formatCurriculumSemester } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { FileTextIcon, XIcon } from '../../Icons';

const formatSemesterNumber = (item) => formatCurriculumSemester(item);

const ExaminationsListingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [activeTab, setActiveTab] = useState('results');
    const [results, setResults] = useState([]);
    const [offeringEditRequests, setOfferingEditRequests] = useState([]);
    const [promotionSummary, setPromotionSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [reviewModal, setReviewModal] = useState(null);
    const [reviewForm, setReviewForm] = useState({ action: 'approve', review_notes: '', hours: '', minutes: '' });
    const [semesters, setSemesters] = useState([]);
    const [genSemesterId, setGenSemesterId] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const [r, offeringReqs, sem] = await Promise.all([
                listResults(token),
                listOfferingEditRequests(token, 'pending'),
                listSemesters(token),
            ]);
            setResults(normalizeList(r));
            setOfferingEditRequests(Array.isArray(offeringReqs) ? offeringReqs : normalizeList(offeringReqs));
            const semList = normalizeList(sem);
            setSemesters(semList);
            if (semList.length && !genSemesterId) {
                const currentSem = semList.find(s => s.is_current) || semList[0];
                setGenSemesterId(String(currentSem?.semester_id || semList[0].semester_id));
            }
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    useEffect(() => {
        if (token) load();
    }, [token]);

    const currentData = activeTab === 'results' ? results : offeringEditRequests;
    const searchFields = activeTab === 'results'
        ? ['student_reg', 'semester_name']
        : ['course_code', 'course_name', 'faculty_name', 'reason'];
    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(currentData, searchFields);

    const handleGenerateResults = async () => {
        if (!genSemesterId) { alert('Select a semester'); return; }
        try {
            await generateSemesterResults({ semester_id: parseInt(genSemesterId, 10) }, token);
            showToast('Results generated from final grades');
            load();
        } catch (e) { alert(e.response?.data?.error || 'Failed to generate results'); }
    };

    const handlePublish = async (id) => {
        try {
            const res = await publishResult(id, token);
            const promo = res?.promotion || {};
            const graduationBlocked = promo.graduation_blocked ? [{
                registration_number: res.registration_number,
                student_name: res.student_name,
                result_status: res.result_status,
                reason: promo.reason,
                audit_issues: promo.audit?.issues || [],
            }] : [];
            setPromotionSummary({
                title: 'Result published',
                single: true,
                student: res.registration_number || res.student_name,
                result_status: res.result_status,
                promoted: promo.promoted ? [{
                    registration_number: res.registration_number,
                    student_name: res.student_name,
                    result_status: res.result_status,
                }] : [],
                held_back: !promo.promoted && !promo.graduated && !promo.graduation_blocked ? [{
                    registration_number: res.registration_number,
                    student_name: res.student_name,
                    result_status: res.result_status,
                    reason: promo.reason,
                }] : [],
                graduated: promo.graduated ? [{
                    registration_number: res.registration_number,
                    student_name: res.student_name,
                }] : [],
                graduation_blocked: graduationBlocked,
            });
            load();
        } catch (e) { alert(e.response?.data?.error || 'Failed to publish result'); }
    };

    const handlePublishSemester = async () => {
        if (!genSemesterId) { alert('Select a semester'); return; }
        if (!confirm('Publish all approved results for this semester? This will promote eligible students.')) return;
        try {
            const res = await publishSemesterResults({ semester_id: parseInt(genSemesterId, 10) }, token);
            setPromotionSummary({
                title: res.message || 'Semester results published',
                single: false,
                promoted: res.promoted || [],
                held_back: res.held_back || [],
                graduated: res.graduated || [],
                graduation_blocked: res.graduation_blocked || [],
                dismissal_review: res.dismissal_review || [],
                published_count: res.published_count,
            });
            load();
        } catch (e) { alert(e.response?.data?.error || 'Failed to publish semester results'); }
    };

    const handleApprove = async (id) => {
        try { await approveResult(id, token); showToast('Result approved'); load(); }
        catch (e) { alert('Failed to approve result'); }
    };

    const buildReviewDuration = () => {
        const payload = {};
        if (reviewForm.hours !== '') payload.hours = parseInt(reviewForm.hours, 10);
        if (reviewForm.minutes !== '') payload.minutes = parseInt(reviewForm.minutes, 10);
        return payload;
    };

    const openReviewModal = (item) => {
        setReviewModal(item);
        setReviewForm({ action: 'approve', review_notes: '', hours: '', minutes: '' });
    };

    const handleReviewRequest = async () => {
        if (!reviewModal) return;
        setSubmitting(true);
        try {
            const duration = buildReviewDuration();
            await reviewOfferingMarksEdit(
                reviewModal.request_id,
                {
                    action: reviewForm.action,
                    remarks: reviewForm.review_notes,
                    ...duration,
                },
                token,
            );
            showToast(`Request ${reviewForm.action === 'approve' ? 'approved' : 'rejected'}`);
            setReviewModal(null);
            setReviewForm({ action: 'approve', review_notes: '', hours: '', minutes: '' });
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to review request');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading results..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > RESULTS" title="Results & Marks" />

            <div className="form-card" style={{ marginBottom: 16, padding: '16px 20px' }}>
                <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
                    Teachers enter marks in their dashboard. Assessments are created automatically when courses are assigned and students enroll.
                </p>
                <ul style={{ margin: '10px 0 0', paddingLeft: '20px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    <li><strong>Publish Results</strong> — compute semester GPAs and release them to students.</li>
                    <li><strong>Marks Requests</strong> — approve when a teacher needs to fix marks after final submission (course-level unlock).</li>
                </ul>
            </div>

            <div className="application-tabs">
                <button className={`app-tab ${activeTab === 'results' ? 'active' : ''}`} onClick={() => { setActiveTab('results'); setPage(1); }}>Publish Results</button>
                <button className={`app-tab ${activeTab === 'marks-edit' ? 'active' : ''}`} onClick={() => { setActiveTab('marks-edit'); setPage(1); }}>
                    Marks Requests {offeringEditRequests.length > 0 && `(${offeringEditRequests.length})`}
                </button>
            </div>

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search..." className="search-input" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                    {activeTab === 'results' && (
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <select className="field-input field-select" value={genSemesterId} onChange={e => setGenSemesterId(e.target.value)}>
                                {semesters.map(s => <option key={s.semester_id} value={s.semester_id}>{s.semester_name}</option>)}
                            </select>
                            <button className="btn-secondary" onClick={handleGenerateResults}>Generate Results</button>
                            <button className="btn-primary" onClick={handlePublishSemester}>Publish Semester</button>
                        </div>
                    )}
                </div>
                <div className="data-table-wrapper">
                    {activeTab === 'results' ? (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Student</th><th>Semester</th><th>CGPA</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={6} icon={<FileTextIcon />} title="No results found" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.result_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{item.student_reg || '—'}</td>
                                        <td>{item.semester_name || '—'}</td>
                                        <td>{item.cgpa || '—'}</td>
                                        <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'PENDING'}</span></td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 8 }}>
                                                {item.is_published ? (
                                                    <span className={getStatusBadgeClass('published')}>PUBLISHED</span>
                                                ) : (
                                                    <button className="action-btn view-btn" onClick={() => handlePublish(item.result_id)}>Publish</button>
                                                )}
                                                <button className="action-btn" onClick={() => handleApprove(item.result_id)}>Approve</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Course</th><th>Teacher</th><th>Semester</th><th>Reason</th><th>Requested</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={8} icon={<FileTextIcon />} title="No pending marks edit requests" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.request_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>
                                            <strong>{item.course_code || '—'}</strong>
                                            {item.course_name && <><br /><small>{item.course_name}</small></>}
                                        </td>
                                        <td>{item.faculty_name || '—'}</td>
                                        <td>{formatSemesterNumber(item)}</td>
                                        <td>{item.reason || '—'}</td>
                                        <td>{formatDate(item.requested_at)}</td>
                                        <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase()}</span></td>
                                        <td>
                                            {item.status === 'pending' && (
                                                <button className="action-btn view-btn" onClick={() => openReviewModal(item)}>Review</button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal
                isOpen={!!reviewModal}
                render={() => (
                <div className="modal-overlay" onClick={() => setReviewModal(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Review Course Marks Edit</h3>
                            <button className="close-btn" onClick={() => setReviewModal(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            <p><strong>Course:</strong> {reviewModal.course_code}{reviewModal.course_name ? ` — ${reviewModal.course_name}` : ''}</p>
                            <p><strong>Teacher:</strong> {reviewModal.faculty_name}</p>
                            <p><strong>Semester:</strong> {formatSemesterNumber(reviewModal)}</p>
                            <p><strong>Reason:</strong> {reviewModal.reason || '—'}</p>
                            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                Approving unlocks the entire course until the teacher re-submits final marks.
                            </p>
                            <div className="field-group">
                                <label className="field-label">Action</label>
                                <select className="field-input field-select" value={reviewForm.action} onChange={e => setReviewForm({ ...reviewForm, action: e.target.value })}>
                                    <option value="approve">Approve</option>
                                    <option value="reject">Reject</option>
                                </select>
                            </div>
                            {reviewForm.action === 'approve' && (
                                <>
                                    <div className="two-column-grid">
                                        <div className="field-group">
                                            <label className="field-label">Hours</label>
                                            <input type="number" className="field-input" min={0}
                                                value={reviewForm.hours}
                                                onChange={e => setReviewForm({ ...reviewForm, hours: e.target.value })} />
                                        </div>
                                        <div className="field-group">
                                            <label className="field-label">Minutes</label>
                                            <input type="number" className="field-input" min={0} max={59}
                                                value={reviewForm.minutes}
                                                onChange={e => setReviewForm({ ...reviewForm, minutes: e.target.value })} />
                                        </div>
                                    </div>
                                    <p className="field-hint">Leave both blank for a default 48-hour edit window.</p>
                                </>
                            )}
                            <div className="field-group">
                                <label className="field-label">Review Notes</label>
                                <textarea className="field-input field-textarea" value={reviewForm.review_notes} onChange={e => setReviewForm({ ...reviewForm, review_notes: e.target.value })} />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setReviewModal(null)}>Cancel</button>
                            <button className="btn-primary" onClick={handleReviewRequest} disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Review'}</button>
                        </div>
                    </div>
                </div>
                )}
            />

            <ModalPortal
                isOpen={!!promotionSummary}
                render={() => (
                <div className="modal-overlay" onClick={() => setPromotionSummary(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>
                        <div className="modal-header">
                            <h3>{promotionSummary.title}</h3>
                            <button className="close-btn" onClick={() => setPromotionSummary(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            {!promotionSummary.single && (
                                <p style={{ marginBottom: 12 }}>Published: <strong>{promotionSummary.published_count ?? 0}</strong> result(s)</p>
                            )}
                            {promotionSummary.promoted?.length > 0 && (
                                <>
                                    <h4 style={{ color: 'var(--accent-success)' }}>Promoted ({promotionSummary.promoted.length})</h4>
                                    <ul style={{ marginBottom: 16 }}>
                                        {promotionSummary.promoted.map((s, i) => (
                                            <li key={i}>{s.registration_number} — {s.student_name} ({s.result_status})</li>
                                        ))}
                                    </ul>
                                </>
                            )}
                            {promotionSummary.held_back?.length > 0 && (
                                <>
                                    <h4 style={{ color: 'var(--accent-warning)' }}>Held back ({promotionSummary.held_back.length})</h4>
                                    <ul style={{ marginBottom: 16 }}>
                                        {promotionSummary.held_back.map((s, i) => (
                                            <li key={i}>{s.registration_number} — {s.student_name}: {s.reason || 'Failed semester'}</li>
                                        ))}
                                    </ul>
                                </>
                            )}
                            {promotionSummary.dismissal_review?.length > 0 && (
                                <>
                                    <h4 style={{ color: '#ef4444' }}>Dismissal review flagged ({promotionSummary.dismissal_review.length})</h4>
                                    <ul style={{ marginBottom: 16 }}>
                                        {promotionSummary.dismissal_review.map((s, i) => (
                                            <li key={i}>{s.registration_number} — {s.student_name} (probation #{s.consecutive_probation_count})</li>
                                        ))}
                                    </ul>
                                </>
                            )}
                            {promotionSummary.graduated?.length > 0 && (
                                <>
                                    <h4 style={{ color: 'var(--accent-primary)' }}>Graduated ({promotionSummary.graduated.length})</h4>
                                    <ul>
                                        {promotionSummary.graduated.map((s, i) => (
                                            <li key={i}>{s.registration_number} — {s.student_name}</li>
                                        ))}
                                    </ul>
                                </>
                            )}
                            {promotionSummary.graduation_blocked?.length > 0 && (
                                <>
                                    <h4 style={{ color: '#f59e0b' }}>Graduation blocked — audit required ({promotionSummary.graduation_blocked.length})</h4>
                                    <ul style={{ marginBottom: 16 }}>
                                        {promotionSummary.graduation_blocked.map((s, i) => (
                                            <li key={i}>
                                                {s.registration_number} — {s.student_name}: {s.reason || 'Degree audit incomplete'}
                                                {s.audit_issues?.length > 0 && (
                                                    <ul>{s.audit_issues.map((issue, j) => <li key={j}>{issue}</li>)}</ul>
                                                )}
                                            </li>
                                        ))}
                                    </ul>
                                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                        Review these students under <strong>Graduation Audit</strong> and confirm graduation manually.
                                    </p>
                                </>
                            )}
                            {!promotionSummary.promoted?.length && !promotionSummary.held_back?.length && !promotionSummary.graduated?.length && !promotionSummary.graduation_blocked?.length && (
                                <p>No promotion changes recorded.</p>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-primary" onClick={() => setPromotionSummary(null)}>Close</button>
                        </div>
                    </div>
                </div>
                )}
            />
        </div>
    );
};

export default ExaminationsListingPage;
