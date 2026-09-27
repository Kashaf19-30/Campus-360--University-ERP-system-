import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { myEnrollments, getMyFailedCourses, submitRepeatRequests, flattenActiveEnrollments } from '../../../services/enrollmentsService';
import { myFinalGrades, myResults, myAssessmentMarks } from '../../../services/examinationsService';
import { myAttendanceSummary, submitLeave, myLeaves, deleteLeave } from '../../../services/attendanceService';
import { myChallans, downloadMyChallan } from '../../../services/feesService';
import { getMyStudentProfile, updateMyStudentProfile } from '../../../services/studentsService';
import { myComplaints, submitComplaint, listCategories, deleteComplaint, getComplaint, submitFeedback, getComplaintThread } from '../../../services/complaintsService';
import { listNotifications, markNotificationRead, markAllNotificationsRead, listAnnouncements } from '../../../services/notificationsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, formatDate, getStatusBadgeClass, formatCurriculumSemester } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { PlusIcon, BookIcon, FileIcon, BellIcon, XIcon, TrashIcon } from '../../Icons';

export const MyEnrollmentsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [failedData, setFailedData] = useState({ failed_courses: [], pending_requests: [] });
    const [selectedRepeats, setSelectedRepeats] = useState([]);
    const [submitting, setSubmitting] = useState(false);

    const load = () => {
        if (!token) return;
        myEnrollments(token).then(d => {
            setItems(flattenActiveEnrollments(d));
        }).catch(console.error).finally(() => setLoading(false));
        getMyFailedCourses(token).then(setFailedData).catch((err) => {
            setFailedData({
                failed_courses: [],
                pending_requests: [],
                fee_error: err.response?.data?.error || err.response?.data?.fee_error || null,
            });
        });
    };

    useEffect(() => { load(); }, [token]);

    const toggleRepeat = (courseId) => {
        setSelectedRepeats(prev =>
            prev.includes(courseId) ? prev.filter(id => id !== courseId) : [...prev, courseId]
        );
    };

    const handleRepeatSubmit = async () => {
        if (!selectedRepeats.length) return;
        setSubmitting(true);
        try {
            const res = await submitRepeatRequests(selectedRepeats, token);
            showToast(res.message || 'Repeat request submitted.');
            setSelectedRepeats([]);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Request failed');
        } finally {
            setSubmitting(false);
        }
    };
    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(items, ['course_code', 'course_name']);
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ENROLLMENTS" title="My Enrollments" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                Your active courses for the current semester. Regular curriculum courses and approved repeat courses both appear below (check the Type column).
            </p>

            {failedData.fee_error && (
                <div className="form-card" style={{ marginBottom: 16, borderLeft: '4px solid #f59e0b' }}>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{failedData.fee_error}</p>
                </div>
            )}

            <div className="form-card" style={{ marginBottom: 16 }}>
                <h3 className="section-title">Failed Courses — Request Repeat</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Courses you failed in any term appear here. Select courses and submit a repeat request for admin approval.
                    Enrolled: {failedData.enrolled_credit_hours ?? 0} / {failedData.max_semester_credit_hours ?? 21} CH.
                </p>
                {failedData.failed_courses?.length === 0 && !failedData.pending_requests?.length && !failedData.rejected_requests?.length ? (
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>No failed courses eligible for repeat right now.</p>
                ) : (
                    <>
                        {failedData.rejected_requests?.length > 0 && (
                            <p style={{ marginBottom: 12, color: '#ef4444' }}>
                                Rejected (you may submit again): {failedData.rejected_requests.map(r => `${r.course_code}${r.admin_remarks ? ` — ${r.admin_remarks}` : ''}`).join(', ')}
                            </p>
                        )}
                        {failedData.failed_courses?.map(c => (
                            <label key={c.course_id} style={{ display: 'block', marginBottom: 8, opacity: c.can_request === false ? 0.6 : 1 }}>
                                <input type="checkbox" checked={selectedRepeats.includes(c.course_id)}
                                    disabled={c.can_request === false}
                                    onChange={() => c.can_request !== false && toggleRepeat(c.course_id)} />{' '}
                                {c.course_code} — {c.course_name} ({c.credit_hours} CH)
                                {c.failed_semester && (
                                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}> — failed in {c.failed_semester}</span>
                                )}
                                {c.can_request === false && c.block_reason && (
                                    <span style={{ color: '#ef4444', display: 'block', fontSize: '0.85rem', marginLeft: 24 }}>
                                        {c.block_reason}
                                    </span>
                                )}
                            </label>
                        ))}
                        {failedData.pending_requests?.length > 0 && (
                            <p style={{ marginTop: 8 }}>Pending: {failedData.pending_requests.map(r => `${r.course_code} (${r.status})`).join(', ')}</p>
                        )}
                        {(failedData.failed_courses?.length > 0 || failedData.rejected_requests?.length > 0) && (
                            <button type="button" className="btn-save" disabled={submitting || !selectedRepeats.length || !!failedData.fee_error}
                                onClick={handleRepeatSubmit} style={{ marginTop: 12 }}>
                                {submitting ? 'Submitting...' : 'Request Repeat'}
                            </button>
                        )}
                    </>
                )}
            </div>
            <div className="form-card">
                <div className="table-toolbar"><div className="table-search search-bar" style={{ maxWidth: 360 }}><input className="search-input" placeholder="Search..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} /></div></div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Course</th><th>Title</th><th>Type</th><th>Teacher</th><th>Semester</th><th>Status</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={7} icon={<BookIcon size={20} />} title="No enrollments" /> : paginated.map((item, i) => (
                                <tr key={item.registration_id || i}><td>{(page-1)*pageSize+i+1}</td><td>{item.course_code || '—'}</td><td>{item.course_name || '—'}</td><td>{item.registration_type_display || item.registration_type || 'Regular'}</td><td>{item.faculty_name || '—'}</td><td>{formatCurriculumSemester(item)}</td><td><span className={getStatusBadgeClass('registered')}>ENROLLED</span></td></tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
        </div>
    );
};

export const MyGradesPage = () => {
    const { token } = useAuth();
    const [grades, setGrades] = useState([]);
    const [assessmentMarks, setAssessmentMarks] = useState([]);
    const [results, setResults] = useState([]);
    const [enrollments, setEnrollments] = useState([]);
    const [selectedCourse, setSelectedCourse] = useState('');
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('assessments');
    useEffect(() => {
        if (!token) return;
        Promise.all([
            myFinalGrades(token),
            myAssessmentMarks(token),
            myResults(token),
            myEnrollments(token),
        ]).then(([g, m, r, e]) => {
            setGrades(normalizeList(g));
            setAssessmentMarks(normalizeList(m));
            setResults(normalizeList(r));
            const flat = flattenActiveEnrollments(e);
            setEnrollments(flat);
            if (flat.length > 0) setSelectedCourse(String(flat[0].course_code ?? ''));
        }).catch(console.error).finally(() => setLoading(false));
    }, [token]);
    const filterByCourse = (item) => {
        if (!selectedCourse) return true;
        const courseKey = String(item.course ?? item.course_code ?? '');
        return courseKey === selectedCourse || item.course_code === selectedCourse;
    };
    const filteredGrades = grades.filter(filterByCourse);
    const filteredAssessments = assessmentMarks.filter(filterByCourse);
    const data = tab === 'grades' ? filteredGrades : tab === 'assessments' ? filteredAssessments : results;
    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(data, ['course_code', 'exam_name']);

    const fmtScore = (n) => (n != null && n !== '' ? Number(n).toFixed(2) : '—');
    const assessmentTotals = filteredAssessments.reduce(
        (acc, item) => {
            if (item.is_absent) return acc;
            acc.points += Number(item.weighted_points) || 0;
            acc.max += Number(item.max_weighted_points) || 0;
            return acc;
        },
        { points: 0, max: 0 },
    );
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > GRADES" title="My Grades & Results" />
            <div className="application-tabs">
                <button className={`app-tab ${tab === 'assessments' ? 'active' : ''}`} onClick={() => setTab('assessments')}>Assessment Marks</button>
                <button className={`app-tab ${tab === 'grades' ? 'active' : ''}`} onClick={() => setTab('grades')}>Course Grades</button>
                <button className={`app-tab ${tab === 'results' ? 'active' : ''}`} onClick={() => setTab('results')}>Semester Results</button>
            </div>
            {(tab === 'grades' || tab === 'assessments') && enrollments.length > 0 && (
                <div className="field-group" style={{ marginBottom: '12px', maxWidth: '320px' }}>
                    <label className="field-label">Filter by Course</label>
                    <select className="field-input field-select" value={selectedCourse} onChange={e => setSelectedCourse(e.target.value)}>
                        <option value="">All Courses</option>
                        {[...new Map(enrollments.map(e => [e.course_code, e])).values()].map(e => (
                            <option key={e.course_code} value={e.course_code}>{e.course_code} — {e.course_name}</option>
                        ))}
                    </select>
                </div>
            )}
            <div className="form-card">
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr>
                            {tab === 'assessments' ? (
                                <><th>Sr#</th><th>Course</th><th>Assessment</th><th>Marks</th><th>Points</th><th>Status</th></>
                            ) : tab === 'grades' ? (
                                <><th>Sr#</th><th>Course</th><th>Grade</th><th>Points</th><th>%</th></>
                            ) : (
                                <><th>Sr#</th><th>Semester</th><th>SGPA</th><th>Status</th></>
                            )}
                        </tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={tab === 'assessments' ? 6 : tab === 'grades' ? 5 : 4} icon={<FileIcon />} title="No records" /> : paginated.map((item, i) => (
                                tab === 'assessments' ? (
                                    <tr key={item.marks_id || i}>
                                        <td>{(page-1)*pageSize+i+1}</td>
                                        <td>{item.course_code || '—'}</td>
                                        <td>{item.exam_name || '—'}</td>
                                        <td>{item.is_absent ? 'Absent' : (item.obtained_marks != null ? `${fmtScore(item.obtained_marks)} / ${fmtScore(item.exam_total_marks)}` : '—')}</td>
                                        <td>{item.is_absent ? '—' : (item.weighted_points != null ? `${fmtScore(item.weighted_points)} / ${fmtScore(item.max_weighted_points)}` : '—')}</td>
                                        <td>{item.is_absent ? 'ABSENT' : 'RECORDED'}</td>
                                    </tr>
                                ) : tab === 'grades' ? (
                                    <tr key={item.final_grade_id || i}>
                                        <td>{(page-1)*pageSize+i+1}</td>
                                        <td>{item.course_code || '—'}</td>
                                        <td>{item.grade_letter || '—'}</td>
                                        <td>{item.weighted_points != null ? `${fmtScore(item.weighted_points)} / ${fmtScore(item.max_weighted_points ?? 100)}` : (item.total_obtained_marks != null ? `${fmtScore(item.total_obtained_marks)} / ${fmtScore(item.total_marks)}` : '—')}</td>
                                        <td>{item.percentage != null ? `${Number(item.percentage).toFixed(1)}%` : '—'}</td>
                                    </tr>
                                ) : (
                                    <tr key={i}><td>{(page-1)*pageSize+i+1}</td><td>{formatCurriculumSemester(item)}</td><td>{item.sgpa != null ? Number(item.sgpa).toFixed(2) : '—'}</td><td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || '—'}</span></td></tr>
                                )
                            ))}
                        </tbody>
                        {tab === 'results' && filtered.length > 0 && (
                            <tfoot>
                                <tr style={{ fontWeight: 600, background: 'var(--surface-alt, #f4f6f9)' }}>
                                    <td colSpan={2} style={{ textAlign: 'right' }}>Cumulative CGPA (best attempt per course)</td>
                                    <td>{(() => {
                                        const latest = [...results].sort((a, b) => (b.result_id || 0) - (a.result_id || 0))[0];
                                        return latest?.cgpa != null ? Number(latest.cgpa).toFixed(2) : '—';
                                    })()}</td>
                                    <td>—</td>
                                </tr>
                            </tfoot>
                        )}
                        {tab === 'assessments' && filteredAssessments.length > 0 && (
                            <tfoot>
                                <tr style={{ fontWeight: 600, background: 'var(--surface-alt, #f4f6f9)' }}>
                                    <td colSpan={3} style={{ textAlign: 'right' }}>Total points (weightage)</td>
                                    <td>—</td>
                                    <td>{fmtScore(assessmentTotals.points)} / {fmtScore(assessmentTotals.max || 100)}</td>
                                    <td>{assessmentTotals.max >= 100 ? '100%' : 'PARTIAL'}</td>
                                </tr>
                            </tfoot>
                        )}
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
        </div>
    );
};

export const MyAttendancePage = () => {
    const { token } = useAuth();
    const [summaries, setSummaries] = useState([]);
    const [courseOptions, setCourseOptions] = useState([]);
    const [selectedOffering, setSelectedOffering] = useState('');
    const [loading, setLoading] = useState(true);

    const buildCourseOptions = (enrollmentData) => {
        const regs = flattenActiveEnrollments(enrollmentData)
            .filter(r => r.offering)
            .map(r => ({
                offering_id: r.offering,
                course_code: r.course_code,
                course_name: r.course_name,
                semester_name: r.semester_name,
            }));
        const seen = new Set();
        return regs.filter(r => {
            if (seen.has(r.offering_id)) return false;
            seen.add(r.offering_id);
            return true;
        });
    };

    useEffect(() => {
        if (!token) return;
        Promise.all([
            myAttendanceSummary(token),
            myEnrollments(token),
        ]).then(([att, en]) => {
            const list = Array.isArray(att) ? att : (att ? [att] : []);
            setSummaries(list);
            const options = buildCourseOptions(en);
            setCourseOptions(options);
            if (options.length > 0) setSelectedOffering(String(options[0].offering_id));
        }).catch(console.error).finally(() => setLoading(false));
    }, [token]);

    useEffect(() => {
        if (!token || !selectedOffering) return;
        myAttendanceSummary(token, selectedOffering).then(d => {
            setSummaries(Array.isArray(d) ? d : (d ? [d] : []));
        }).catch(console.error);
    }, [token, selectedOffering]);

    const current = summaries[0] || {};
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > ATTENDANCE" title="My Attendance" />
            {courseOptions.length > 0 && (
                <div className="field-group" style={{ marginBottom: '16px', maxWidth: '320px' }}>
                    <label className="field-label">Select Subject</label>
                    <select className="field-input field-select" value={selectedOffering} onChange={e => setSelectedOffering(e.target.value)}>
                        {courseOptions.map(e => (
                            <option key={e.offering_id} value={e.offering_id}>{e.course_code} — {e.course_name}</option>
                        ))}
                    </select>
                </div>
            )}
            <div className="stats-grid">
                <div className="stat-card"><div className="stat-header"><div className="stat-info"><span className="stat-label">Attended</span><h3 className="stat-value">{current.attended_lectures ?? 0}</h3></div></div></div>
                <div className="stat-card"><div className="stat-header"><div className="stat-info"><span className="stat-label">Total Lectures</span><h3 className="stat-value">{current.total_lectures ?? 0}</h3></div></div></div>
                <div className="stat-card"><div className="stat-header"><div className="stat-info"><span className="stat-label">Percentage</span><h3 className="stat-value">{current.attendance_percentage != null ? `${Number(current.attendance_percentage).toFixed(1)}%` : '—'}</h3></div></div></div>
                <div className="stat-card"><div className="stat-header"><div className="stat-info"><span className="stat-label">Leave Count</span><h3 className="stat-value">{current.leave_count ?? 0}</h3></div></div></div>
            </div>
            {summaries.length > 1 && (
                <div className="form-card" style={{ marginTop: '20px' }}>
                    <div className="data-table-wrapper">
                        <table className="data-table">
                            <thead><tr><th>Course</th><th>Attended</th><th>Total</th><th>%</th></tr></thead>
                            <tbody>
                                {summaries.map((s, i) => (
                                    <tr key={i}><td>{s.course_code}</td><td>{s.attended_lectures}</td><td>{s.total_lectures}</td><td>{Number(s.attendance_percentage).toFixed(1)}%</td></tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export const MyFeesPage = () => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(null);

    useEffect(() => {
        if (!token) return;
        myChallans(token).then(d => setItems(normalizeList(d))).catch(console.error).finally(() => setLoading(false));
    }, [token]);

    const handleDownload = async (challanId, challanNumber) => {
        setDownloading(challanId);
        try {
            const res = await downloadMyChallan(challanId, token);
            const blob = new Blob([res.data], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Semester-Challan-${challanNumber || challanId}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('Failed to download challan PDF');
        } finally {
            setDownloading(null);
        }
    };

    const { paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(items, ['fee_type']);
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > FEES" title="My Fee Challans" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                Download your semester challan and pay at the university finance office. Finance will confirm payment — no upload needed.
            </p>
            <div className="form-card">
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Semester</th><th>Amount</th><th>Due Date</th><th>Status</th><th>Action</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={6} icon={<FileIcon />} title="No challans" /> : paginated.map((item, i) => (
                                <tr key={item.challan_id || i}>
                                    <td>{(page-1)*pageSize+i+1}</td>
                                    <td>{formatCurriculumSemester(item)}</td>
                                    <td>{item.total_amount ?? item.amount ?? '—'}</td>
                                    <td>{formatDate(item.due_date)}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase() || 'PENDING'}</span></td>
                                    <td>
                                        <button type="button" className="btn-secondary small" disabled={downloading === item.challan_id}
                                            onClick={() => handleDownload(item.challan_id, item.challan_number)}>
                                            {downloading === item.challan_id ? '...' : 'Download PDF'}
                                        </button>
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

export const MyProfilePage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [profileLocked, setProfileLocked] = useState(false);
    const [registrationNumber, setRegistrationNumber] = useState('');
    const [programName, setProgramName] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [profileForm, setProfileForm] = useState({
        blood_group: 'A+',
        medical_conditions: '',
        disabilities: '',
        guardian_phone: '',
        guardian_occupation: '',
        residential_address: '',
    });

    useEffect(() => {
        if (!token) return;
        getMyStudentProfile(token).then(d => {
            const prof = d.profile || {};
            setRegistrationNumber(d.registration_number || '');
            setProgramName(d.program_name || '');
            setProfileLocked(!!prof.profile_locked);
            setProfileForm({
                blood_group: prof.blood_group || 'A+',
                medical_conditions: prof.medical_conditions || '',
                disabilities: prof.disabilities || '',
                guardian_phone: prof.guardian_phone || '',
                guardian_occupation: prof.guardian_occupation || '',
                residential_address: prof.residential_address || prof.permanent_address || '',
            });
        }).catch(console.error).finally(() => setLoading(false));
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (profileLocked) return;
        if (!profileForm.blood_group || !profileForm.guardian_phone || !profileForm.guardian_occupation || !profileForm.residential_address) {
            alert('Please fill in all required fields.');
            return;
        }
        setSubmitting(true);
        try {
            await updateMyStudentProfile(profileForm, token);
            showToast('Profile updated');
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update profile');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > PROFILE" title="My Profile" />
            {profileLocked && (
                <div className="form-card" style={{ marginBottom: 16, borderLeft: '4px solid #f59e0b', padding: '12px 16px' }}>
                    <strong>Profile locked.</strong> Your details are read-only. Contact the admin office to request changes.
                </div>
            )}
            <div className="form-card" style={{ maxWidth: 750 }}>
                <div style={{ marginBottom: 16, color: 'var(--text-secondary)' }}>
                    <p><strong>Registration #:</strong> {registrationNumber || '—'}</p>
                    <p><strong>Program:</strong> {programName || '—'}</p>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="two-column-grid" style={{ marginBottom: 20 }}>
                        <div className="field-group">
                            <label className="field-label">Blood Group <span className="required">*</span></label>
                            <select className="field-input field-select" disabled={profileLocked} value={profileForm.blood_group}
                                onChange={e => setProfileForm({ ...profileForm, blood_group: e.target.value })}>
                                {['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
                            </select>
                        </div>
                        <div className="field-group">
                            <label className="field-label">Guardian Phone <span className="required">*</span></label>
                            <input type="text" className="field-input" disabled={profileLocked} value={profileForm.guardian_phone}
                                onChange={e => setProfileForm({ ...profileForm, guardian_phone: e.target.value })} required />
                        </div>
                        <div className="field-group">
                            <label className="field-label">Guardian Occupation <span className="required">*</span></label>
                            <input type="text" className="field-input" disabled={profileLocked} value={profileForm.guardian_occupation}
                                onChange={e => setProfileForm({ ...profileForm, guardian_occupation: e.target.value })} required />
                        </div>
                        <div className="field-group">
                            <label className="field-label">Residential Address <span className="required">*</span></label>
                            <input type="text" className="field-input" disabled={profileLocked} value={profileForm.residential_address}
                                onChange={e => setProfileForm({ ...profileForm, residential_address: e.target.value })} required />
                        </div>
                        <div className="field-group">
                            <label className="field-label">Medical Conditions</label>
                            <input type="text" className="field-input" disabled={profileLocked} value={profileForm.medical_conditions}
                                onChange={e => setProfileForm({ ...profileForm, medical_conditions: e.target.value })} />
                        </div>
                        <div className="field-group">
                            <label className="field-label">Disabilities</label>
                            <input type="text" className="field-input" disabled={profileLocked} value={profileForm.disabilities}
                                onChange={e => setProfileForm({ ...profileForm, disabilities: e.target.value })} />
                        </div>
                    </div>
                    {!profileLocked && (
                        <button type="submit" className="btn-primary" disabled={submitting}>
                            {submitting ? 'Saving...' : 'Save Profile'}
                        </button>
                    )}
                </form>
            </div>
        </div>
    );
};

export const MyComplaintsPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [selectedComplaint, setSelectedComplaint] = useState(null);
    const [complaintThread, setComplaintThread] = useState(null);
    const [feedbackForm, setFeedbackForm] = useState({ rating: 5, comments: '' });
    const [formData, setFormData] = useState({ subject: '', description: '', category: '' });
    const load = () => myComplaints(token).then(d => setItems(normalizeList(d)));
    useEffect(() => {
        if (!token) return;
        Promise.all([
            load(),
            listCategories(token).then(d => setCategories(normalizeList(d))).catch(() => []),
        ]).finally(() => setLoading(false));
    }, [token]);
    const { paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(items, ['subject']);
    const handleDelete = async (id) => {
        if (!confirm('Delete this complaint?')) return;
        try {
            await deleteComplaint(id, token);
            showToast('Complaint deleted');
            if (selectedComplaint?.complaint_id === id) setSelectedComplaint(null);
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to delete complaint');
        }
    };

    const handleView = async (item) => {
        try {
            const [detail, thread] = await Promise.all([
                getComplaint(item.complaint_id, token),
                getComplaintThread(item.complaint_id, token).catch(() => null),
            ]);
            setSelectedComplaint(detail);
            setComplaintThread(thread);
        } catch {
            setSelectedComplaint(item);
            setComplaintThread(null);
        }
    };

    const handleSubmit = async () => {
        const subject = formData.subject.trim();
        const description = formData.description.trim();
        if (!subject || !description) {
            alert('Please fill in subject and description.');
            return;
        }
        if (subject.length < 3) {
            alert('Subject must be at least 3 characters.');
            return;
        }
        if (description.length < 10) {
            alert('Description must be at least 10 characters.');
            return;
        }
        if (!formData.category) {
            alert('Please select a complaint category.');
            return;
        }
        try {
            await submitComplaint({
                subject,
                description,
                category: parseInt(formData.category, 10),
            }, token);
            showToast('Complaint submitted');
            setShowModal(false);
            setFormData({ subject: '', description: '', category: '' });
            load();
        } catch (e) {
            const msg = e.response?.data?.category?.[0]
                || e.response?.data?.error
                || Object.values(e.response?.data || {}).flat().join(', ')
                || 'Failed to submit complaint';
            alert(msg);
        }
    };
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > COMPLAINTS" title="My Complaints" />
            <div className="form-card">
                <div className="table-toolbar"><button className="btn-add" onClick={() => setShowModal(true)}><PlusIcon /> Submit Complaint</button></div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Subject</th><th>Category</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={6} icon={<BellIcon size={20} />} title="No complaints" /> : paginated.map((item, i) => (
                                <tr key={item.complaint_id || i} style={{ cursor: 'pointer' }} onClick={() => handleView(item)}>
                                    <td>{(page-1)*pageSize+i+1}</td><td>{item.subject}</td><td>{item.category_name || '—'}</td><td>{formatDate(item.created_at || item.submitted_at)}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status === 'in_progress' ? 'UNDER REVIEW' : item.status?.toUpperCase() || 'OPEN'}</span></td>
                                    <td onClick={e => e.stopPropagation()}>
                                        {!['resolved', 'rejected', 'closed'].includes(item.status) && (
                                            <button className="action-btn danger" onClick={() => handleDelete(item.complaint_id)}><TrashIcon /></button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>
            <ModalPortal
                isOpen={!!selectedComplaint}
                render={() => (
                <div className="modal-overlay" onClick={() => { setSelectedComplaint(null); setComplaintThread(null); }}>
                <div className="glass-modal glass-modal-lg" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h3>{selectedComplaint.subject}</h3><button type="button" className="close-btn" onClick={() => { setSelectedComplaint(null); setComplaintThread(null); }}><XIcon /></button></div>
                    <div className="modal-body">
                        <p><strong>Status:</strong> {selectedComplaint.status === 'in_progress' ? 'Under Review' : selectedComplaint.status}</p>
                        <p style={{ marginTop: '12px' }}><strong>Your Message:</strong></p>
                        <p style={{ color: 'var(--text-secondary)' }}>{selectedComplaint.description}</p>
                        {(complaintThread?.messages || []).length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <p><strong>Messages</strong></p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                                    {(complaintThread.messages || []).map(msg => (
                                        <div key={msg.message_id} style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-medium)' }}>
                                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{msg.sender_username || 'User'} <span style={{ fontWeight: 400, color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{formatDate(msg.sent_at)}</span></div>
                                            <div>{msg.message_text}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {selectedComplaint.admin_response && !(complaintThread?.messages || []).some(m => m.message_text === selectedComplaint.admin_response) && (
                            <>
                                <p style={{ marginTop: '16px' }}><strong>Admin Response:</strong></p>
                                <p style={{ color: 'var(--text-secondary)', padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>{selectedComplaint.admin_response}</p>
                            </>
                        )}
                        {['resolved', 'rejected', 'closed'].includes(selectedComplaint.status) && (
                            selectedComplaint.has_feedback ? (
                                <p style={{ marginTop: 16, color: 'var(--text-secondary)' }}>Thank you — your feedback has already been submitted.</p>
                            ) : (
                            <div style={{ marginTop: 16 }}>
                                <p><strong>Rate this resolution</strong></p>
                                <div className="field-group">
                                    <label className="field-label">Rating (1–5)</label>
                                    <input type="number" min={1} max={5} className="field-input" style={{ maxWidth: 80 }} value={feedbackForm.rating} onChange={e => setFeedbackForm({ ...feedbackForm, rating: parseInt(e.target.value, 10) || 5 })} />
                                </div>
                                <div className="field-group">
                                    <label className="field-label">Comments</label>
                                    <textarea className="field-input field-textarea" value={feedbackForm.comments} onChange={e => setFeedbackForm({ ...feedbackForm, comments: e.target.value })} />
                                </div>
                                <button type="button" className="btn-primary" onClick={async () => {
                                    try {
                                        await submitFeedback(selectedComplaint.complaint_id, { rating: feedbackForm.rating, comments: feedbackForm.comments }, token);
                                        showToast('Feedback submitted');
                                        setSelectedComplaint({ ...selectedComplaint, has_feedback: true });
                                        load();
                                    } catch (e) {
                                        const msg = e.response?.data?.error
                                            || e.response?.data?.rating?.[0]
                                            || Object.values(e.response?.data || {}).flat().join(', ')
                                            || 'Failed to submit feedback';
                                        alert(msg);
                                    }
                                }}>Submit Feedback</button>
                            </div>
                            )
                        )}
                    </div>
                </div></div>
                )}
            />

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}><div className="glass-modal" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h3>Submit Complaint</h3><button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button></div>
                    <div className="modal-body">
                        <div className="field-group"><label className="field-label">Subject</label><input className="field-input" value={formData.subject} onChange={e => setFormData({ ...formData, subject: e.target.value })} /></div>
                        <div className="field-group"><label className="field-label">Description</label><textarea className="field-input field-textarea" value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} /></div>
                        <div className="field-group"><label className="field-label">Category</label>
                            <select className="field-input field-select" value={formData.category} onChange={e => setFormData({ ...formData, category: e.target.value })}>
                                <option value="">Select category</option>
                                {categories.map(c => (
                                    <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
                                ))}
                            </select>
                            {categories.length === 0 && (
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '6px' }}>
                                    No categories found. Ask admin to run seed_erp_data.
                                </p>
                            )}
                        </div>
                    </div>
                    <div className="modal-footer"><button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button><button className="btn-primary" onClick={handleSubmit}>Submit</button></div>
                </div></div>
            )} />
        </div>
    );
};

export const MyNotificationsPage = () => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);
    const load = () => listNotifications(token).then(d => setItems(normalizeList(d)));
    useEffect(() => { if (token) load().finally(() => setLoading(false)); }, [token]);
    const { paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(items, ['title', 'message']);
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
            <PageHeader breadcrumb="DASHBOARD > NOTIFICATIONS" title="My Notifications" />
            <div style={{ marginBottom: 12 }}>
                <button type="button" className="btn-secondary small" onClick={handleMarkAllRead}>Mark all as read</button>
            </div>
            <div className="form-card">
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Title</th><th>Preview</th><th>Date</th><th>Read</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? <EmptyRow colSpan={5} icon={<BellIcon size={20} />} title="No notifications" /> : paginated.map((item, i) => (
                                <tr key={item.notification_id || i} style={{ cursor: 'pointer' }} onClick={() => openNotification(item)}>
                                    <td>{(page-1)*pageSize+i+1}</td>
                                    <td>{item.title || item.subject || '—'}</td>
                                    <td>{(item.message || '').substring(0, 60)}{(item.message || '').length > 60 ? '...' : ''}</td>
                                    <td>{formatDate(item.created_at)}</td>
                                    <td>{item.is_read ? 'Yes' : 'No'}</td>
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
                        <div className="modal-body">
                            <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>{formatDate(selected?.created_at)}</p>
                            <p style={{ whiteSpace: 'pre-wrap' }}>{selected?.message || '—'}</p>
                        </div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export const MyAnnouncementsPage = () => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        if (!token) return;
        listAnnouncements(token).then(d => setItems(normalizeList(d))).catch(console.error).finally(() => setLoading(false));
    }, [token]);
    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            <PageHeader breadcrumb="DASHBOARD > ANNOUNCEMENTS" title="Campus Announcements" />
            <div className="form-card">
                {items.length === 0 ? (
                    <p style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>No announcements</p>
                ) : items.map((item, i) => (
                    <div key={item.announcement_id || i} style={{ padding: '16px', borderBottom: '1px solid var(--border-color)' }}>
                        <h4 style={{ margin: '0 0 8px' }}>{item.title}</h4>
                        <p style={{ color: 'var(--text-secondary)', margin: '0 0 8px' }}>{item.content}</p>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>{formatDate(item.published_date || item.created_at)} · {item.announcement_type}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export const MyLeavesPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [courseOptions, setCourseOptions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ offering: '', start_date: '', end_date: '', reason: '' });
    const todayStr = new Date().toISOString().split('T')[0];

    const loadCourses = () => myEnrollments(token).then((d) => {
        const regs = flattenActiveEnrollments(d)
            .filter(r => r.offering)
            .map(r => ({
                offering_id: r.offering,
                course_code: r.course_code,
                course_name: r.course_name,
                faculty_name: r.faculty_name,
                semester_name: r.semester_name,
            }));
        const seen = new Set();
        const unique = regs.filter(r => {
            if (seen.has(r.offering_id)) return false;
            seen.add(r.offering_id);
            return true;
        });
        setCourseOptions(unique);
    }).catch(() => setCourseOptions([]));

    const load = () => myLeaves(token).then(d => setItems(normalizeList(d)));
    useEffect(() => {
        if (!token) return;
        Promise.all([load(), loadCourses()]).finally(() => setLoading(false));
    }, [token]);

    const handleSubmit = async () => {
        if (!form.offering || !form.start_date || !form.end_date || !form.reason.trim()) {
            alert('Course, dates, and reason are required.');
            return;
        }
        if (form.start_date < todayStr || form.end_date < todayStr) {
            alert('Start and end dates cannot be before today.');
            return;
        }
        if (form.end_date < form.start_date) {
            alert('End date must be on or after start date.');
            return;
        }
        try {
            await submitLeave({
                offering: parseInt(form.offering, 10),
                start_date: form.start_date,
                end_date: form.end_date,
                reason: form.reason,
            }, token);
            showToast('Leave application submitted');
            setShowModal(false);
            setForm({ offering: '', start_date: '', end_date: '', reason: '' });
            load();
        } catch (e) {
            alert(e.response?.data?.error || e.response?.data?.offering?.[0] || Object.values(e.response?.data || {}).flat().join(', ') || 'Failed to submit leave');
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this leave application?')) return;
        try {
            await deleteLeave(id, token);
            showToast('Leave deleted');
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to delete');
        }
    };

    if (loading) return <LoadingSpinner />;
    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > LEAVES" title="Leave Applications" />
            <div className="form-card">
                <div className="table-toolbar"><button className="btn-add" onClick={() => setShowModal(true)}><PlusIcon /> Apply for Leave</button></div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Course</th><th>Dates</th><th>Reason</th><th>Status</th><th>Action</th></tr></thead>
                        <tbody>
                            {items.length === 0 ? <EmptyRow colSpan={6} title="No leave applications" /> : items.map((item, i) => (
                                <tr key={item.leave_id}>
                                    <td>{i + 1}</td>
                                    <td>{item.course_code}{item.course_name ? ` — ${item.course_name}` : ''}</td>
                                    <td>{formatDate(item.start_date)} – {formatDate(item.end_date)}</td>
                                    <td>{item.reason}</td>
                                    <td><span className={getStatusBadgeClass(item.status)}>{item.status?.toUpperCase()}</span></td>
                                    <td>{['pending', 'rejected'].includes(item.status) && <button className="action-btn danger" onClick={() => handleDelete(item.leave_id)}><TrashIcon /></button>}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h3>Apply for Leave</h3><button type="button" className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button></div>
                    <div className="modal-body">
                        <div className="field-group">
                            <label className="field-label">Course <span className="required">*</span></label>
                            <select
                                className="field-input field-select"
                                value={form.offering}
                                onChange={e => setForm({ ...form, offering: e.target.value })}
                            >
                                <option value="">Select course</option>
                                {courseOptions.map(c => (
                                    <option key={c.offering_id} value={c.offering_id}>
                                        {c.course_code} — {c.course_name}{c.faculty_name ? ` (${c.faculty_name})` : ''}
                                    </option>
                                ))}
                            </select>
                            {courseOptions.length === 0 && (
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '6px' }}>
                                    No registered courses found. Enroll in courses before applying for leave.
                                </p>
                            )}
                        </div>
                        <div className="two-column-grid">
                            <div className="field-group"><label className="field-label">Start Date</label><input type="date" className="field-input" min={todayStr} value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></div>
                            <div className="field-group"><label className="field-label">End Date</label><input type="date" className="field-input" min={form.start_date || todayStr} value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></div>
                        </div>
                        <div className="field-group"><label className="field-label">Reason</label><textarea className="field-input field-textarea" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} /></div>
                    </div>
                    <div className="modal-footer"><button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button><button type="button" className="btn-primary" onClick={handleSubmit}>Submit</button></div>
                    </div>
                </div>
            )} />
        </div>
    );
};
