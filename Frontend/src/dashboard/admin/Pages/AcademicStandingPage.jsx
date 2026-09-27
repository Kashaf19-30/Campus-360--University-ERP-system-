import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listAcademicStanding, manualPromoteStudent, updateStudentStatus,
    repeatSemester, confirmDismissal, clearDismissalReview,
} from '../../../services/studentsService';
import { listSemesters, getAcademicPolicy } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import {
    PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow,
    useToast, getStatusBadgeClass,
} from '../../shared/helpers';
import { UserIcon } from '../../Icons';

const STANDING_OPTIONS = [
    { value: '', label: 'All standings' },
    { value: 'promoted', label: 'Promoted' },
    { value: 'probation', label: 'Probation' },
    { value: 'held_back', label: 'Held back (failed)' },
    { value: 'dismissal_review', label: 'Dismissal review' },
    { value: 'graduated', label: 'Graduated' },
];

const standingBadge = (standing) => {
    const map = {
        promoted: 'active',
        probation: 'pending',
        held_back: 'inactive',
        dismissal_review: 'rejected',
        graduated: 'approved',
    };
    return map[standing] || 'pending';
};

const AcademicStandingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [semesters, setSemesters] = useState([]);
    const [policy, setPolicy] = useState(null);
    const [selectedSemester, setSelectedSemester] = useState('');
    const [standingFilter, setStandingFilter] = useState('held_back');
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const buildParams = () => {
        const p = new URLSearchParams();
        if (selectedSemester) p.set('semester_id', selectedSemester);
        if (standingFilter) p.set('standing', standingFilter);
        const qs = p.toString();
        return qs ? `?${qs}` : '';
    };

    const load = async () => {
        setLoading(true);
        try {
            const data = await listAcademicStanding(token, buildParams());
            setItems(Array.isArray(data.students) ? data.students : normalizeList(data));
        } catch (e) {
            console.error(e);
            showToast('Failed to load academic standing', 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!token) return;
        Promise.all([
            listSemesters(token),
            getAcademicPolicy(token),
        ]).then(([semData, pol]) => {
            const sems = normalizeList(semData);
            setSemesters(sems);
            setPolicy(pol);
            const current = sems.find(s => s.is_current);
            if (current) setSelectedSemester(String(current.semester_id));
        }).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (token) load();
    }, [token, selectedSemester, standingFilter]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } =
        useTableFilter(items, ['registration_number', 'student_name', 'program_name']);

    const runAction = async (fn, successMsg) => {
        setSubmitting(true);
        try {
            const result = await fn();
            showToast(result?.message || successMsg);
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Action failed');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading academic standing..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ACADEMIC STANDING" title="Academic Standing" />

            {policy && (
                <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
                    <div className="stat-pill" style={{ padding: '8px 14px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        Probation threshold: SGPA ≥ <strong>{policy.min_sgpa_probation}</strong>
                    </div>
                    <div className="stat-pill" style={{ padding: '8px 14px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        Graduation CGPA: ≥ <strong>{policy.min_cgpa_graduation}</strong>
                    </div>
                    <div className="stat-pill" style={{ padding: '8px 14px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        Dismissal after: <strong>{policy.max_consecutive_probation}</strong> consecutive probations
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <select className="field-input field-select" value={selectedSemester}
                    onChange={e => { setSelectedSemester(e.target.value); setPage(1); }}>
                    <option value="">All terms</option>
                    {semesters.map(s => (
                        <option key={s.semester_id} value={s.semester_id}>{s.semester_name}</option>
                    ))}
                </select>
                <select className="field-input field-select" value={standingFilter}
                    onChange={e => { setStandingFilter(e.target.value); setPage(1); }}>
                    {STANDING_OPTIONS.map(o => (
                        <option key={o.value || 'all'} value={o.value}>{o.label}</option>
                    ))}
                </select>
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
                            <tr>
                                <th>Sr#</th><th>Reg No</th><th>Student</th><th>Program</th>
                                <th>Sem</th><th>Term</th><th>SGPA</th><th>CGPA</th>
                                <th>Prob.#</th><th>Result</th><th>Standing</th><th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={12} icon={<UserIcon size={20} />}
                                    title="No records found"
                                    subtitle="Publish semester results first, then filter by standing." />
                            ) : paginated.map((item, i) => (
                                <tr key={`${item.student_id}-${item.semester_id || i}`}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td><span className="app-number">{item.registration_number}</span></td>
                                    <td>{item.student_name}</td>
                                    <td>{item.program_name}</td>
                                    <td>{item.current_semester}</td>
                                    <td>{item.semester_name}</td>
                                    <td>{item.sgpa}</td>
                                    <td>{item.cgpa}</td>
                                    <td>{item.consecutive_probation_count ?? 0}</td>
                                    <td><span className={getStatusBadgeClass(item.result_status)}>{item.result_status?.toUpperCase()}</span></td>
                                    <td><span className={getStatusBadgeClass(standingBadge(item.standing))}>{item.standing?.replace(/_/g, ' ').toUpperCase()}</span></td>
                                    <td>
                                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                            {item.standing === 'held_back' && (
                                                <>
                                                    <button className="action-btn view-btn" disabled={submitting}
                                                        onClick={() => runAction(
                                                            () => manualPromoteStudent(item.student_id, { semester_id: item.semester_id }, token),
                                                            'Student promoted',
                                                        )}>Promote</button>
                                                    <button className="action-btn" disabled={submitting}
                                                        onClick={() => runAction(
                                                            () => repeatSemester(item.student_id, token),
                                                            'Re-enrolled for repeat semester',
                                                        )}>Repeat</button>
                                                    <button className="action-btn danger" disabled={submitting}
                                                        onClick={() => {
                                                            if (!confirm(`Mark ${item.registration_number} as dropped?`)) return;
                                                            runAction(
                                                                () => updateStudentStatus(item.student_id, { status: 'dropped' }, token),
                                                                'Student marked as dropped',
                                                            );
                                                        }}>Drop</button>
                                                </>
                                            )}
                                            {item.standing === 'dismissal_review' && (
                                                <>
                                                    <button className="action-btn danger" disabled={submitting}
                                                        onClick={() => {
                                                            if (!confirm(`Confirm dismissal (expel) for ${item.registration_number}?`)) return;
                                                            runAction(() => confirmDismissal(item.student_id, token), 'Student dismissed');
                                                        }}>Dismiss</button>
                                                    <button className="action-btn view-btn" disabled={submitting}
                                                        onClick={() => runAction(
                                                            () => clearDismissalReview(item.student_id, token),
                                                            'Review cleared — student continues',
                                                        )}>Allow continue</button>
                                                </>
                                            )}
                                        </div>
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
        </div>
    );
};

export default AcademicStandingPage;
