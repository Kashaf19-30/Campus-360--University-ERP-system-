import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listGraduationCandidates, getDegreeAudit, confirmGraduation, getTranscript,
} from '../../../services/studentsService';
import {
    PageHeader, LoadingSpinner, EmptyRow, useToast, getStatusBadgeClass,
} from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { UserIcon, XIcon } from '../../Icons';

const GraduationAuditPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [candidates, setCandidates] = useState([]);
    const [readyCount, setReadyCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [auditDetail, setAuditDetail] = useState(null);
    const [transcript, setTranscript] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const data = await listGraduationCandidates(token);
            setCandidates(data.candidates || []);
            setReadyCount(data.ready_count ?? 0);
        } catch (e) {
            console.error(e);
            showToast('Failed to load graduation candidates', 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) load();
    }, [token]);

    const openAudit = async (studentId) => {
        try {
            const data = await getDegreeAudit(studentId, token);
            setAuditDetail(data);
            setTranscript(null);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to load audit');
        }
    };

    const openTranscript = async (studentId) => {
        try {
            const data = await getTranscript(studentId, token);
            setTranscript(data);
            setAuditDetail(null);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to load transcript');
        }
    };

    const handleConfirmGraduation = async () => {
        if (!auditDetail?.student_id) return;
        if (!confirm(`Confirm graduation for ${auditDetail.registration_number}?`)) return;
        setSubmitting(true);
        try {
            const result = await confirmGraduation(auditDetail.student_id, token);
            showToast(result?.message || 'Graduation confirmed');
            setAuditDetail(null);
            setTranscript(result?.transcript || null);
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Graduation failed');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading graduation candidates..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > GRADUATION" title="Graduation Audit" />

            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, maxWidth: 720 }}>
                Review degree completion before confirming graduation. A student must pass all program courses,
                meet the minimum CGPA, clear all fee challans, and have no academic review flags.
            </p>

            <div className="stat-pill" style={{ padding: '10px 16px', background: 'var(--bg-secondary)', borderRadius: 8, marginBottom: 16, display: 'inline-block' }}>
                Ready to graduate: <strong>{readyCount}</strong> / {candidates.length} candidates
            </div>

            <div className="form-card">
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Reg No</th><th>Student</th><th>Program</th><th>Sem</th>
                                <th>CGPA</th><th>Progress</th><th>Status</th><th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {candidates.length === 0 ? (
                                <EmptyRow colSpan={8} icon={<UserIcon size={20} />} title="No graduation candidates yet" />
                            ) : candidates.map(c => (
                                <tr key={c.student_id}>
                                    <td><span className="app-number">{c.registration_number}</span></td>
                                    <td>{c.student_name}</td>
                                    <td>{c.program_name}</td>
                                    <td>{c.current_semester}</td>
                                    <td>{c.cgpa}</td>
                                    <td>{c.degree_completion_percent}%</td>
                                    <td>
                                        <span className={getStatusBadgeClass(
                                            c.bucket === 'ready' ? 'active' : c.bucket === 'blocked' ? 'pending' : 'inactive'
                                        )}>
                                            {c.bucket === 'ready' ? 'READY' : c.bucket === 'blocked' ? 'BLOCKED' : 'IN PROGRESS'}
                                        </span>
                                    </td>
                                    <td>
                                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                            <button className="action-btn view-btn" onClick={() => openAudit(c.student_id)}>Audit</button>
                                            <button className="action-btn" onClick={() => openTranscript(c.student_id)}>Transcript</button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <ModalPortal isOpen={!!auditDetail} render={() => (
                <div className="modal-overlay" onClick={() => setAuditDetail(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 640, maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="modal-header">
                            <h3>Degree Audit — {auditDetail?.registration_number}</h3>
                            <button className="close-btn" onClick={() => setAuditDetail(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            {auditDetail && (
                                <>
                                    <p><strong>{auditDetail.student_name}</strong> — {auditDetail.program_name}</p>
                                    <p>CGPA: <strong>{auditDetail.cgpa}</strong> (min {auditDetail.min_cgpa_graduation})</p>
                                    <p>Progress: {auditDetail.completed_courses}/{auditDetail.total_courses} courses · {auditDetail.earned_credit_hours}/{auditDetail.total_credit_hours} CH</p>
                                    <p>
                                        Eligible:{' '}
                                        <span className={getStatusBadgeClass(auditDetail.eligible ? 'active' : 'inactive')}>
                                            {auditDetail.eligible ? 'YES' : 'NO'}
                                        </span>
                                    </p>
                                    {auditDetail.issues?.length > 0 && (
                                        <>
                                            <h4 style={{ marginTop: 16 }}>Issues</h4>
                                            <ul>{auditDetail.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
                                        </>
                                    )}
                                    {auditDetail.missing_courses?.length > 0 && (
                                        <>
                                            <h4 style={{ marginTop: 12 }}>Missing courses</h4>
                                            <ul>
                                                {auditDetail.missing_courses.map(c => (
                                                    <li key={c.course_id}>{c.course_code} — {c.course_name} (Sem {c.semester_number})</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                    {auditDetail.outstanding_challans?.length > 0 && (
                                        <>
                                            <h4 style={{ marginTop: 12 }}>Outstanding challans</h4>
                                            <ul>
                                                {auditDetail.outstanding_challans.map(c => (
                                                    <li key={c.challan_id}>{c.challan_number} — {c.semester__semester_name} ({c.status})</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setAuditDetail(null)}>Close</button>
                            {auditDetail?.eligible && (
                                <button className="btn-primary" onClick={handleConfirmGraduation} disabled={submitting}>
                                    {submitting ? 'Confirming...' : 'Confirm Graduation'}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )} />

            <ModalPortal isOpen={!!transcript} render={() => (
                <div className="modal-overlay" onClick={() => setTranscript(null)}>
                    <div className="glass-modal transcript-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 800, maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="modal-header">
                            <h3>
                                {transcript?.document_type === 'official_transcript' ? 'Official Transcript' : 'Unofficial Transcript'}
                            </h3>
                            <button className="close-btn" onClick={() => setTranscript(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body" id="transcript-print-area">
                            {transcript && (
                                <>
                                    <div style={{ textAlign: 'center', marginBottom: 20 }}>
                                        <h2 style={{ margin: 0 }}>Campus 360</h2>
                                        <p style={{ color: 'var(--text-secondary)', margin: '4px 0' }}>Academic Transcript</p>
                                    </div>
                                    <div style={{ display: 'grid', gap: 6, marginBottom: 20 }}>
                                        <p><strong>Name:</strong> {transcript.student.name}</p>
                                        <p><strong>Registration No:</strong> {transcript.student.registration_number}</p>
                                        <p><strong>Program:</strong> {transcript.student.program_name}</p>
                                        <p><strong>Batch:</strong> {transcript.student.batch_year}</p>
                                        <p><strong>CGPA:</strong> {transcript.student.cgpa}</p>
                                        {transcript.student.graduation_date && (
                                            <p><strong>Graduation Date:</strong> {transcript.student.graduation_date}</p>
                                        )}
                                    </div>
                                    {transcript.semesters?.map(sem => (
                                        <div key={sem.semester_id} style={{ marginBottom: 16 }}>
                                            <h4>{sem.semester_name}{sem.sgpa ? ` — SGPA: ${sem.sgpa}` : ''}</h4>
                                            <table className="data-table">
                                                <thead>
                                                    <tr><th>Code</th><th>Course</th><th>CH</th><th>Grade</th><th>Status</th></tr>
                                                </thead>
                                                <tbody>
                                                    {sem.courses.map((c, i) => (
                                                        <tr key={i}>
                                                            <td>{c.course_code}</td>
                                                            <td>{c.course_name}</td>
                                                            <td>{c.credit_hours}</td>
                                                            <td>{c.grade_letter}</td>
                                                            <td>{c.status?.toUpperCase()}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ))}
                                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 16 }}>
                                        Issued: {transcript.issued_at} · {transcript.document_type.replace('_', ' ')}
                                    </p>
                                </>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setTranscript(null)}>Close</button>
                            <button className="btn-primary" onClick={() => window.print()}>Print</button>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export default GraduationAuditPage;
