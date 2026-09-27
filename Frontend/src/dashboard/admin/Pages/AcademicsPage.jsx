import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listDepartments, listPrograms, createDepartment, updateDepartment, deleteDepartment,
    createProgram, updateProgram, deleteProgram,
    listProgramCourses, addProgramCourse, removeProgramCourse,
} from '../../../services/academicsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { PlusIcon, BookIcon, XIcon, TrashIcon } from '../../Icons';

const AcademicsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [activeTab, setActiveTab] = useState('departments');
    const [loading, setLoading] = useState(true);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [programCourses, setProgramCourses] = useState([]);
    const [selectedProgram, setSelectedProgram] = useState('');
    const [selectedSemester, setSelectedSemester] = useState('1');
    const [showModal, setShowModal] = useState(false);
    const [editItem, setEditItem] = useState(null);
    const [formData, setFormData] = useState({});
    const [submitting, setSubmitting] = useState(false);

    const parseIntField = (val, fallback = 0) => {
        const n = parseInt(val, 10);
        return Number.isFinite(n) ? n : fallback;
    };

    const apiError = (e) => {
        const d = e.response?.data;
        if (!d) return 'Request failed';
        if (typeof d.error === 'string') return d.error;
        const first = Object.values(d)[0];
        return Array.isArray(first) ? first[0] : String(first);
    };

    const selectedProgramObj = programs.find(p => String(p.program_id) === String(selectedProgram));

    const loadBase = async () => {
        if (!token) return;
        setLoading(true);
        const [deptResult, progResult] = await Promise.allSettled([
            listDepartments(token),
            listPrograms(token),
        ]);
        if (deptResult.status === 'fulfilled') {
            setDepartments(normalizeList(deptResult.value));
        } else {
            console.error(deptResult.reason);
            showToast(apiError(deptResult.reason), 'error');
        }
        if (progResult.status === 'fulfilled') {
            setPrograms(normalizeList(progResult.value));
        } else {
            console.error(progResult.reason);
            showToast(apiError(progResult.reason), 'error');
        }
        setLoading(false);
    };

    useEffect(() => { loadBase(); }, [token]);

    const loadProgramCourses = async () => {
        if (!token || !selectedProgram) { setProgramCourses([]); return; }
        try {
            const d = await listProgramCourses(selectedProgram, token, selectedSemester);
            setProgramCourses(normalizeList(d));
        } catch (e) { console.error(e); }
    };

    useEffect(() => { loadProgramCourses(); }, [token, selectedProgram, selectedSemester]);

    const getCurrentData = () => {
        if (activeTab === 'departments') return departments;
        if (activeTab === 'programs') return programs;
        if (activeTab === 'program-courses') return programCourses;
        return [];
    };

    const searchFields = {
        departments: ['department_name', 'department_code'],
        programs: ['program_name', 'program_code', 'degree_level'],
        'program-courses': ['course_code', 'course_name'],
    };

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } =
        useTableFilter(getCurrentData(), searchFields[activeTab] || []);

    const openCreate = () => {
        setEditItem(null);
        if (activeTab === 'departments') {
            setFormData({ department_name: '', department_code: '' });
        } else if (activeTab === 'programs') {
            setFormData({
                program_name: '', program_code: '', department: '', degree_level: 'BS',
                duration_years: 4, total_semesters: 8, total_credit_hours: 130, fee_per_semester: 75000,
            });
        } else {
            setFormData({
                course_code: '', course_name: '', course_type: 'core',
                credit_hours: 3, theory_credit_hours: 3, lab_credit_hours: 0,
                prerequisite_codes: '',
            });
        }
        setShowModal(true);
    };

    const openEdit = (item) => {
        setEditItem(item);
        if (activeTab === 'departments') {
            setFormData({ department_name: item.department_name, department_code: item.department_code });
        } else if (activeTab === 'programs') {
            setFormData({
                program_name: item.program_name, program_code: item.program_code,
                department: item.department, degree_level: item.degree_level || 'BS',
                duration_years: item.duration_years, total_semesters: item.total_semesters,
                total_credit_hours: item.total_credit_hours, fee_per_semester: item.fee_per_semester,
            });
        }
        setShowModal(true);
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            if (activeTab === 'departments') {
                if (editItem) await updateDepartment(editItem.department_id, formData, token);
                else await createDepartment(formData, token);
            } else if (activeTab === 'programs') {
                const payload = { ...formData, program_type: 'morning' };
                if (editItem) await updateProgram(editItem.program_id, payload, token);
                else await createProgram(payload, token);
            } else {
                if (!selectedProgram) {
                    alert('Select a program from the filter above first.');
                    return;
                }
                const prog = programs.find(p => String(p.program_id) === String(selectedProgram));
                const payload = {
                    program: parseIntField(selectedProgram),
                    semester_number: parseIntField(selectedSemester, 1),
                    department: prog?.department ?? prog?.department_id,
                    course_code: (formData.course_code || '').trim(),
                    course_name: (formData.course_name || '').trim(),
                    course_type: formData.course_type || 'core',
                    credit_hours: parseIntField(formData.credit_hours, 3),
                    theory_credit_hours: parseIntField(formData.theory_credit_hours, 0),
                    lab_credit_hours: parseIntField(formData.lab_credit_hours, 0),
                    prerequisite_codes: (formData.prerequisite_codes || '')
                        .split(',').map(s => s.trim()).filter(Boolean),
                };
                await addProgramCourse(payload, token);
            }
            showToast(editItem ? 'Updated successfully' : 'Created successfully');
            setShowModal(false);
            loadBase();
            if (activeTab === 'program-courses') loadProgramCourses();
        } catch (e) {
            alert(apiError(e));
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (item) => {
        const label = activeTab === 'departments' ? item.department_name : item.program_name;
        if (!confirm(`Delete ${label}?`)) return;
        try {
            if (activeTab === 'departments') await deleteDepartment(item.department_id, token);
            else if (activeTab === 'programs') await deleteProgram(item.program_id, token);
            showToast('Deleted successfully');
            loadBase();
        } catch (e) {
            alert(apiError(e));
        }
    };

    const openCreateProgramCourse = () => {
        if (!selectedProgram) {
            alert('Select a program from the filter above first.');
            return;
        }
        openCreate();
    };

    const renderRow = (item, index) => {
        const sr = (page - 1) * pageSize + index + 1;
        if (activeTab === 'departments') {
            return (
                <tr key={item.department_id}>
                    <td>{sr}</td><td>{item.department_code}</td><td>{item.department_name}</td>
                    <td>
                        <button className="action-btn" onClick={() => openEdit(item)}>Edit</button>
                        <button className="action-btn danger" onClick={() => handleDelete(item)}>Delete</button>
                    </td>
                </tr>
            );
        }
        if (activeTab === 'programs') {
            return (
                <tr key={item.program_id}>
                    <td>{sr}</td><td>{item.program_code}</td><td>{item.program_name}</td>
                    <td>{item.duration_years} yrs</td><td>{item.total_semesters}</td>
                    <td>{item.total_credit_hours}</td><td>{item.fee_per_semester ?? '—'}</td><td>{item.degree_level}</td>
                    <td>
                        <button className="action-btn" onClick={() => openEdit(item)}>Edit</button>
                        <button className="action-btn danger" onClick={() => handleDelete(item)}>Delete</button>
                    </td>
                </tr>
            );
        }
        return (
            <tr key={item.program_course_id}>
                <td>{sr}</td><td>{item.course_code}</td><td>{item.course_name}</td>
                <td>{item.semester_number}</td><td>{item.course_type}</td>
                <td>{item.credit_hours}</td><td>{item.theory_credit_hours}</td><td>{item.lab_credit_hours}</td>
                <td>{(item.prerequisites || []).join(', ') || '—'}</td>
                <td>
                    <button className="action-btn danger" onClick={async () => {
                        if (confirm('Remove this course from program?')) {
                            await removeProgramCourse(item.program_course_id, token);
                            loadProgramCourses();
                            showToast('Removed');
                        }
                    }}><TrashIcon size={14} /></button>
                </td>
            </tr>
        );
    };

    const headers = {
        departments: ['Sr#', 'Code', 'Name', 'Actions'],
        programs: ['Sr#', 'Code', 'Name', 'Duration', 'Semesters', 'Credit Hrs', 'Fee/Sem', 'Degree', 'Actions'],
        'program-courses': ['Sr#', 'Code', 'Name', 'Semester', 'Type', 'Credits', 'Theory', 'Lab', 'Prerequisites', 'Action'],
    };

    if (loading) return <LoadingSpinner message="Loading academics..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ACADEMICS" title="Academics Management" />

            <div className="application-tabs">
                {['departments', 'programs', 'program-courses'].map(tab => (
                    <button key={tab} className={`app-tab ${activeTab === tab ? 'active' : ''}`}
                        onClick={() => { setActiveTab(tab); setPage(1); }}>
                        {tab === 'program-courses' ? 'Program Courses' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {activeTab === 'program-courses' && (
                <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    <div className="field-group" style={{ maxWidth: '320px', flex: 1 }}>
                        <label className="field-label">Program</label>
                        <select className="field-input field-select" value={selectedProgram}
                            onChange={e => { setSelectedProgram(e.target.value); setPage(1); }}>
                            <option value="">Choose program</option>
                            {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                        </select>
                    </div>
                    <div className="field-group" style={{ maxWidth: '180px' }}>
                        <label className="field-label">Semester</label>
                        <select className="field-input field-select" value={selectedSemester}
                            onChange={e => { setSelectedSemester(e.target.value); setPage(1); }}>
                            {[1,2,3,4,5,6,7,8].map(n => <option key={n} value={n}>Semester {n}</option>)}
                        </select>
                    </div>
                </div>
            )}

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search..." className="search-input" value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                    {(activeTab !== 'program-courses' || selectedProgram) && (
                        <button className="btn-add" onClick={activeTab === 'program-courses' ? openCreateProgramCourse : openCreate}>
                            <PlusIcon /> <span>Add New</span>
                        </button>
                    )}
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr>{headers[activeTab].map(h => <th key={h}>{h}</th>)}</tr></thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={headers[activeTab].length} icon={<BookIcon size={20} />} title="No records found" />
                            ) : paginated.map((item, i) => renderRow(item, i))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}
                        style={{ maxWidth: '520px', width: '95%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
                        <div className="modal-header">
                            <h3>{editItem ? 'Edit' : 'Add'} {activeTab === 'program-courses' ? 'Course' : activeTab.slice(0, -1)}</h3>
                            <button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button>
                        </div>
                        <div className="modal-body" style={{ overflowY: 'auto', flex: 1 }}>
                            {activeTab === 'departments' && (<>
                                <div className="field-group"><label className="field-label">Department Name</label>
                                    <input className="field-input" value={formData.department_name || ''} onChange={e => setFormData({ ...formData, department_name: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Department Code</label>
                                    <input className="field-input" value={formData.department_code || ''} onChange={e => setFormData({ ...formData, department_code: e.target.value })} /></div>
                            </>)}
                            {activeTab === 'programs' && (<>
                                <div className="field-group"><label className="field-label">Program Name</label>
                                    <input className="field-input" value={formData.program_name || ''} onChange={e => setFormData({ ...formData, program_name: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Program Code</label>
                                    <input className="field-input" value={formData.program_code || ''} onChange={e => setFormData({ ...formData, program_code: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Department</label>
                                    <select className="field-input field-select" value={formData.department || ''} onChange={e => setFormData({ ...formData, department: e.target.value })}>
                                        <option value="">Select department</option>
                                        {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                                    </select></div>
                                <div className="field-group"><label className="field-label">Degree Level</label>
                                    <input className="field-input" placeholder="BS" value={formData.degree_level || 'BS'} onChange={e => setFormData({ ...formData, degree_level: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Duration (Years)</label>
                                    <input type="number" className="field-input" value={formData.duration_years || 4} onChange={e => setFormData({ ...formData, duration_years: parseInt(e.target.value, 10) })} /></div>
                                <div className="field-group"><label className="field-label">Total Semesters</label>
                                    <input type="number" className="field-input" value={formData.total_semesters || 8} onChange={e => setFormData({ ...formData, total_semesters: parseInt(e.target.value, 10) })} /></div>
                                <div className="field-group"><label className="field-label">Total Credit Hours</label>
                                    <input type="number" className="field-input" value={formData.total_credit_hours || 130} onChange={e => setFormData({ ...formData, total_credit_hours: parseInt(e.target.value, 10) })} /></div>
                                <div className="field-group"><label className="field-label">Fee Per Semester</label>
                                    <input type="number" className="field-input" value={formData.fee_per_semester || ''} onChange={e => setFormData({ ...formData, fee_per_semester: e.target.value })} /></div>
                            </>)}
                            {activeTab === 'program-courses' && (<>
                                {selectedProgramObj && (
                                    <p style={{ margin: '0 0 12px', fontSize: '0.9rem', opacity: 0.85 }}>
                                        Adding to <strong>{selectedProgramObj.program_name}</strong>, Semester {selectedSemester}
                                    </p>
                                )}
                                <div className="field-group"><label className="field-label">Course Code</label>
                                    <input className="field-input" value={formData.course_code || ''} onChange={e => setFormData({ ...formData, course_code: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Course Name</label>
                                    <input className="field-input" value={formData.course_name || ''} onChange={e => setFormData({ ...formData, course_name: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Type</label>
                                    <select className="field-input field-select" value={formData.course_type || 'core'} onChange={e => setFormData({ ...formData, course_type: e.target.value })}>
                                        <option value="core">Core</option><option value="elective">Elective</option>
                                    </select></div>
                                <div className="field-group"><label className="field-label">Credit Hours</label>
                                    <input type="number" min="1" className="field-input" value={formData.credit_hours ?? 3}
                                        onChange={e => setFormData({ ...formData, credit_hours: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Theory Credit Hours</label>
                                    <input type="number" min="0" className="field-input" value={formData.theory_credit_hours ?? 3}
                                        onChange={e => setFormData({ ...formData, theory_credit_hours: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Lab Credit Hours</label>
                                    <input type="number" min="0" className="field-input" value={formData.lab_credit_hours ?? 0}
                                        onChange={e => setFormData({ ...formData, lab_credit_hours: e.target.value })} /></div>
                                <div className="field-group"><label className="field-label">Prerequisites (comma-separated codes)</label>
                                    <input className="field-input" placeholder="e.g. CS101, MTH101 or 90+ CH"
                                        value={formData.prerequisite_codes || ''}
                                        onChange={e => setFormData({ ...formData, prerequisite_codes: e.target.value })} /></div>
                            </>)}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn-primary" onClick={handleSubmit} disabled={submitting}>{submitting ? 'Saving...' : 'Save'}</button>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export default AcademicsPage;
