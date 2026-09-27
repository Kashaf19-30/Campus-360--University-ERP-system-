import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { PageHeader, useToast, LoadingSpinner, getStatusBadgeClass, useTableFilter, TableSearchBar, TablePagination, EmptyRow } from '../../shared/helpers';
import { listRepeatRequests, reviewRepeatRequest } from '../../../services/enrollmentsService';

const RepeatRequestsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('pending');
    const [remarks, setRemarks] = useState({});
    const [submitting, setSubmitting] = useState(null);

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const qs = filter ? `?status=${filter}` : '';
            const data = await listRepeatRequests(token, qs);
            setItems(Array.isArray(data) ? data : []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [token, filter]);

    useEffect(() => { load(); }, [load]);

    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(
        items, ['student_name', 'course_code', 'course_name', 'registration_number']
    );

    const handleReview = async (requestId, action) => {
        setSubmitting(requestId);
        try {
            const res = await reviewRepeatRequest(requestId, action, token, remarks[requestId] || '');
            showToast(res.message || `Request ${action}d`);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Review failed');
        } finally {
            setSubmitting(null);
        }
    };

    if (loading) return <LoadingSpinner message="Loading repeat requests..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ENROLLMENTS" title="Repeat Course Requests" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                Students can only submit repeat requests that fit within the semester credit cap.
                Enrolled CH is shown per row for reference.
            </p>
            <div style={{ marginBottom: 16 }}>
                <select className="field-input field-select" value={filter} onChange={e => setFilter(e.target.value)}>
                    <option value="pending">Pending</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                    <option value="">All</option>
                </select>
            </div>
            <div className="form-card">
                <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search student, course..." />
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th>
                                <th>Student</th>
                                <th>Course</th>
                                <th>Req CH</th>
                                <th>Enrolled CH</th>
                                <th>Cap / After</th>
                                <th>Semester</th>
                                <th>Status</th>
                                <th>Requested</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={10} title="No requests found" />
                            ) : paginated.map((row, i) => (
                                <tr key={row.request_id}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td>{row.registration_number}<br /><small>{row.student_name}</small></td>
                                    <td>{row.course_code}<br /><small>{row.course_name}</small></td>
                                    <td>{row.credit_hours}</td>
                                    <td>{row.enrolled_credit_hours ?? '—'}</td>
                                    <td>
                                        {row.max_semester_credit_hours ?? '—'} max
                                        <br />
                                        <small style={{ color: row.would_exceed_credit_cap ? '#ef4444' : 'var(--text-secondary)' }}>
                                            → {row.credit_hours_after_approval ?? '—'} CH after
                                        </small>
                                    </td>
                                    <td>{row.semester_name}</td>
                                    <td><span className={getStatusBadgeClass(row.status)}>{row.status?.toUpperCase()}</span></td>
                                    <td>{row.requested_at ? new Date(row.requested_at).toLocaleDateString() : '—'}</td>
                                    <td>
                                        {row.status === 'pending' ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 200 }}>
                                                <input
                                                    className="field-input"
                                                    placeholder="Optional remarks"
                                                    value={remarks[row.request_id] || ''}
                                                    onChange={e => setRemarks(p => ({ ...p, [row.request_id]: e.target.value }))}
                                                />
                                                <div style={{ display: 'flex', gap: 8 }}>
                                                    <button type="button" className="btn-save small"
                                                        disabled={submitting === row.request_id || row.would_exceed_credit_cap}
                                                        title={row.would_exceed_credit_cap ? 'Would exceed semester credit cap' : ''}
                                                        onClick={() => handleReview(row.request_id, 'approve')}>Approve</button>
                                                    <button type="button" className="btn-secondary small" disabled={submitting === row.request_id}
                                                        onClick={() => handleReview(row.request_id, 'reject')}>Reject</button>
                                                </div>
                                            </div>
                                        ) : row.admin_remarks || '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
        </div>
    );
};

export default RepeatRequestsPage;
