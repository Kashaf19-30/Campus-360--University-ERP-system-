import React, { useState, useEffect } from 'react';

import { useAuth } from '../../context/AuthContext';

import { myEnrollments, getMyAcademicStatus, flattenActiveEnrollments } from '../../services/enrollmentsService';

import { myFinalGrades, myResults } from '../../services/examinationsService';

import { myAttendanceSummary } from '../../services/attendanceService';

import { myChallans } from '../../services/feesService';

import { myComplaints } from '../../services/complaintsService';

import { listNotifications } from '../../services/notificationsService';

import { getMyStudentProfile, myDegreeProgress } from '../../services/studentsService';

import { normalizeList } from '../../services/api';

import { CheckIcon, UserIcon, BookIcon, ClipboardIcon, FileIcon, BellIcon, ArrowRightIcon } from '../Icons';



const flattenEnrollments = flattenActiveEnrollments;



const StudentDashboardHomePage = ({ onNavigate, isGraduated = false }) => {

    const { token, user } = useAuth();

    const [loading, setLoading] = useState(true);

    const [stats, setStats] = useState([]);

    const [studentInfo, setStudentInfo] = useState(null);
    const [degreeProgress, setDegreeProgress] = useState(null);
    const [academicStatus, setAcademicStatus] = useState(null);



    useEffect(() => {

        const load = async () => {

            if (!token) return;

            setLoading(true);

            try {

                const [enr, grades, att, challans, complaints, notifs, profile, progress, acadStatus] = await Promise.allSettled([

                    isGraduated ? Promise.resolve([]) : myEnrollments(token), myFinalGrades(token), myAttendanceSummary(token),

                    isGraduated ? Promise.resolve([]) : myChallans(token), myComplaints(token), listNotifications(token),

                    getMyStudentProfile(token), myDegreeProgress(token), getMyAcademicStatus(token),

                ]);

                const count = (r) => r.status === 'fulfilled' ? normalizeList(r.value).length : 0;

                const enrData = enr.status === 'fulfilled' ? enr.value : {};

                const courseCount = flattenEnrollments(enrData).length;

                const attData = att.status === 'fulfilled' ? att.value : {};

                if (profile.status === 'fulfilled') setStudentInfo(profile.value);
                if (progress.status === 'fulfilled') setDegreeProgress(progress.value);
                if (acadStatus.status === 'fulfilled') setAcademicStatus(acadStatus.value);

                setStats([

                    ...(isGraduated ? [] : [{ label: 'Enrolled Courses', value: courseCount.toString(), icon: <BookIcon size={20} />, color: '#3b82f6', bg: '#eff6ff' }]),

                    { label: 'Final Grades', value: count(grades).toString(), icon: <CheckIcon />, color: '#10b981', bg: '#f0fdf4' },

                    { label: 'Attendance', value: attData.percentage != null ? `${attData.percentage}%` : '—', icon: <ClipboardIcon size={20} />, color: '#f59e0b', bg: '#fffbeb', progress: attData.percentage || 0 },

                    ...(isGraduated ? [] : [{ label: 'Fee Challans', value: count(challans).toString(), icon: <FileIcon />, color: '#4169E1', bg: '#eef2ff' }]),

                    { label: 'My Complaints', value: count(complaints).toString(), icon: <BellIcon size={20} />, color: '#ef4444', bg: '#fef2f2' },

                    { label: 'Notifications', value: count(notifs).toString(), icon: <BellIcon size={20} />, color: '#06b6d4', bg: '#ecfeff' },

                ]);

            } catch (e) { console.error(e); }

            finally { setLoading(false); }

        };

        load();

    }, [token, isGraduated]);



    if (loading) return <div className="home-dashboard fade-in"><div className="loading-spinner">Loading dashboard...</div></div>;



    return (

        <div className="home-dashboard fade-in">

            <div className="welcome-banner fade-up">

                <div className="welcome-text">

                    <h1>{isGraduated ? 'Congratulations, ' : 'Welcome Back, '}<span className="highlight-text-welcome">{user?.username || 'Student'}</span>{isGraduated ? '!' : ' 👋'}</h1>

                    <p>{isGraduated
                        ? 'You have graduated. View your official transcript, grades, and campus announcements from your alumni portal.'
                        : 'Track your courses, grades, attendance, fees, and campus activities from your student portal.'}</p>

                    {studentInfo && (

                        <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>

                            <span><strong>Program:</strong> {studentInfo.program_name}</span>

                            <span><strong>Reg No:</strong> {studentInfo.registration_number}</span>

                            <span><strong>Batch:</strong> {studentInfo.batch_year}</span>

                            {degreeProgress && (
                                <span><strong>Degree Progress:</strong> {degreeProgress.degree_completion_percent}% ({degreeProgress.earned_credit_hours}/{degreeProgress.total_credit_hours} CH)</span>
                            )}

                        </div>

                    )}

                </div>

            </div>

            {isGraduated && (
                <div className="form-card fade-up" style={{ marginBottom: 20, borderLeft: '4px solid #10b981', background: '#f0fdf4' }}>
                    <h3 className="section-title" style={{ marginBottom: 8 }}>Alumni Status</h3>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                        Your degree is complete. Enrollments, fee payments, and leave applications are no longer available.
                        Download your official transcript from <button type="button" className="link-btn" onClick={() => onNavigate('transcript')}>My Transcript</button>.
                    </p>
                </div>
            )}

            {academicStatus && !isGraduated && (
                <div className="form-card fade-up" style={{ marginBottom: 20 }}>
                    <h3 className="section-title" style={{ marginBottom: 12 }}>Academic Status</h3>
                    <div style={{ display: 'grid', gap: 8, fontSize: '0.9rem' }}>
                        <p><strong>Current Semester:</strong> Semester {academicStatus.current_semester}</p>
                        <p><strong>Semester Status:</strong> {academicStatus.semester_status}</p>
                        <p><strong>Financial Status:</strong> {academicStatus.financial_status}</p>
                        {academicStatus.registration_blocked && (
                            <p style={{ color: '#dc2626', padding: '10px 12px', background: '#fef2f2', borderRadius: 8 }}>
                                <strong>Registration Blocked:</strong> {academicStatus.registration_block_reason}
                            </p>
                        )}
                        {(academicStatus.repeat_courses || []).length > 0 && (
                            <div style={{ marginTop: 8 }}>
                                <strong>Repeat Courses</strong>
                                <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>
                                    {academicStatus.repeat_courses.map(r => (
                                        <li key={r.course_code}>{r.course_code} — {r.status}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="stats-grid">

                {stats.map((stat, i) => (

                    <div key={i} className="stat-card fade-up">

                        <div className="stat-header">

                            <div className="stat-icon-wrapper" style={{ backgroundColor: stat.bg, color: stat.color }}>{stat.icon}</div>

                            <div className="stat-info">

                                <span className="stat-label">{stat.label}</span>

                                <h3 className="stat-value">{stat.value}</h3>

                            </div>

                        </div>

                        {stat.progress !== undefined && stat.progress > 0 && (

                            <div className="stat-progress-container">

                                <div className="stat-progress-bar" style={{ width: `${stat.progress}%`, backgroundColor: stat.color }}></div>

                            </div>

                        )}

                    </div>

                ))}

            </div>

            <div className="home-content-bottom">

                <div className="home-section quick-links-section fade-up">

                    <div className="section-header">

                        <div className="section-header-icon"><ArrowRightIcon /></div>

                        <h2 className="section-title">Quick Actions</h2>

                    </div>

                    <div className="quick-links-grid">

                        {!isGraduated && (
                            <button className="quick-link-btn" onClick={() => onNavigate('enrollments')}><div className="quick-link-icon"><BookIcon size={20} /></div><span>My Enrollments</span></button>
                        )}

                        <button className="quick-link-btn" onClick={() => onNavigate('grades')}><div className="quick-link-icon"><CheckIcon /></div><span>My Grades</span></button>

                        <button className="quick-link-btn" onClick={() => onNavigate('transcript')}><div className="quick-link-icon"><FileIcon /></div><span>My Transcript</span></button>

                        <button className="quick-link-btn" onClick={() => onNavigate('attendance')}><div className="quick-link-icon"><ClipboardIcon size={20} /></div><span>My Attendance</span></button>

                        {!isGraduated && (
                            <button className="quick-link-btn" onClick={() => onNavigate('fees')}><div className="quick-link-icon"><FileIcon /></div><span>My Fees</span></button>
                        )}

                        <button className="quick-link-btn" onClick={() => onNavigate('complaints')}><div className="quick-link-icon"><BellIcon size={20} /></div><span>My Complaints</span></button>

                    </div>

                </div>

            </div>

        </div>

    );

};



export default StudentDashboardHomePage;

