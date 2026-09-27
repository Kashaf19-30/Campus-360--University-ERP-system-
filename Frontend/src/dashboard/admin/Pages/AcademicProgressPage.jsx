import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    getSemesterProgress,
    getRepeatProgress,
    promoteSemesterBatch,
} from '../../../services/enrollmentsService';
import { PageHeader, LoadingSpinner, useToast, getStatusBadgeClass } from '../../shared/helpers';
import { ClipboardIcon, FileIcon } from '../../Icons';

const STATUS_CLASS = {
    ready_for_promotion: 'active',
    in_progress: 'pending',
    not_eligible: 'inactive',
    no_students: 'inactive',
};

const AcademicProgressPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [curriculumSem, setCurriculumSem] = useState(1);
    const [semesterProgress, setSemesterProgress] = useState(null);
    const [repeatProgress, setRepeatProgress] = useState(null);
    const [loading, setLoading] = useState(true);
    const [promoting, setPromoting] = useState(false);

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [sem, rep] = await Promise.all([
                getSemesterProgress(token, curriculumSem),
                getRepeatProgress(token, curriculumSem),
            ]);
            setSemesterProgress(sem);
            setRepeatProgress(rep);
        } catch (e) {
            console.error(e);
            showToast('Failed to load academic progress', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, curriculumSem]);

    useEffect(() => {
        load();
    }, [load]);

    const handlePromote = async () => {
        if (!semesterProgress || semesterProgress.status !== 'ready_for_promotion') return;
        if (!confirm(
            `Promote all ${semesterProgress.student_count} student(s) in Semester ${curriculumSem}? `
            + 'This will publish results, calculate GPA, and advance the entire batch.'
        )) return;

        setPromoting(true);
        try {
            const res = await promoteSemesterBatch(token, curriculumSem);
            if (res.success) {
                const promoted = res.promoted?.length || 0;
                const blocked = res.registration_blocked?.length || 0;
                const graduated = res.graduated?.length || 0;
                const heldBack = res.held_back?.length || 0;
                const pending = res.promotion_pending?.length || 0;
                const targetSem = curriculumSem + 1;
                if (pending > 0 && promoted === 0 && graduated === 0) {
                    showToast(
                        `Promotion initiated — ${pending} student(s) pending Semester ${targetSem} fee. `
                        + 'Courses will enroll automatically when finance marks fees paid.',
                        'success',
                    );
                } else if (promoted === 0 && graduated === 0 && blocked > 0) {
                    showToast(
                        `No students promoted — ${blocked} blocked by unpaid Semester ${targetSem} fee`,
                        'error',
                    );
                } else if (promoted === 0 && graduated === 0 && heldBack > 0) {
                    const reason = res.held_back[0]?.reason || 'See held-back list';
                    showToast(`No students promoted — ${heldBack} held back (${reason})`, 'error');
                } else {
                    showToast(
                        `Batch promoted — ${promoted} promoted, ${graduated} graduated, ${pending} pending fee`,
                        promoted > 0 || graduated > 0 ? 'success' : 'error',
                    );
                }
                load();
            } else {
                alert(res.error || 'Promotion failed');
            }
        } catch (e) {
            alert(e.response?.data?.error || 'Promotion failed');
        } finally {
            setPromoting(false);
        }
    };

    if (loading && !semesterProgress) {
        return <LoadingSpinner message="Loading academic progress..." />;
    }

    const sp = semesterProgress || {};
    const rp = repeatProgress || {};

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ACADEMIC PROGRESS" title="Academic Progress" />

            <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <label className="field-label" style={{ margin: 0 }}>Curriculum Semester</label>
                <select
                    className="field-input field-select"
                    style={{ maxWidth: 200 }}
                    value={curriculumSem}
                    onChange={e => setCurriculumSem(parseInt(e.target.value, 10))}
                >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map(n => (
                        <option key={n} value={n}>Semester {n}</option>
                    ))}
                </select>
            </div>

            {/* Section A — Semester Progress */}
            <div className="form-card" style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
                    <div>
                        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <ClipboardIcon size={20} /> Section A — Semester Progress
                        </h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: 4 }}>
                            Regular curriculum courses only. Promotion requires 100% assessment weightage per course and all marks submitted — not finals alone.
                        </p>
                    </div>
                    <span className={getStatusBadgeClass(STATUS_CLASS[sp.status] || 'pending')}>
                        {sp.status_label || '—'}
                    </span>
                </div>

                <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', marginBottom: 16 }}>
                    <div className="stat-card"><span>Students</span><strong>{sp.student_count ?? 0}</strong></div>
                    <div className="stat-card">
                        <span>Course Completion</span>
                        <strong>{sp.regular_courses_completed ?? 0} / {sp.regular_courses_total ?? 0}</strong>
                    </div>
                </div>

                {(sp.pending_courses || []).length > 0 && (
                    <div style={{ marginBottom: 16, padding: 12, background: '#fffbeb', borderRadius: 8, border: '1px solid #fcd34d' }}>
                        <strong>Pending Courses</strong>
                        <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                            {sp.pending_courses.map(c => (
                                <li key={c.offering_id}>
                                    {c.course_code} — {c.course_name} · Teacher: {c.teacher_name}
                                    {c.weight_complete === false && (
                                        <> · Weight: {c.weight_allocated ?? 0}% / 100%</>
                                    )}
                                    {c.pending_students > 0 && <> · {c.pending_students} student(s) awaiting grades</>}
                                    {c.promotion_block_reason && <> — {c.promotion_block_reason}</>}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Course</th>
                                <th>Teacher</th>
                                <th>Weight</th>
                                <th>Graded</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(sp.courses || []).length === 0 ? (
                                <tr><td colSpan={5} className="empty-row">No regular course registrations for this semester</td></tr>
                            ) : sp.courses.map(c => (
                                <tr key={c.offering_id}>
                                    <td><strong>{c.course_code}</strong> — {c.course_name}</td>
                                    <td>{c.teacher_name}</td>
                                    <td>{c.weight_complete ? '100%' : `${c.weight_allocated ?? 0}%`}</td>
                                    <td>{c.graded_students} / {c.total_students}</td>
                                    <td>
                                        <span className={getStatusBadgeClass(c.is_complete ? 'active' : (c.weight_complete === false ? 'inactive' : 'pending'))}>
                                            {c.is_complete ? 'COMPLETED' : (c.weight_complete === false ? 'WEIGHT INCOMPLETE' : 'PENDING')}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {sp.status === 'ready_for_promotion' && (
                    <div style={{ marginTop: 16 }}>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handlePromote}
                            disabled={promoting}
                        >
                            {promoting ? 'Promoting...' : `Promote Semester ${curriculumSem} Batch`}
                        </button>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 8 }}>
                            Promotes all {sp.student_count} students together. Financial clearance is handled separately — unpaid fees block course registration only.
                        </p>
                    </div>
                )}
            </div>

            {/* Section B — Repeat Course Progress */}
            <div className="form-card">
                <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <FileIcon size={20} /> Section B — Repeat Course Progress
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: 16 }}>
                    Active repeat/improvement courses for Semester {curriculumSem} students only (completed repeats are hidden). These never block semester promotion.
                </p>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Course</th>
                                <th>Teacher</th>
                                <th>Enrolled</th>
                                <th>Waiting</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(rp.items || []).length === 0 ? (
                                <tr><td colSpan={5} className="empty-row">No repeat course registrations</td></tr>
                            ) : rp.items.map(c => (
                                <tr key={c.offering_id}>
                                    <td><strong>{c.course_code}</strong> — {c.course_name}</td>
                                    <td>{c.teacher_name}</td>
                                    <td>{c.enrolled_students}</td>
                                    <td>{c.waiting_students}</td>
                                    <td>
                                        <span className={getStatusBadgeClass(c.is_complete ? 'active' : 'pending')}>
                                            {c.status_label}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AcademicProgressPage;
