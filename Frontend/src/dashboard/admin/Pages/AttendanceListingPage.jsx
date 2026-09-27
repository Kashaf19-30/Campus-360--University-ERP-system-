import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listAttendance, listAttendanceSummaries } from '../../../services/attendanceService';
import { listDepartments, listPrograms, listSemesters, listProgramCourses } from '../../../services/academicsService';
import { BASE_URL, getAuthHeader } from '../../../services/api';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, formatDate, getStatusBadgeClass } from '../../shared/helpers';
import { ClipboardIcon } from '../../Icons';

const AttendanceListingPage = () => {
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState('records');
    const [records, setRecords] = useState([]);
    const [summaries, setSummaries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [semesters, setSemesters] = useState([]);
    const [courses, setCourses] = useState([]);
    const [filters, setFilters] = useState({
        department_id: '', program_id: '', semester_id: '', course_id: '',
    });

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
        listSemesters(token).then(d => setSemesters(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !filters.department_id) { setPrograms([]); return; }
        listPrograms(token, filters.department_id).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, filters.department_id]);

    useEffect(() => {
        if (!token || !filters.program_id) { setCourses([]); return; }
        listProgramCourses(filters.program_id, token)
            .then(d => setCourses(normalizeList(d))).catch(console.error);
    }, [token, filters.program_id]);

    const buildQuery = useCallback(() => {
        const params = new URLSearchParams();
        if (filters.department_id) params.set('department', filters.department_id);
        if (filters.program_id) params.set('program', filters.program_id);
        if (filters.semester_id) params.set('semester', filters.semester_id);
        if (filters.course_id) params.set('course', filters.course_id);
        return params.toString();
    }, [filters]);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const qs = buildQuery();
            const [r, s] = await Promise.all([
                listAttendance(token, qs),
                listAttendanceSummaries(token, qs),
            ]);
            setRecords(normalizeList(r));
            setSummaries(normalizeList(s));
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [token, buildQuery]);

    useEffect(() => { if (token) load(); }, [token, load]);

    const currentData = activeTab === 'records' ? records : summaries;
    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(
        currentData,
        ['student_reg', 'faculty_name', 'course_code', 'course_name', 'semester_name'],
    );

    const exportReport = () => {
        const qs = buildQuery();
        const url = `${BASE_URL}/attendance/summary/export/${qs ? '?' + qs : ''}`;
        fetch(url, getAuthHeader(token))
            .then(r => r.blob())
            .then(blob => {
                const blobUrl = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = 'attendance_report.csv';
                a.click();
            }).catch(() => alert('Export failed'));
    };

    const resetFilters = () => {
        setFilters({ department_id: '', program_id: '', semester_id: '', course_id: '' });
        setPage(1);
    };

    if (loading && records.length === 0 && summaries.length === 0) {
        return <LoadingSpinner message="Loading attendance..." />;
    }

    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > ATTENDANCE" title="Attendance Management" />
            <div className="application-tabs">
                <button className={`app-tab ${activeTab === 'records' ? 'active' : ''}`} onClick={() => { setActiveTab('records'); setPage(1); }}>Records</button>
                <button className={`app-tab ${activeTab === 'summary' ? 'active' : ''}`} onClick={() => { setActiveTab('summary'); setPage(1); }}>Summary Report</button>
            </div>
            <div className="form-card">
                <div className="form-grid-2" style={{ marginBottom: '16px' }}>
                    <div className="field-group">
                        <label className="field-label">Department</label>
                        <select className="field-input field-select" value={filters.department_id}
                            onChange={e => setFilters({ department_id: e.target.value, program_id: '', semester_id: '', course_id: '' })}>
                            <option value="">All departments</option>
                            {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Program</label>
                        <select className="field-input field-select" value={filters.program_id} disabled={!filters.department_id}
                            onChange={e => setFilters(p => ({ ...p, program_id: e.target.value, course_id: '' }))}>
                            <option value="">All programs</option>
                            {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Semester</label>
                        <select className="field-input field-select" value={filters.semester_id}
                            onChange={e => setFilters(p => ({ ...p, semester_id: e.target.value }))}>
                            <option value="">All semesters</option>
                            {semesters.map(s => <option key={s.semester_id} value={s.semester_id}>{s.semester_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Course</label>
                        <select className="field-input field-select" value={filters.course_id} disabled={!filters.program_id}
                            onChange={e => setFilters(p => ({ ...p, course_id: e.target.value }))}>
                            <option value="">All courses</option>
                            {courses.map(c => (
                                <option key={c.course_id} value={c.course_id}>
                                    {c.course_code} — {c.course_name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search..." className="search-input" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn-secondary" type="button" onClick={resetFilters}>Clear Filters</button>
                        {activeTab === 'summary' && (
                            <button className="btn-secondary" onClick={exportReport}>Export CSV</button>
                        )}
                    </div>
                </div>
                <div className="data-table-wrapper">
                    {activeTab === 'records' ? (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Student</th><th>Course</th><th>Teacher</th><th>Date</th><th>Status</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={6} icon={<ClipboardIcon size={20} />} title="No attendance records" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.attendance_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{item.student_reg || '—'}</td>
                                        <td>{item.course_code || '—'}</td>
                                        <td>{item.faculty_name || '—'}</td>
                                        <td>{formatDate(item.attendance_date || item.date)}</td>
                                        <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'PRESENT'}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Student</th><th>Course</th><th>Semester</th><th>Present</th><th>Absent</th><th>Percentage</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={7} icon={<ClipboardIcon size={20} />} title="No summary data" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.summary_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{item.student_reg || item.student?.registration_number || '—'}</td>
                                        <td>{item.course_code || '—'}</td>
                                        <td>{item.semester_name || '—'}</td>
                                        <td>{item.attended_lectures ?? '—'}</td>
                                        <td>{(item.total_lectures || 0) - (item.attended_lectures || 0)}</td>
                                        <td>{item.attendance_percentage != null ? `${Number(item.attendance_percentage).toFixed(1)}%` : '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
        </div>
    );
};

export default AttendanceListingPage;
