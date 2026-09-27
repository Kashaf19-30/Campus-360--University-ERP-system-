import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { getMyOfferings, getMyOfferingsForMarks, getOfferingStudents, submitFinalMarks } from '../../../services/offeringsService';
import {
    listExaminations, enterMarks, listMarks, getMarksLockStatus,
    createContinuousAssessment, requestOfferingMarksEdit, updateExamination,
} from '../../../services/examinationsService';
import { listAttendance, markAttendance, nextLectureNumber, teacherLeaves, reviewLeave } from '../../../services/attendanceService';
import { listNotifications, markNotificationRead, markAllNotificationsRead, listAnnouncements, createAnnouncement, getAnnouncementTargetOptions } from '../../../services/notificationsService';
import { normalizeList } from '../../../services/api';
import { listDepartments, listPrograms } from '../../../services/academicsService';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, formatDate, getStatusBadgeClass, TableSearchBar, formatOfferingLabel } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { PlusIcon, BookIcon, ClipboardIcon, FileIcon, BellIcon, XIcon } from '../../Icons';

const CATEGORY_CAPS = { quiz: 10, assignment: 10, presentation: 10 };
const FIXED_WEIGHTS = { mid_term: 30, final: 40 };
const CONTINUOUS_CATEGORIES = ['quiz', 'assignment', 'presentation'];
const CATEGORY_LABELS = {
    quiz: 'Quiz',
    assignment: 'Assignment',
    presentation: 'Presentation / Project',
    mid_term: 'Mid Term Exam',
    final: 'Final Term Exam',
};

const sumCategoryWeight = (exams, category) =>
    exams
        .filter(e => e.assessment_category === category && e.weight_percentage != null && parseFloat(e.weight_percentage) > 0)
        .reduce((total, e) => total + parseFloat(e.weight_percentage), 0);

const isTeacherContinuousExam = (exam) =>
    CONTINUOUS_CATEGORIES.includes(exam.assessment_category)
    && exam.weight_percentage != null
    && parseFloat(exam.weight_percentage) > 0;

const examsForMarksEntry = (exams) => {
    const eligible = exams.filter(exam =>
        exam.assessment_category === 'mid_term'
        || exam.assessment_category === 'final'
        || isTeacherContinuousExam(exam)
    );
    const order = { quiz: 1, assignment: 2, presentation: 3, mid_term: 4, final: 5 };
    return eligible.sort((a, b) => {
        const diff = (order[a.assessment_category] || 99) - (order[b.assessment_category] || 99);
        return diff !== 0 ? diff : (a.exam_name || '').localeCompare(b.exam_name || '');
    });
};

const buildWeightSummary = (exams) => {
    const continuous = CONTINUOUS_CATEGORIES.map((category) => {
        const used = sumCategoryWeight(exams, category);
        const cap = CATEGORY_CAPS[category];
        return { category, label: CATEGORY_LABELS[category], used, cap, remaining: Math.max(0, cap - used) };
    });
    const continuousUsed = continuous.reduce((t, c) => t + c.used, 0);
    return {
        continuous,
        continuousUsed,
        continuousCap: 30,
        midFixed: FIXED_WEIGHTS.mid_term,
        finalFixed: FIXED_WEIGHTS.final,
        totalAllocated: continuousUsed + FIXED_WEIGHTS.mid_term + FIXED_WEIGHTS.final,
    };
};

export const TeacherProfileModal = ({ profile, loading, onClose }) => (
    <div className="modal-overlay" onClick={onClose}>
        <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '560px', width: '95%' }}>
            <div className="modal-header">
                <h3>My Profile</h3>
                <button className="close-btn" onClick={onClose}><XIcon /></button>
            </div>
            <div className="modal-body">
                {loading ? <LoadingSpinner message="Loading profile..." /> : profile ? (
                    <div style={{ display: 'grid', gap: '8px' }}>
                        <p><strong>Employee ID:</strong> {profile.employee_code}</p>
                        <p><strong>Name:</strong> {profile.username}</p>
                        <p><strong>Email:</strong> {profile.email}</p>
                        <p><strong>Department:</strong> {profile.department_name}</p>
                        <p><strong>Program:</strong> {profile.program_name || '—'}</p>
                        <p><strong>Designation:</strong> {profile.designation_title}</p>
                        <p><strong>Qualification:</strong> {profile.qualification}</p>
                        <p><strong>Employment Type:</strong> {profile.employment_type}</p>
                        <p><strong>Office Floor:</strong> {profile.office_floor || '—'}</p>
                        <p><strong>Office Hours:</strong> {profile.office_hours || '—'}</p>
                        {profile.employee_profile && (<>
                            <hr />
                            <p><strong>Phone:</strong> {profile.employee_profile.phone_number || '—'}</p>
                            <p><strong>Address:</strong> {profile.employee_profile.current_address || '—'}</p>
                        </>)}
                    </div>
                ) : <p>Unable to load profile.</p>}
            </div>
            <div className="modal-footer">
                <button className="btn-secondary" onClick={onClose}>Close</button>
            </div>
        </div>
    </div>
);

export const TeacherSectionsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [filters, setFilters] = useState({ department_id: '', program_id: '' });
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('active');
    const [editModal, setEditModal] = useState(null);
    const [editReason, setEditReason] = useState('');
    const [submittingEdit, setSubmittingEdit] = useState(false);

    const loadCourses = () => {
        if (!token) return;
        setLoading(true);
        const params = new URLSearchParams();
        params.set('active', tab === 'completed' ? 'false' : 'true');
        if (filters.department_id) params.set('department_id', filters.department_id);
        if (filters.program_id) params.set('program_id', filters.program_id);
        getMyOfferings(token, params.toString())
            .then(d => setItems(normalizeList(d)))
            .catch((e) => {
                console.error(e);
                showToast(e.response?.data?.error || 'Failed to load courses', 'error');
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !filters.department_id) { setPrograms([]); return; }
        listPrograms(token, filters.department_id).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, filters.department_id]);

    useEffect(() => { loadCourses(); }, [token, tab, filters]);

    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(
        items,
        ['course_code', 'course_name', 'department_name', 'program_code', 'program_name']
    );

    const submitOfferingEditRequest = async () => {
        if (!editModal || !editReason.trim()) {
            alert('Please enter a reason for the edit request.');
            return;
        }
        setSubmittingEdit(true);
        try {
            await requestOfferingMarksEdit({
                offering_id: editModal.offering_id || editModal.section_id,
                reason: editReason.trim(),
            }, token);
            showToast('Marks edit request submitted to admin');
            setEditModal(null);
            setEditReason('');
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to submit request');
        } finally {
            setSubmittingEdit(false);
        }
    };

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > COURSES" title="My Courses" />
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                <button type="button" className={tab === 'active' ? 'btn-save' : 'btn-secondary'} onClick={() => setTab('active')}>Active</button>
                <button type="button" className={tab === 'completed' ? 'btn-save' : 'btn-secondary'} onClick={() => setTab('completed')}>Completed</button>
            </div>
            {tab === 'active' && (
                <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                    Active courses are assigned to you and do not have final marks submitted yet.
                </p>
            )}
            <div className="filter-bar" style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <select className="field-input field-select" value={filters.department_id}
                    onChange={e => setFilters({ department_id: e.target.value, program_id: '' })}>
                    <option value="">All departments</option>
                    {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                </select>
                <select className="field-input field-select" value={filters.program_id} disabled={!filters.department_id}
                    onChange={e => setFilters(f => ({ ...f, program_id: e.target.value }))}>
                    <option value="">All programs</option>
                    {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                </select>
            </div>
            <div className="form-card">
                <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search course, department, program..." />
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Code</th><th>Course</th><th>Type</th><th>Department</th><th>Program</th><th>Enrolled</th><th>Status</th>{tab === 'completed' && <th>Action</th>}</tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={tab === 'completed' ? 9 : 8} icon={<BookIcon size={20} />} title={tab === 'completed' ? 'No completed courses' : 'No assigned courses'} subtitle={tab === 'completed' ? 'Courses appear here after you submit final marks.' : 'Courses appear here when assigned by admin.'} /> : paginated.map((item, i) => (
                                <tr key={item.offering_id || `${item.course_id}-${item.program_code}-${item.repeat_offering ? 'repeat' : 'regular'}`}>
                                    <td>{(page-1)*pageSize+i+1}</td>
                                    <td><strong>{item.course_code || '—'}</strong></td>
                                    <td>{item.course_name || '—'}</td>
                                    <td>{item.offering_type_label || (item.repeat_offering ? 'Repeat' : 'Regular')}</td>
                                    <td>{item.department_name || '—'}</td>
                                    <td>{item.program_code || item.program_name || '—'}</td>
                                    <td>{item.enrolled_count ?? 0}</td>
                                    <td><span className={getStatusBadgeClass(item.marks_unlock_active ? 'active' : ((item.teaching_complete || item.marks_locked) ? 'completed' : (item.has_offering === false ? 'pending' : 'active')))}>{item.marks_unlock_active ? 'UNLOCKED' : ((item.teaching_complete || item.marks_locked) ? 'COMPLETED' : (item.has_offering === false ? 'AWAITING ENROLLMENT' : 'ACTIVE'))}</span></td>
                                    {tab === 'completed' && (
                                        <td>
                                            {item.marks_unlock_active ? (
                                                <span className="field-hint">Edit marks in Examinations tab, then re-submit final marks.</span>
                                            ) : (
                                                <button type="button" className="action-btn view-btn" onClick={() => { setEditModal(item); setEditReason(''); }}>
                                                    Request Edit
                                                </button>
                                            )}
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal isOpen={!!editModal} render={() => (
                <div className="modal-overlay" onClick={() => setEditModal(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
                        <div className="modal-header">
                            <h3>Request Marks Edit — {editModal.course_code}</h3>
                            <button className="close-btn" onClick={() => setEditModal(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                                Admin approval unlocks this course for editing until you re-submit final marks.
                            </p>
                            <div className="field-group">
                                <label className="field-label">Reason <span className="required">*</span></label>
                                <textarea className="field-input field-textarea" rows={3} value={editReason}
                                    onChange={e => setEditReason(e.target.value)}
                                    placeholder="Explain why marks need correction..." />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setEditModal(null)}>Cancel</button>
                            <button className="btn-primary" onClick={submitOfferingEditRequest} disabled={submittingEdit}>
                                {submittingEdit ? 'Submitting...' : 'Submit Request'}
                            </button>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export const TeacherAttendancePage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    
    const [sections, setSections] = useState([]);
    const [selectedSection, setSelectedSection] = useState('');
    const [attendanceDate, setAttendanceDate] = useState(new Date().toISOString().split('T')[0]);
    const [lectureNumber, setLectureNumber] = useState(1);
    const [topicCovered, setTopicCovered] = useState('');
    const [students, setStudents] = useState([]);
    const [studentStatuses, setStudentStatuses] = useState({}); // { student_id: 'present' | 'absent' | 'leave' }
    const [fetchingStudents, setFetchingStudents] = useState(false);

    const load = () => listAttendance(token).then(d => setItems(normalizeList(d)));

    useEffect(() => {
        if (token) {
            load().finally(() => setLoading(false));
            getMyOfferingsForMarks(token).then(d => {
                const list = normalizeList(d);
                setSections(list);
                if (list.length > 0) setSelectedSection(String(list[0].offering_id || list[0].section_id));
            }).catch(console.error);
        }
    }, [token]);

    useEffect(() => {
        if (showModal && selectedSection) {
            fetchSectionStudents(selectedSection, attendanceDate);
            nextLectureNumber(selectedSection, token).then(d => {
                if (d?.lecture_number) setLectureNumber(d.lecture_number);
            }).catch(() => {});
        }
    }, [showModal, selectedSection, attendanceDate, token]);

    const fetchSectionStudents = async (secId, date) => {
        if (!secId) return;
        setFetchingStudents(true);
        try {
            const list = await getOfferingStudents(secId, token, date);
            setStudents(Array.isArray(list) ? list : []);
            const initialMap = {};
            (Array.isArray(list) ? list : []).forEach(s => {
                initialMap[s.student_id] = s.default_status || (s.approved_leave ? 'leave' : 'present');
            });
            setStudentStatuses(initialMap);
        } catch (e) {
            console.error(e);
        } finally {
            setFetchingStudents(false);
        }
    };

    const handleStatusChange = (studentId, status) => {
        const student = students.find(s => s.student_id === studentId);
        if (student?.approved_leave && status !== 'leave') return;
        setStudentStatuses(prev => ({ ...prev, [studentId]: status }));
    };

    const setAllStatuses = (status) => {
        const next = { ...studentStatuses };
        students.forEach((s) => {
            if (s.approved_leave && status !== 'leave') return;
            next[s.student_id] = status;
        });
        setStudentStatuses(next);
    };

    const handleSubmit = async () => {
        if (!selectedSection || !attendanceDate) {
            alert('Course and date are required.');
            return;
        }
        const records = Object.keys(studentStatuses).map(stId => ({
            student: parseInt(stId),
            status: studentStatuses[stId],
            remarks: ''
        }));
        
        try {
            await markAttendance({
                offering_id: parseInt(selectedSection, 10),
                attendance_date: attendanceDate,
                lecture_number: lectureNumber,
                topic_covered: topicCovered,
                records: records
            }, token);
            showToast('Attendance marked successfully!');
            setShowModal(false);
            load();
        } catch (e) {
            alert(e.response?.data?.error || e.message || 'Failed to mark attendance');
        }
    };

    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(items, ['course_code', 'course_name', 'topic_covered', 'faculty_name']);

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ATTENDANCE" title="Attendance Management" />
            <div className="form-card">
                <div className="table-toolbar">
                    <button className="btn-add" onClick={() => setShowModal(true)}><PlusIcon /> Mark Class Attendance</button>
                </div>
                <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search course, topic..." />
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Course</th><th>Date</th><th>Lec#</th><th>Topic Covered</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={5} icon={<ClipboardIcon size={20} />} title="No attendance sessions marked yet" /> : paginated.map((item, i) => (
                                <tr key={i}>
                                    <td>{(page-1)*pageSize+i+1}</td>
                                    <td>{item.course_code || item.faculty_name || 'Course'}</td>
                                    <td>{formatDate(item.attendance_date || item.date)}</td>
                                    <td>{item.lecture_number || '1'}</td>
                                    <td>{item.topic_covered || '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" style={{ maxWidth: '700px', width: '90%' }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Mark Session Attendance</h3>
                            <button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
                            <div className="two-column-grid" style={{ marginBottom: '16px' }}>
                                <div className="field-group">
                                    <label className="field-label">Course</label>
                                    <select className="field-input field-select" value={selectedSection} onChange={e => setSelectedSection(e.target.value)}>
                                        <option value="">Select course</option>
                                        {sections.map(s => (
                                            <option key={s.offering_id || s.section_id || s.course_id} value={s.offering_id || s.section_id || ''}>
                                                {formatOfferingLabel(s)}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="field-group">
                                    <label className="field-label">Attendance Date</label>
                                    <input type="date" className="field-input" value={attendanceDate} onChange={e => setAttendanceDate(e.target.value)} />
                                </div>
                                <div className="field-group">
                                    <label className="field-label">Lecture Number</label>
                                    <input type="number" className="field-input" value={lectureNumber} onChange={e => setLectureNumber(parseInt(e.target.value) || 1)} />
                                </div>
                                <div className="field-group">
                                    <label className="field-label">Topic Covered</label>
                                    <input type="text" className="field-input" placeholder="e.g. Introduction to React" value={topicCovered} onChange={e => setTopicCovered(e.target.value)} />
                                </div>
                            </div>

                            <h4 style={{ margin: '16px 0 8px 0', borderBottom: '1px solid #eee', paddingBottom: '6px' }}>Enrolled Students Attendance Status</h4>
                            {students.length > 0 && (
                                <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
                                    <button type="button" className="btn-secondary" onClick={() => setAllStatuses('present')}>Mark All Present</button>
                                    <button type="button" className="btn-secondary" onClick={() => setAllStatuses('absent')}>Mark All Absent</button>
                                </div>
                            )}

                            {fetchingStudents ? (
                                <LoadingSpinner message="Loading enrolled students..." />
                            ) : students.length === 0 ? (
                                <p style={{ color: '#666', fontStyle: 'italic' }}>No registered students found in this section.</p>
                            ) : (
                                <div className="data-table-wrapper">
                                    <table className="data-table">
                                        <thead><tr><th>Reg #</th><th>Student Name</th><th>Status (Radio)</th></tr></thead>
                                        <tbody>
                                            {students.map(std => (
                                                <tr key={std.student_id}>
                                                    <td>{std.registration_number}</td>
                                                    <td>{std.username}{std.approved_leave ? ' (approved leave)' : ''}</td>
                                                    <td>
                                                        <div style={{ display: 'flex', gap: '12px' }}>
                                                            <label style={{ cursor: std.approved_leave ? 'not-allowed' : 'pointer', color: 'green', fontWeight: 'bold', opacity: std.approved_leave ? 0.5 : 1 }}>
                                                                <input type="radio" name={`status_${std.student_id}`} value="present" disabled={std.approved_leave} checked={studentStatuses[std.student_id] === 'present'} onChange={() => handleStatusChange(std.student_id, 'present')} /> Present
                                                            </label>
                                                            <label style={{ cursor: std.approved_leave ? 'not-allowed' : 'pointer', color: 'red', fontWeight: 'bold', opacity: std.approved_leave ? 0.5 : 1 }}>
                                                                <input type="radio" name={`status_${std.student_id}`} value="absent" disabled={std.approved_leave} checked={studentStatuses[std.student_id] === 'absent'} onChange={() => handleStatusChange(std.student_id, 'absent')} /> Absent
                                                            </label>
                                                            <label style={{ cursor: 'pointer', color: 'orange', fontWeight: 'bold' }}>
                                                                <input type="radio" name={`status_${std.student_id}`} value="leave" checked={studentStatuses[std.student_id] === 'leave'} onChange={() => handleStatusChange(std.student_id, 'leave')} /> Leave
                                                            </label>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn-primary" onClick={handleSubmit}>Submit Attendance</button>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export const TeacherExaminationsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [sections, setSections] = useState([]);
    const [selectedOffering, setSelectedOffering] = useState('');
    const [loading, setLoading] = useState(true);
    const [selectedExam, setSelectedExam] = useState(null);
    const [marks, setMarks] = useState([]);
    const [students, setStudents] = useState([]);
    const [marksForm, setMarksForm] = useState({});
    const [showMarksModal, setShowMarksModal] = useState(false);
    const [lockStatus, setLockStatus] = useState(null);
    const [showContinuousModal, setShowContinuousModal] = useState(false);
    const [continuousForm, setContinuousForm] = useState({ offering_id: '', assessment_category: 'quiz', exam_name: '', weight_percentage: '', total_marks: 100 });
    const [creatingContinuous, setCreatingContinuous] = useState(false);
    const [weightEditModal, setWeightEditModal] = useState(null);
    const [savingWeight, setSavingWeight] = useState(false);

    const loadExams = async (offeringId = selectedOffering) => {
        if (!token) return [];
        const params = offeringId ? `offering=${encodeURIComponent(offeringId)}` : '';
        const exams = await listExaminations(token, params).then(d => normalizeList(d));
        setItems(exams);
        return exams;
    };

    useEffect(() => {
        if (!token) return;
        getMyOfferingsForMarks(token)
            .then(d => {
                const list = normalizeList(d);
                setSections(list);
                if (list.length > 0) {
                    setSelectedOffering(String(list[0].offering_id || list[0].section_id || ''));
                }
            })
            .catch((e) => {
                console.error(e);
                showToast(e.response?.data?.error || 'Failed to load courses for marks', 'error');
            })
            .finally(() => setLoading(false));
    }, [token]);

    useEffect(() => {
        if (!token || !selectedOffering) {
            setItems([]);
            return;
        }
        setLoading(true);
        loadExams(selectedOffering).finally(() => setLoading(false));
    }, [token, selectedOffering]);

    const formatMarksError = (err) => {
        const data = err?.response?.data;
        if (!data) return err?.message || 'Failed to save marks';
        if (data.error) return data.error;
        if (Array.isArray(data.errors) && data.errors.length > 0) {
            const first = data.errors[0];
            if (typeof first === 'string') return first;
            if (first?.error) return first.error;
            if (first?.errors) return JSON.stringify(first.errors);
        }
        return 'Failed to save marks';
    };

    const openMarks = async (exam) => {
        setSelectedExam(exam);
        setShowMarksModal(true);
        setLockStatus(null);
        setStudents([]);
        setMarksForm({});
        try {
            const offeringId = exam.offering || exam.section || selectedOffering;
            const [marksData, secStudents, lockData] = await Promise.all([
                listMarks(exam.exam_id, token),
                offeringId ? getOfferingStudents(offeringId, token, '', true) : Promise.resolve([]),
                getMarksLockStatus({ exam_id: exam.exam_id }, token),
            ]);
            const markList = normalizeList(marksData);
            const roster = Array.isArray(secStudents) ? secStudents : [];
            const rosterIds = new Set(roster.map(s => s.student_id));
            const mergedStudents = [...roster];
            markList.forEach(m => {
                if (m.student != null && !rosterIds.has(m.student)) {
                    mergedStudents.push({
                        student_id: m.student,
                        registration_number: m.student_reg || '—',
                        username: m.student_username || m.student_reg || `Student ${m.student}`,
                    });
                    rosterIds.add(m.student);
                }
            });
            mergedStudents.sort((a, b) => (
                (a.registration_number || '').localeCompare(b.registration_number || '')
            ));
            setMarks(markList);
            setStudents(mergedStudents);
            setLockStatus(lockData);
            const form = {};
            mergedStudents.forEach(s => {
                const existing = markList.find(m => m.student === s.student_id);
                form[s.student_id] = existing?.obtained_marks ?? '';
            });
            setMarksForm(form);
        } catch (e) {
            alert('Failed to load marks');
        }
    };

    const examEditable = lockStatus?.editable ?? true;
    const examFullyLocked = lockStatus && !lockStatus.editable;

    const saveMarks = async () => {
        if (!selectedExam) return;
        const examTotal = Number(selectedExam.total_marks) || 100;
        for (const [stId, val] of Object.entries(marksForm)) {
            if (val === '' || val == null) continue;
            const num = parseFloat(val);
            if (Number.isNaN(num)) {
                alert('Please enter valid numeric marks.');
                return;
            }
            if (num < 0) {
                alert('Marks cannot be negative.');
                return;
            }
            if (num > examTotal) {
                alert(`Marks cannot exceed the exam total of ${examTotal}.`);
                return;
            }
        }
        const entries = Object.keys(marksForm).map(stId => ({
            student: parseInt(stId, 10),
            obtained_marks: marksForm[stId] === '' ? null : parseFloat(marksForm[stId]),
            is_absent: marksForm[stId] === '',
        }));
        try {
            await enterMarks(selectedExam.exam_id, { marks: entries }, token);
            showToast('Marks saved');
            setShowMarksModal(false);
            if (selectedOffering) await loadExams(selectedOffering);
        } catch (e) {
            alert(formatMarksError(e));
        }
    };

    const handleSubmitFinal = async (sectionId) => {
        if (!confirm('Submit final marks? This will lock the section and compute final grades.')) return;
        try {
            await submitFinalMarks(sectionId, token);
            showToast('Final marks submitted. Section locked.');
            setSelectedOffering('');
            const secs = await getMyOfferingsForMarks(token).then(d => normalizeList(d));
            setSections(secs);
            setItems([]);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to submit final marks');
        }
    };

    const submitContinuousAssessment = async () => {
        const { offering_id, assessment_category, exam_name, weight_percentage, total_marks } = continuousForm;
        if (!offering_id || !exam_name.trim() || weight_percentage === '') {
            alert('Course, assessment name, and weight are required.');
            return;
        }
        setCreatingContinuous(true);
        try {
            await createContinuousAssessment({
                offering_id: parseInt(offering_id, 10),
                assessment_category,
                exam_name: exam_name.trim(),
                weight_percentage: parseFloat(weight_percentage),
                total_marks: parseFloat(total_marks) || 100,
            }, token);
            showToast('Continuous assessment created');
            setShowContinuousModal(false);
            setContinuousForm({ offering_id: selectedOffering || '', assessment_category: 'quiz', exam_name: '', weight_percentage: '', total_marks: 100 });
            if (selectedOffering) await loadExams(selectedOffering);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to create assessment');
        } finally {
            setCreatingContinuous(false);
        }
    };

    const openWeightEdit = (exam) => {
        setWeightEditModal({
            exam_id: exam.exam_id,
            exam_name: exam.exam_name,
            assessment_category: exam.assessment_category,
            weight_percentage: exam.weight_percentage ?? '',
        });
    };

    const openAddAssessment = (category) => {
        if (!selectedOffering) {
            alert('Select a course first.');
            return;
        }
        setContinuousForm({
            offering_id: selectedOffering,
            assessment_category: category,
            exam_name: '',
            weight_percentage: '',
            total_marks: 100,
        });
        setShowContinuousModal(true);
    };

    const saveWeightEdit = async () => {
        if (!weightEditModal) return;
        const weight = parseFloat(weightEditModal.weight_percentage);
        if (Number.isNaN(weight) || weight <= 0) {
            alert('Enter a valid weight percentage.');
            return;
        }
        setSavingWeight(true);
        try {
            await updateExamination(weightEditModal.exam_id, { weight_percentage: weight }, token);
            showToast('Weight updated');
            setWeightEditModal(null);
            if (selectedOffering) await loadExams(selectedOffering);
        } catch (e) {
            alert(e.response?.data?.error || e.response?.data?.weight_percentage?.[0] || 'Failed to update weight');
        } finally {
            setSavingWeight(false);
        }
    };

    const selectedSection = sections.find(s => String(s.offering_id || s.section_id) === String(selectedOffering));
    const weightSummary = buildWeightSummary(items);
    const weightIsComplete = Math.abs(weightSummary.totalAllocated - 100) < 0.01;
    const marksExams = useMemo(() => examsForMarksEntry(items), [items]);
    const canAdjustWeight = (exam) => isTeacherContinuousExam(exam);
    const categorySummary = (category) => weightSummary.continuous.find(c => c.category === category);
    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(marksExams, ['exam_name', 'assessment_category']);
    if (loading && !selectedOffering) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > EXAMINATIONS" title="Examinations & Marks" />

            <div className="form-card" style={{ marginBottom: 16 }}>
                <h3 style={{ margin: '0 0 12px 0' }}>Step 1 — Select Course</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Choose an active course, or a completed course that admin unlocked for mark corrections.
                </p>
                <div className="field-group" style={{ maxWidth: 420, marginBottom: 0 }}>
                    <label className="field-label">Course <span className="required">*</span></label>
                    <select
                        className="field-input field-select"
                        value={selectedOffering}
                        onChange={e => { setSelectedOffering(e.target.value); setPage(1); }}
                    >
                        <option value="">Select course to begin</option>
                        {sections.map(s => (
                            <option key={s.offering_id || s.section_id} value={s.offering_id || s.section_id}>
                                {formatOfferingLabel(s)}
                                {s.marks_unlock_active ? ' (unlocked for edit)' : ''}
                            </option>
                        ))}
                    </select>
                </div>
                {sections.length === 0 && !loading && (
                    <p style={{ color: 'var(--text-secondary)', marginTop: 12 }}>No courses available for marks entry. Request an edit from My Courses → Completed if final marks were already submitted.</p>
                )}
                {selectedSection?.marks_unlock_active && (
                    <p style={{ marginTop: 12, padding: '10px 12px', borderRadius: 8, background: 'rgba(34,197,94,0.1)', color: 'var(--text-secondary)' }}>
                        Admin unlocked this course until {selectedSection.marks_unlock_until ? new Date(selectedSection.marks_unlock_until).toLocaleString() : 'the deadline'}. Update marks in Step 3, then click <strong>Submit Final Marks</strong> again when done.
                    </p>
                )}
            </div>

            {selectedOffering && (
            <>
            {loading ? <LoadingSpinner message="Loading course assessments..." /> : (
            <>
            <div className="form-card" style={{ marginBottom: 16 }}>
                <h3 style={{ margin: '0 0 12px 0' }}>Step 2 — Set Weightage</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                    Quiz, assignment, and presentation: up to 10% each (split across one or more items).
                    Mid Term is fixed at 30% and Final at 40%.
                </p>
                <div style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
                    {weightSummary.continuous.map(row => (
                        <div key={row.category} style={{ padding: '12px 14px', borderRadius: 8, background: 'var(--bg-secondary)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                                <strong>{row.label}</strong>
                                <span>{row.used.toFixed(1)}% / {row.cap}% used ({row.remaining.toFixed(1)}% remaining)</span>
                            </div>
                        </div>
                    ))}
                    <div style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(65,105,225,0.08)' }}>
                        <strong>Mid Term Exam</strong> — <span>30% (fixed)</span>
                    </div>
                    <div style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(65,105,225,0.08)' }}>
                        <strong>Final Term Exam</strong> — <span>40% (fixed)</span>
                    </div>
                    <div style={{ padding: '12px 14px', borderRadius: 8, border: `1px solid ${weightIsComplete ? 'var(--border-color)' : '#fca5a5'}`, background: weightIsComplete ? 'transparent' : 'rgba(239,68,68,0.06)' }}>
                        <strong>Total allocated:</strong> {weightSummary.totalAllocated.toFixed(1)}% / 100%
                        {!weightIsComplete && (
                            <p style={{ margin: '8px 0 0', color: '#dc2626', fontSize: '0.875rem' }}>
                                Complete 100% weightage (30% continuous + 30% mid + 40% final) — students are not eligible for promotion until this is done.
                            </p>
                        )}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    {weightSummary.continuous.map(row => (
                        row.remaining > 0 ? (
                            <button key={row.category} type="button" className="btn-primary" onClick={() => openAddAssessment(row.category)}>
                                <PlusIcon /> Add {row.label}
                            </button>
                        ) : (
                            <span key={row.category} className="field-hint" style={{ alignSelf: 'center' }}>
                                {row.label} cap reached ({row.cap}%)
                            </span>
                        )
                    ))}
                </div>
            </div>

            <div className="form-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                    <div>
                        <h3 style={{ margin: 0 }}>Step 3 — Enter Marks</h3>
                        <p style={{ color: 'var(--text-secondary)', margin: '8px 0 0 0' }}>
                            Quizzes, assignments, and presentations you added in Step 2, plus Mid and Final exams.
                            Enter marks for each enrolled student separately.
                        </p>
                    </div>
                    {selectedSection && (
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => handleSubmitFinal(selectedSection.offering_id || selectedSection.section_id)}
                            disabled={!weightIsComplete}
                            title={!weightIsComplete ? 'Complete 100% assessment weightage before submitting final marks' : ''}
                        >
                            Submit Final Marks
                        </button>
                    )}
                </div>
                <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search assessment..." />
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Assessment</th><th>Category</th><th>Weight %</th><th>Total Marks</th><th>Actions</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={6} icon={<FileIcon />} title="Add assessments in Step 2, then enter marks here" />
                            ) : paginated.map((item, i) => (
                                <tr key={item.exam_id || i}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td>{item.exam_name}</td>
                                    <td>{CATEGORY_LABELS[item.assessment_category] || item.exam_type_name || '—'}</td>
                                    <td>
                                        {item.assessment_category === 'mid_term' ? '30 (fixed)'
                                            : item.assessment_category === 'final' ? '40 (fixed)'
                                            : `${item.weight_percentage}%`}
                                    </td>
                                    <td>{item.total_marks}</td>
                                    <td style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                        {canAdjustWeight(item) && (
                                            <button type="button" className="action-btn" onClick={() => openWeightEdit(item)}>Edit Weight</button>
                                        )}
                                        <button className="action-btn view-btn" onClick={() => openMarks(item)}>
                                            Enter Marks
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
            </>
            )}
            </>
            )}

            <ModalPortal isOpen={showMarksModal && !!selectedExam} render={() => (
                <div className="modal-overlay" onClick={() => setShowMarksModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '650px', width: '90%' }}>
                        <div className="modal-header">
                            <h3>Enter Marks — {selectedExam.exam_name}</h3>
                            <button className="close-btn" onClick={() => setShowMarksModal(false)}><XIcon /></button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                            {lockStatus && !examEditable && (
                                <div className="field-hint" style={{ marginBottom: 12, padding: '8px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 6 }}>
                                    Locked — {lockStatus.lock_reason || 'Marks cannot be edited.'} Use <strong>My Courses → Completed → Request Edit</strong> to ask admin for a course unlock.
                                </div>
                            )}
                            <table className="data-table">
                                <thead><tr><th>Reg #</th><th>Student</th><th>Obtained Marks</th></tr></thead>
                                <tbody>
                                    {students.length === 0 ? (
                                        <tr><td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No enrolled students found for this course.</td></tr>
                                    ) : students.map(s => (
                                        <tr key={s.student_id}>
                                            <td>{s.registration_number}</td>
                                            <td>{s.username}</td>
                                            <td>
                                                <input
                                                    type="number"
                                                    className="field-input"
                                                    style={{ maxWidth: '100px' }}
                                                    value={marksForm[s.student_id] ?? ''}
                                                    onChange={e => setMarksForm({ ...marksForm, [s.student_id]: e.target.value })}
                                                    onClick={e => e.stopPropagation()}
                                                    min={0}
                                                    max={selectedExam?.total_marks || 100}
                                                    step="0.01"
                                                    placeholder="Marks"
                                                    disabled={!examEditable}
                                                />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowMarksModal(false)}>Cancel</button>
                            <button className="btn-primary" onClick={saveMarks} disabled={examFullyLocked}>Save Marks</button>
                        </div>
                    </div>
                </div>
            )} />

            <ModalPortal isOpen={showContinuousModal} render={() => {
                const catRow = categorySummary(continuousForm.assessment_category);
                const maxWeight = catRow ? Math.min(catRow.cap, catRow.remaining) : 10;
                return (
                    <div className="modal-overlay" onClick={() => setShowContinuousModal(false)}>
                        <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
                            <div className="modal-header">
                                <h3>Add {CATEGORY_LABELS[continuousForm.assessment_category]}</h3>
                                <button className="close-btn" onClick={() => setShowContinuousModal(false)}><XIcon /></button>
                            </div>
                            <div className="modal-body">
                                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                                    Course: <strong>{selectedSection?.course_code || '—'}</strong>.
                                    {catRow && <> Up to <strong>{maxWeight.toFixed(1)}%</strong> remaining for {catRow.label.toLowerCase()} (max {catRow.cap}% total).</>}
                                </p>
                                <div className="field-group">
                                    <label className="field-label">Assessment Name</label>
                                    <input className="field-input" placeholder="e.g. Quiz 2, Assignment 3"
                                        value={continuousForm.exam_name}
                                        onChange={e => setContinuousForm({ ...continuousForm, exam_name: e.target.value })} />
                                </div>
                                <div className="two-column-grid">
                                    <div className="field-group">
                                        <label className="field-label">Weight (% of final)</label>
                                        <input type="number" className="field-input" min={0.5} max={maxWeight} step={0.5}
                                            value={continuousForm.weight_percentage}
                                            onChange={e => setContinuousForm({ ...continuousForm, weight_percentage: e.target.value })} />
                                    </div>
                                    <div className="field-group">
                                        <label className="field-label">Total Marks</label>
                                        <input type="number" className="field-input" min={1}
                                            value={continuousForm.total_marks}
                                            onChange={e => setContinuousForm({ ...continuousForm, total_marks: e.target.value })} />
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button className="btn-secondary" onClick={() => setShowContinuousModal(false)}>Cancel</button>
                                <button className="btn-primary" onClick={submitContinuousAssessment} disabled={creatingContinuous}>
                                    {creatingContinuous ? 'Creating...' : 'Add Assessment'}
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }} />

            <ModalPortal isOpen={!!weightEditModal} render={() => {
                const catRow = categorySummary(weightEditModal?.assessment_category);
                const currentWeight = parseFloat(weightEditModal?.weight_percentage || 0) || 0;
                const maxWeight = catRow ? Math.min(catRow.cap, catRow.remaining + currentWeight) : 10;
                return (
                <div className="modal-overlay" onClick={() => setWeightEditModal(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
                        <div className="modal-header">
                            <h3>Edit Weight — {weightEditModal.exam_name}</h3>
                            <button className="close-btn" onClick={() => setWeightEditModal(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                                {CATEGORY_LABELS[weightEditModal.assessment_category]} — max {maxWeight.toFixed(1)}% for this item (category cap {catRow?.cap ?? 10}%).
                            </p>
                            <div className="field-group">
                                <label className="field-label">Weight (% of final grade)</label>
                                <input
                                    type="number"
                                    className="field-input"
                                    min={0.5}
                                    max={maxWeight}
                                    step={0.5}
                                    value={weightEditModal.weight_percentage}
                                    onChange={e => setWeightEditModal({ ...weightEditModal, weight_percentage: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setWeightEditModal(null)}>Cancel</button>
                            <button className="btn-primary" onClick={saveWeightEdit} disabled={savingWeight}>
                                {savingWeight ? 'Saving...' : 'Save Weight'}
                            </button>
                        </div>
                    </div>
                </div>
                );
            }} />
        </div>
    );
};

export const TeacherNotificationsPage = () => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);
    const load = () => listNotifications(token).then(d => setItems(normalizeList(d)));
    useEffect(() => { if (token) load().finally(() => setLoading(false)); }, [token]);
    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(items, ['title', 'message']);
    const openNotification = async (item) => {
        setSelected(item);
        if (!item.is_read) {
            await markNotificationRead(item.notification_id, token).catch(() => {});
            load();
        }
    };
    const handleMarkAllRead = async () => {
        await markAllNotificationsRead(token).catch(() => {});
        load();
    };
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > NOTIFICATIONS" title="Notifications" />
            <div style={{ marginBottom: 12 }}>
                <button type="button" className="btn-secondary small" onClick={handleMarkAllRead}>Mark all as read</button>
            </div>
            <div className="form-card">
                <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search notifications..." />
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Title</th><th>Preview</th><th>Date</th><th>Read</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={5} icon={<BellIcon size={20} />} title="No notifications" /> : paginated.map((item, i) => (
                                <tr key={i} style={{ cursor: 'pointer' }} onClick={() => openNotification(item)}>
                                    <td>{(page-1)*pageSize+i+1}</td><td>{item.title || item.subject || '—'}</td>
                                    <td>{(item.message || '').substring(0, 50)}...</td>
                                    <td>{formatDate(item.created_at)}</td><td>{item.is_read ? 'Yes' : 'No'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
            <ModalPortal isOpen={!!selected} render={() => (
                <div className="modal-overlay" onClick={() => setSelected(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header"><h3>{selected?.title || 'Notification'}</h3><button type="button" className="close-btn" onClick={() => setSelected(null)}><XIcon /></button></div>
                        <div className="modal-body"><p style={{ color: 'var(--text-secondary)' }}>{formatDate(selected?.created_at)}</p><p style={{ whiteSpace: 'pre-wrap' }}>{selected?.message}</p></div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export const TeacherLeavesPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [remarks, setRemarks] = useState({});

    const load = () => teacherLeaves(token).then(d => setItems(normalizeList(d)));
    useEffect(() => { if (token) load().finally(() => setLoading(false)); }, [token]);

    const handleReview = async (leaveId, action) => {
        const note = remarks[leaveId] || '';
        if (action === 'rejected' && !note.trim()) {
            alert('Remarks required when rejecting leave.');
            return;
        }
        try {
            await reviewLeave(leaveId, { action, teacher_remarks: note }, token);
            showToast(`Leave ${action}`);
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to review leave');
        }
    };

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > LEAVES" title="Student Leave Applications" />
            <div className="form-card">
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Student</th><th>Course</th><th>Dates</th><th>Reason</th><th>Action</th></tr></thead>
                        <tbody>
                            {items.length === 0 ? <EmptyRow colSpan={6} title="No pending leave requests" /> : items.map((item, i) => (
                                <tr key={item.leave_id}>
                                    <td>{i + 1}</td>
                                    <td>{item.student_name} ({item.student_reg})</td>
                                    <td>{item.course_code} — {item.faculty_name || '—'}</td>
                                    <td>{formatDate(item.start_date)} – {formatDate(item.end_date)}</td>
                                    <td>{item.reason}</td>
                                    <td>
                                        <input className="field-input" style={{ maxWidth: '120px', marginBottom: '4px' }} placeholder="Remarks" value={remarks[item.leave_id] || ''} onChange={e => setRemarks({ ...remarks, [item.leave_id]: e.target.value })} />
                                        <div style={{ display: 'flex', gap: '4px' }}>
                                            <button className="btn-verify" onClick={() => handleReview(item.leave_id, 'approved')}>Approve</button>
                                            <button className="action-btn danger" onClick={() => handleReview(item.leave_id, 'rejected')}>Reject</button>
                                        </div>
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

export const TeacherAnnouncementsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [targets, setTargets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ title: '', content: '', announcement_type: 'academic', target_audience_option: '' });

    const load = () => listAnnouncements(token).then(d => setItems(normalizeList(d)));
    useEffect(() => {
        if (!token) return;
        Promise.all([load(), getAnnouncementTargetOptions(token).then(setTargets).catch(() => [])]).finally(() => setLoading(false));
    }, [token]);

    const openCreateModal = () => {
        if (targets.length === 0) {
            alert('No active enrolled courses available. Announcements can only be sent to courses that are active and not yet completed.');
            return;
        }
        setForm({
            title: '',
            content: '',
            announcement_type: 'academic',
            target_audience_option: targets[0]?.value || '',
        });
        setShowModal(true);
    };

    const handleCreate = async () => {
        if (!form.title.trim() || !form.content.trim()) {
            alert('Title and content are required.');
            return;
        }
        if (!form.target_audience_option || !form.target_audience_option.startsWith('offering_')) {
            alert('Select the course whose enrolled students should receive this announcement.');
            return;
        }
        try {
            await createAnnouncement(form, token);
            showToast('Announcement published');
            setShowModal(false);
            setForm({ title: '', content: '', announcement_type: 'academic', target_audience_option: '' });
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to create announcement');
        }
    };

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ANNOUNCEMENTS" title="Announcements" />
            <div className="form-card">
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Publish announcements only to students enrolled in your active, not-yet-completed courses.
                </p>
                <div className="table-toolbar">
                    <button className="btn-add" onClick={openCreateModal} disabled={targets.length === 0}>
                        <PlusIcon /> New Announcement
                    </button>
                </div>
                {targets.length === 0 && (
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>No eligible courses — completed or locked courses cannot receive new announcements.</p>
                )}
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Title</th><th>Course</th><th>Type</th><th>Date</th></tr></thead>
                        <tbody>
                            {items.length === 0 ? <EmptyRow colSpan={5} title="No announcements" /> : items.map((item, i) => (
                                <tr key={item.announcement_id || i}>
                                    <td>{i + 1}</td>
                                    <td>{item.title}</td>
                                    <td>{item.target_course_code || '—'}</td>
                                    <td>{item.announcement_type}</td>
                                    <td>{formatDate(item.published_date || item.created_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header"><h3>Create Announcement</h3><button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button></div>
                        <div className="modal-body">
                            <div className="field-group"><label className="field-label">Title</label><input className="field-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></div>
                            <div className="field-group"><label className="field-label">Type</label>
                                <select className="field-input field-select" value={form.announcement_type} onChange={e => setForm({ ...form, announcement_type: e.target.value })}>
                                    <option value="academic">Academic</option>
                                    <option value="general">General</option>
                                </select>
                            </div>
                            <div className="field-group">
                                <label className="field-label">Course <span className="required">*</span></label>
                                <select className="field-input field-select" value={form.target_audience_option} onChange={e => setForm({ ...form, target_audience_option: e.target.value })}>
                                    <option value="">Select enrolled course</option>
                                    {targets.map(t => (
                                        <option key={t.value} value={t.value}>{t.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="field-group"><label className="field-label">Content</label><textarea className="field-input field-textarea" rows={4} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} /></div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn-primary" onClick={handleCreate}>Publish</button>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};
