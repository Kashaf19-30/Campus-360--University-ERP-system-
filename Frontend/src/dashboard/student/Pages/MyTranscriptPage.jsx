import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { myTranscript, myDegreeAudit } from '../../../services/studentsService';
import { PageHeader, LoadingSpinner, useToast, getStatusBadgeClass, formatCurriculumSemester } from '../../shared/helpers';
import { FileTextIcon } from '../../Icons';

const MyTranscriptPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [transcript, setTranscript] = useState(null);
    const [audit, setAudit] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        Promise.all([myTranscript(token), myDegreeAudit(token)])
            .then(([t, a]) => {
                setTranscript(t);
                setAudit(a);
            })
            .catch(() => showToast('Failed to load transcript', 'error'))
            .finally(() => setLoading(false));
    }, [token]);

    if (loading) return <LoadingSpinner message="Loading transcript..." />;
    if (!transcript) {
        return (
            <div className="page-container fade-in">
                {Toast}
                <PageHeader breadcrumb="DASHBOARD > TRANSCRIPT" title="My Transcript" />
                <div className="form-card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <FileTextIcon size={32} />
                    <p>Unable to load transcript. Please try again later.</p>
                </div>
            </div>
        );
    }

    const isOfficial = transcript.document_type === 'official_transcript';

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > TRANSCRIPT" title="My Transcript" />

            {audit && !audit.eligible && audit.status !== 'graduated' && (
                <div style={{ padding: '12px 16px', background: 'rgba(239,68,68,0.08)', borderRadius: 8, marginBottom: 16 }}>
                    <strong>Degree not yet complete.</strong>
                    {audit.issues?.length > 0 && (
                        <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                            {audit.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                        </ul>
                    )}
                </div>
            )}

            <div style={{ marginBottom: 12, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <span className={getStatusBadgeClass(isOfficial ? 'approved' : 'pending')}>
                    {isOfficial ? 'OFFICIAL TRANSCRIPT' : 'UNOFFICIAL TRANSCRIPT'}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>
                    Progress: {transcript.audit_summary?.degree_completion_percent}% · CGPA: {transcript.student.cgpa}
                </span>
                <button className="btn-primary" onClick={() => window.print()} style={{ marginLeft: 'auto' }}>
                    Print / Save PDF
                </button>
            </div>

            <div className="form-card" id="student-transcript-print">
                <div style={{ textAlign: 'center', marginBottom: 24, paddingTop: 8 }}>
                    <h2 style={{ margin: 0 }}>Campus 360</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Academic Transcript</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 24 }}>
                    <p><strong>Name:</strong> {transcript.student.name}</p>
                    <p><strong>Registration No:</strong> {transcript.student.registration_number}</p>
                    <p><strong>Program:</strong> {transcript.student.program_name}</p>
                    <p><strong>Batch:</strong> {transcript.student.batch_year}</p>
                    <p><strong>CGPA:</strong> {transcript.student.cgpa}</p>
                    <p><strong>Status:</strong> {transcript.student.status?.toUpperCase()}</p>
                    {transcript.student.graduation_date && (
                        <p><strong>Graduation Date:</strong> {transcript.student.graduation_date}</p>
                    )}
                </div>

                {transcript.semesters?.length === 0 ? (
                    <EmptyTranscript />
                ) : transcript.semesters.map(sem => (
                    <div key={sem.semester_id} style={{ marginBottom: 24 }}>
                        <h3 style={{ marginBottom: 8 }}>
                            {formatCurriculumSemester(sem)}
                            {sem.sgpa && <span style={{ fontWeight: 400, fontSize: '0.9rem', color: 'var(--text-secondary)' }}> · SGPA {sem.sgpa}</span>}
                        </h3>
                        <div className="data-table-wrapper">
                            <table className="data-table">
                                <thead>
                                    <tr><th>Code</th><th>Course</th><th>Credit Hrs</th><th>Grade</th><th>Points</th><th>Status</th></tr>
                                </thead>
                                <tbody>
                                    {sem.courses.map((c, i) => (
                                        <tr key={i}>
                                            <td>{c.course_code}</td>
                                            <td>{c.course_name}</td>
                                            <td>{c.credit_hours}</td>
                                            <td>{c.grade_letter}</td>
                                            <td>{c.grade_points}</td>
                                            <td>{c.status?.toUpperCase()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ))}

                <div style={{
                    marginTop: 24,
                    padding: '16px 20px',
                    background: 'var(--surface-alt, #f4f6f9)',
                    borderRadius: 8,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: 12,
                }}>
                    <strong>Cumulative CGPA (best attempt per course; fails count until cleared)</strong>
                    <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>{transcript.cumulative_cgpa ?? transcript.student.cgpa}</span>
                </div>

                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-light)', paddingTop: 16, marginTop: 24 }}>
                    Issued on {transcript.issued_at}. This is an {isOfficial ? 'official' : 'unofficial'} transcript generated by Campus 360 ERP.
                </p>
            </div>
        </div>
    );
};

const EmptyTranscript = () => (
    <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-secondary)' }}>
        <FileTextIcon size={32} />
        <p>No graded courses on record yet.</p>
    </div>
);

export default MyTranscriptPage;
