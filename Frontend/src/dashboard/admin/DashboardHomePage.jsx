import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getDashboardStats } from '../../services/dashboardService';
import { listSemesters } from '../../services/academicsService';
import { listNotifications } from '../../services/notificationsService';
import { normalizeList } from '../../services/api';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { UserIcon, BookIcon, ClipboardIcon, FileIcon, BellIcon } from '../Icons';

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

const AdminDashboardHomePage = ({ onNavigate }) => {
    const { token, user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [semesters, setSemesters] = useState([]);
    const [semesterId, setSemesterId] = useState('');
    const [stats, setStats] = useState(null);
    const [unreadNotifs, setUnreadNotifs] = useState(0);
    const didInitSemester = useRef(false);

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const params = semesterId ? `?semester=${semesterId}` : '';
            const [data, sem, notifs] = await Promise.all([
                getDashboardStats(token, params),
                listSemesters(token),
                listNotifications(token),
            ]);
            setStats(data);
            setUnreadNotifs(normalizeList(notifs).filter(n => !n.is_read).length);
            const semList = Array.isArray(sem) ? sem : (sem?.results || sem || []);
            setSemesters(semList);
            if (!didInitSemester.current && !semesterId && data?.semester?.semester_id) {
                didInitSemester.current = true;
                setSemesterId(String(data.semester.semester_id));
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [token, semesterId]);

    useEffect(() => {
        if (token) load();
    }, [token, semesterId]);

    if (loading && !stats) {
        return <div className="home-dashboard fade-in"><div className="loading-spinner">Loading dashboard...</div></div>;
    }

    const summary = stats?.summary || {};
    const statCards = [
        { label: 'Active Students', value: summary.students ?? 0, icon: <UserIcon size={20} />, color: '#3b82f6', bg: '#eff6ff' },
        { label: 'Faculty', value: summary.faculty ?? 0, icon: <BookIcon size={20} />, color: '#10b981', bg: '#f0fdf4' },
        { label: 'Course Assignments', value: summary.course_assignments ?? summary.course_offerings ?? 0, icon: <ClipboardIcon />, color: '#f59e0b', bg: '#fffbeb' },
        { label: 'Course Registrations', value: summary.enrollments ?? 0, icon: <FileIcon />, color: '#4169E1', bg: '#eef2ff' },
        { label: 'Open Complaints', value: summary.complaints_open ?? 0, icon: <BellIcon size={20} />, color: '#ef4444', bg: '#fef2f2' },
        { label: 'Pending Challans', value: summary.challans_pending ?? 0, icon: <FileIcon />, color: '#fbbf24', bg: '#fffbeb' },
        { label: 'Unread Notifications', value: unreadNotifs, icon: <BellIcon size={20} />, color: '#06b6d4', bg: '#ecfeff', nav: 'notifications' },
    ];

    const programData = (stats?.students_by_program || []).map(r => ({
        name: r.program_code || r.program_name?.slice(0, 12) || '—',
        fullName: r.program_name,
        count: r.count,
    }));

    const semesterData = (stats?.students_by_semester || []).map(r => ({
        name: `Sem ${r.semester}`,
        count: r.count,
    }));

    const courseData = (stats?.enrollments_by_course || []).slice(0, 10).map(r => ({
        name: r.course_code,
        fullName: r.course_name,
        count: r.count,
    }));

    const facultyLoad = stats?.faculty_load || [];

    return (
        <div className="home-dashboard fade-in">
            <div className="welcome-banner fade-up">
                <div className="welcome-text">
                    <h1>Welcome Back, <span className="highlight-text-welcome">{user?.username || 'Admin'}</span></h1>
                    <p>University overview — students, programs, enrollments, and faculty workload.</p>
                </div>
                <div style={{ marginLeft: 'auto', minWidth: 200 }}>
                    <select
                        className="field-input field-select"
                        value={semesterId}
                        onChange={e => setSemesterId(e.target.value)}
                    >
                        <option value="">Current enrollments</option>
                        {semesters.filter(s => s.is_current).map(s => (
                            <option key={s.semester_id} value={s.semester_id}>
                                Active Session
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="stats-grid">
                {statCards.map((stat, i) => (
                    <div key={i} className="stat-card fade-up" style={{ animationDelay: `${0.05 * (i + 1)}s` }}>
                        <div className="stat-header">
                            <div className="stat-icon-wrapper" style={{ backgroundColor: stat.bg, color: stat.color }}>{stat.icon}</div>
                            <div className="stat-info">
                                <span className="stat-label">{stat.label}</span>
                                <h3 className="stat-value">{Number(stat.value).toLocaleString()}</h3>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="dashboard-charts-grid">
                <div className="form-card dashboard-chart-card">
                    <h3 className="chart-title">Students by Program</h3>
                    {programData.length === 0 ? (
                        <p className="chart-empty">No active students</p>
                    ) : (
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={programData} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light, #e5e7eb)" />
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" height={60} />
                                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                                <Tooltip formatter={(v, _n, p) => [v, p.payload.fullName || p.payload.name]} />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                    {programData.map((_, i) => (
                                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>

                <div className="form-card dashboard-chart-card">
                    <h3 className="chart-title">Students by Curriculum Semester</h3>
                    {semesterData.length === 0 ? (
                        <p className="chart-empty">No data</p>
                    ) : (
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={semesterData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light, #e5e7eb)" />
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </div>

            <div className="dashboard-charts-grid">
                <div className="form-card dashboard-chart-card">
                    <h3 className="chart-title">
                        Top Courses by Enrollment
                    </h3>
                    {courseData.length === 0 ? (
                        <p className="chart-empty">No enrollments for selected semester</p>
                    ) : (
                        <ResponsiveContainer width="100%" height={Math.max(240, courseData.length * 36)}>
                            <BarChart data={courseData} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light, #e5e7eb)" />
                                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                                <YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 11 }} />
                                <Tooltip formatter={(v, _n, p) => [v, p.payload.fullName || p.payload.name]} />
                                <Bar dataKey="count" fill="#4169E1" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>

                <div className="form-card dashboard-chart-card">
                    <h3 className="chart-title">
                        Faculty Course Load
                    </h3>
                    {facultyLoad.length === 0 ? (
                        <p className="chart-empty">No course assignments</p>
                    ) : (
                        <div className="data-table-wrapper" style={{ maxHeight: 320, overflowY: 'auto' }}>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Faculty</th>
                                        <th>Courses</th>
                                        <th>Students</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {facultyLoad.map((row, i) => (
                                        <tr key={i}>
                                            <td>{row.faculty_name}</td>
                                            <td>{row.course_count}</td>
                                            <td>{row.total_enrolled}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            <div className="home-content-bottom">
                <div className="home-section quick-links-section fade-up">
                    <div className="section-header">
                        <h2 className="section-title">Quick Actions</h2>
                    </div>
                    <div className="quick-links-grid">
                        <button className="quick-link-btn" onClick={() => onNavigate('students')}><UserIcon size={20} /><span>Students</span></button>
                        <button className="quick-link-btn" onClick={() => onNavigate('teacher-courses')}><ClipboardIcon size={20} /><span>Teacher Courses</span></button>
                        <button className="quick-link-btn" onClick={() => onNavigate('examinations')}><FileIcon /><span>Results & Marks</span></button>
                        <button className="quick-link-btn" onClick={() => onNavigate('enrollments')}><BookIcon size={20} /><span>Enrollments</span></button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AdminDashboardHomePage;
