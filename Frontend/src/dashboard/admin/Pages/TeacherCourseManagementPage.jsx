import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { PageHeader, useToast, LoadingSpinner, useTableFilter, TableSearchBar } from '../../shared/helpers';
import { listDepartments, listPrograms } from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import {
    getFacultyWorkload, listFaculty, listUnassignedProgramCourses,
    createFacultyCourseAssignment, removeFacultyCourseAssignment,
} from '../../../services/facultyService';
import { TrashIcon } from '../../Icons';

const TeacherCourseManagementPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [workload, setWorkload] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [facultyList, setFacultyList] = useState([]);
    const [unassigned, setUnassigned] = useState([]);
    const [assignForm, setAssignForm] = useState({
        faculty_id: '', department_id: '', program_id: '', course_id: '',
    });

    const loadWorkload = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await getFacultyWorkload(token);
            setWorkload(res.workload || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { loadWorkload(); }, [loadWorkload]);

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
        listFaculty(token).then(d => setFacultyList(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !assignForm.department_id) { setPrograms([]); return; }
        listPrograms(token, assignForm.department_id).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, assignForm.department_id]);

    useEffect(() => {
        if (!token || !assignForm.program_id) { setUnassigned([]); return; }
        listUnassignedProgramCourses(assignForm.program_id, token)
            .then(setUnassigned).catch(console.error);
    }, [token, assignForm.program_id]);

    const handleAssign = async (e) => {
        e.preventDefault();
        if (!assignForm.faculty_id || !assignForm.program_id || !assignForm.course_id) {
            alert('Select teacher, program, and course.');
            return;
        }
        try {
            await createFacultyCourseAssignment({
                faculty_id: parseInt(assignForm.faculty_id, 10),
                program_id: parseInt(assignForm.program_id, 10),
                course_id: parseInt(assignForm.course_id, 10),
            }, token);
            showToast('Course assigned to teacher.');
            setAssignForm(prev => ({ ...prev, course_id: '' }));
            loadWorkload();
            listUnassignedProgramCourses(assignForm.program_id, token).then(setUnassigned).catch(console.error);
        } catch (err) {
            alert(err.response?.data?.error || 'Assignment failed');
        }
    };

    const handleRemove = async (assignmentId) => {
        if (!window.confirm('Remove this course assignment?')) return;
        try {
            await removeFacultyCourseAssignment(assignmentId, token);
            showToast('Assignment removed.');
            loadWorkload();
            if (assignForm.program_id) {
                listUnassignedProgramCourses(assignForm.program_id, token).then(setUnassigned).catch(console.error);
            }
        } catch (err) {
            alert(err.response?.data?.error || 'Remove failed');
        }
    };

    const { search, setSearch, paginated, filtered } = useTableFilter(workload, ['employee_code', 'faculty_name', 'department_name', 'home_program']);

    if (loading) return <LoadingSpinner message="Loading teacher assignments..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > TEACHERS" title="Teacher Course Management" />

            <div className="form-card" style={{ marginBottom: '24px' }}>
                <h3 className="section-title">Assign Course to Teacher</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                    Each course is assigned per program. Teaching the same course in CS and AI counts as 2 lectures.
                </p>
                <form onSubmit={handleAssign} className="form-grid-2">
                    <div className="field-group">
                        <label className="field-label">Teacher</label>
                        <select className="field-input field-select" value={assignForm.faculty_id}
                            onChange={e => setAssignForm(p => ({ ...p, faculty_id: e.target.value }))}>
                            <option value="">Select teacher</option>
                            {facultyList.map(f => (
                                <option key={f.faculty_id} value={f.faculty_id}>
                                    {f.employee_code} — {f.username}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Department</label>
                        <select className="field-input field-select" value={assignForm.department_id}
                            onChange={e => setAssignForm({ faculty_id: assignForm.faculty_id, department_id: e.target.value, program_id: '', course_id: '' })}>
                            <option value="">Select department</option>
                            {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Program</label>
                        <select className="field-input field-select" value={assignForm.program_id} disabled={!assignForm.department_id}
                            onChange={e => setAssignForm(p => ({ ...p, program_id: e.target.value, course_id: '' }))}>
                            <option value="">Select program</option>
                            {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Unassigned Course</label>
                        <select className="field-input field-select" value={assignForm.course_id} disabled={!assignForm.program_id}
                            onChange={e => setAssignForm(p => ({ ...p, course_id: e.target.value }))}>
                            <option value="">Select course</option>
                            {unassigned.map(c => (
                                <option key={c.course_id} value={c.course_id}>
                                    {c.course_code} — {c.course_name} (Sem {c.semester_number})
                                </option>
                            ))}
                        </select>
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                        <button type="submit" className="btn-save">Assign Course</button>
                    </div>
                </form>
            </div>

            <div className="table-card">
                <h3 className="section-title" style={{ padding: '16px 16px 0' }}>Teacher Workload</h3>
                <div style={{ padding: '0 16px 16px' }}>
                    <TableSearchBar search={search} onSearchChange={setSearch} placeholder="Search teacher, department, program..." />
                </div>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Teacher</th>
                            <th>Dept</th>
                            <th>Home Program</th>
                            <th>Lectures</th>
                            <th>Assigned Courses</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.length === 0 ? (
                            <tr><td colSpan={5} style={{ textAlign: 'center', padding: '24px' }}>No teachers found.</td></tr>
                        ) : filtered.map(row => (
                            <tr key={row.faculty_id}>
                                <td>{row.employee_code}<br /><small>{row.faculty_name}</small></td>
                                <td>{row.department_name}</td>
                                <td>{row.home_program || '—'}</td>
                                <td><strong>{row.lecture_count}</strong></td>
                                <td>
                                    {row.courses.length === 0 ? (
                                        <span style={{ color: 'var(--text-secondary)' }}>No courses assigned</span>
                                    ) : (
                                        <div className="course-assignment-list">
                                            {row.courses.map(c => (
                                                <div key={c.assignment_id} className="course-assignment-chip">
                                                    <span className="course-assignment-label">
                                                        <strong>{c.course_code}</strong>
                                                        <span className="course-assignment-meta">({c.course_name})</span>
                                                        {c.semester_number != null && (
                                                            <span className="course-assignment-semester">Sem {c.semester_number}</span>
                                                        )}
                                                        <span className="course-assignment-program">{c.program_code}</span>
                                                    </span>
                                                    <button
                                                        type="button"
                                                        className="action-btn danger course-assignment-remove"
                                                        title="Remove assignment"
                                                        onClick={() => handleRemove(c.assignment_id)}
                                                    >
                                                        <TrashIcon size={14} />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TeacherCourseManagementPage;
