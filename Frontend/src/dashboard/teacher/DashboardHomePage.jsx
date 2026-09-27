import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getMyOfferings } from '../../services/offeringsService';
import { getTeacherAcademicWarnings } from '../../services/enrollmentsService';
import { listExaminations } from '../../services/examinationsService';
import { listAttendance } from '../../services/attendanceService';
import { listNotifications } from '../../services/notificationsService';
import { normalizeList } from '../../services/api';
import { CheckIcon, BookIcon, ClipboardIcon, FileIcon, BellIcon, ArrowRightIcon } from '../Icons';

const TeacherDashboardHomePage = ({ onNavigate }) => {
    const { token, user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState([]);
    const [warnings, setWarnings] = useState(null);

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            setLoading(true);
            try {
                const [offerings, exams, att, notifs, warn] = await Promise.allSettled([
                    getMyOfferings(token, 'active=true'), listExaminations(token), listAttendance(token), listNotifications(token),
                    getTeacherAcademicWarnings(token),
                ]);
                const count = (r) => r.status === 'fulfilled' ? normalizeList(r.value).length : 0;
                setStats([
                    { label: 'My Courses', value: count(offerings).toString(), icon: <BookIcon size={20} />, color: '#3b82f6', bg: '#eff6ff' },
                    { label: 'Examinations', value: count(exams).toString(), icon: <FileIcon />, color: '#10b981', bg: '#f0fdf4' },
                    { label: 'Attendance Records', value: count(att).toString(), icon: <ClipboardIcon size={20} />, color: '#f59e0b', bg: '#fffbeb' },
                    { label: 'Notifications', value: count(notifs).toString(), icon: <BellIcon size={20} />, color: '#4169E1', bg: '#eef2ff' },
                ]);
                if (warn.status === 'fulfilled') setWarnings(warn.value);
            } catch (e) { console.error(e); }
            finally { setLoading(false); }
        };
        load();
    }, [token]);

    if (loading) return <div className="home-dashboard fade-in"><div className="loading-spinner">Loading dashboard...</div></div>;

    return (
        <div className="home-dashboard fade-in">
            <div className="welcome-banner fade-up">
                <div className="welcome-text">
                    <h1>Welcome Back, <span className="highlight-text-welcome">{user?.username || 'Teacher'}</span> 👋</h1>
                    <p>Manage your courses, mark attendance, enter exam marks, and stay updated with campus notifications.</p>
                </div>
            </div>
            <div className="stats-grid">
                {stats.map((stat, i) => (
                    <div key={i} className="stat-card fade-up">
                        <div className="stat-header">
                            <div className="stat-icon-wrapper" style={{ backgroundColor: stat.bg, color: stat.color }}>{stat.icon}</div>
                            <div className="stat-info"><span className="stat-label">{stat.label}</span><h3 className="stat-value">{stat.value}</h3></div>
                        </div>
                    </div>
                ))}
            </div>

            {warnings && ((warnings.pending_final_grades || []).length > 0 || (warnings.blocking_promotion || []).length > 0 || (warnings.incomplete_weight_allocations || []).length > 0) && (
                <div className="form-card fade-up" style={{ marginBottom: 20 }}>
                    <h3 className="section-title" style={{ marginBottom: 12, color: '#b45309' }}>Academic Workflow Alerts</h3>
                    {(warnings.incomplete_weight_allocations || []).map(w => (
                        <div key={`weight-${w.offering_id}`} style={{ padding: 12, marginBottom: 8, background: '#fef2f2', borderRadius: 8, border: '1px solid #fca5a5' }}>
                            <p style={{ margin: 0, fontWeight: 600, color: '#dc2626' }}>{w.course_code} — {w.course_name}</p>
                            <p style={{ margin: '4px 0 0', fontSize: '0.875rem' }}>{w.message}</p>
                        </div>
                    ))}
                    {(warnings.pending_final_grades || []).map(w => (
                        <div key={w.offering_id} style={{ padding: 12, marginBottom: 8, background: '#fffbeb', borderRadius: 8, border: '1px solid #fcd34d' }}>
                            <p style={{ margin: 0, fontWeight: 600 }}>{w.course_code} — {w.course_name}</p>
                            <p style={{ margin: '4px 0 0', fontSize: '0.875rem' }}>Students waiting for grades: {w.students_waiting}</p>
                            {!w.weight_complete && (
                                <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: '#dc2626' }}>Complete 100% assessment weightage first.</p>
                            )}
                        </div>
                    ))}
                    {(warnings.blocking_promotion || []).map(w => (
                        <div key={`block-${w.offering_id}`} style={{ padding: 12, marginBottom: 8, background: '#fef2f2', borderRadius: 8, border: '1px solid #fca5a5' }}>
                            <p style={{ margin: 0, fontWeight: 600, color: '#dc2626' }}>{w.message}</p>
                        </div>
                    ))}
                </div>
            )}

            <div className="home-section quick-links-section fade-up">
                <div className="section-header"><div className="section-header-icon"><ArrowRightIcon /></div><h2 className="section-title">Quick Actions</h2></div>
                <div className="quick-links-grid">
                    <button className="quick-link-btn" onClick={() => onNavigate('courses')}><div className="quick-link-icon"><BookIcon size={20} /></div><span>My Courses</span></button>
                    <button className="quick-link-btn" onClick={() => onNavigate('attendance')}><div className="quick-link-icon"><ClipboardIcon size={20} /></div><span>Mark Attendance</span></button>
                    <button className="quick-link-btn" onClick={() => onNavigate('examinations')}><div className="quick-link-icon"><FileIcon /></div><span>Examinations</span></button>
                </div>
            </div>
        </div>
    );
};

export default TeacherDashboardHomePage;
