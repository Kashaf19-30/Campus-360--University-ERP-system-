import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listEnrollments } from '../../../services/enrollmentsService';
import { listDepartments, listPrograms, listProgramCourses } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, getStatusBadgeClass } from '../../shared/helpers';
import { FileTextIcon } from '../../Icons';

const CURRICULUM_SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8];

const EnrollmentsListingPage = () => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [stats, setStats] = useState({});
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [courses, setCourses] = useState([]);
    const [selectedDept, setSelectedDept] = useState('');
    const [selectedProgram, setSelectedProgram] = useState('');
    const [selectedCurriculumSem, setSelectedCurriculumSem] = useState('1');
    const [selectedCourse, setSelectedCourse] = useState('');
    const [loading, setLoading] = useState(true);

    const buildParams = () => {
        const p = new URLSearchParams();
        if (selectedDept) p.set('department', selectedDept);
        if (selectedProgram) p.set('program', selectedProgram);
        if (selectedCurriculumSem) p.set('curriculum_semester', selectedCurriculumSem);
        if (selectedCourse) p.set('course', selectedCourse);
        const qs = p.toString();
        return qs ? `?${qs}` : '';
    };

    const load = async () => {
        setLoading(true);
        try {
            const data = await listEnrollments(token, buildParams());
            setItems(Array.isArray(data.enrollments) ? data.enrollments : normalizeList(data));
            setStats(data.stats || {});
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

    useEffect(() => {
        if (!token || !selectedProgram) { setCourses([]); return; }
        listProgramCourses(selectedProgram, token, selectedCurriculumSem)
            .then(d => setCourses(normalizeList(d)))
            .catch(console.error);
    }, [token, selectedProgram, selectedCurriculumSem]);

    useEffect(() => {
        if (token) load();
    }, [token, selectedDept, selectedProgram, selectedCurriculumSem, selectedCourse]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } =
        useTableFilter(items, ['registration_number', 'student_name', 'course_code', 'program_name']);

    if (loading) return <LoadingSpinner message="Loading enrollments..." />;

    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > ENROLLMENTS" title="Enrollments Management" />

            <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <select className="field-input field-select" value={selectedDept} onChange={e => { setSelectedDept(e.target.value); setSelectedProgram(''); setSelectedCourse(''); setPage(1); }}>
                    <option value="">All Departments</option>
                    {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                </select>
                <select className="field-input field-select" value={selectedProgram} onChange={e => { setSelectedProgram(e.target.value); setSelectedCourse(''); setPage(1); }} disabled={!selectedDept}>
                    <option value="">All Programs</option>
                    {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                </select>
                <select className="field-input field-select" value={selectedCurriculumSem}
                    onChange={e => { setSelectedCurriculumSem(e.target.value); setSelectedCourse(''); setPage(1); }}>
                    {CURRICULUM_SEMESTERS.map(n => <option key={n} value={n}>Semester {n}</option>)}
                </select>
                <select className="field-input field-select" value={selectedCourse} onChange={e => { setSelectedCourse(e.target.value); setPage(1); }} disabled={!selectedProgram}>
                    <option value="">All Courses</option>
                    {courses.map(c => <option key={c.course_id} value={c.course_id}>{c.course_code} — {c.course_name}</option>)}
                </select>
            </div>

            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <div className="stat-pill" style={{ padding: '10px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    Total Registrations: <strong>{stats.total_registrations ?? items.length}</strong>
                </div>
                <div className="stat-pill" style={{ padding: '10px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    Unique Students: <strong>{stats.unique_students ?? '—'}</strong>
                </div>
                <div className="stat-pill" style={{ padding: '10px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    Courses: <strong>{stats.courses_count ?? '—'}</strong>
                </div>
            </div>

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search enrollments..." className="search-input" value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr><th>Sr#</th><th>Student</th><th>Reg No</th><th>Program</th><th>Course</th><th>Teacher</th><th>Term</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={8} icon={<FileTextIcon />} title="No enrollments found" subtitle="Try Semester 1 with no course filter, or assign courses in Course Assignments." />
                            ) : paginated.map((item, i) => (
                                <tr key={item.registration_id ?? `${item.registration_number}-${item.course_code}-${i}`}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td>{item.student_name || '—'}</td>
                                    <td>{item.registration_number || '—'}</td>
                                    <td>{item.program_name || '—'}</td>
                                    <td>{item.course_code === '—' ? item.course_name : `${item.course_code} — ${item.course_name}`}</td>
                                    <td>{item.faculty_name || '—'}</td>
                                    <td>{item.semester_name || '—'}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'REGISTERED'}</span></td>
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

export default EnrollmentsListingPage;
