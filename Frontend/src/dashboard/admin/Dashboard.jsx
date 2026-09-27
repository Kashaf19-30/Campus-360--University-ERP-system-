import React, { useMemo } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pageIdFromPath } from '../../routes/paths';
import { useDashboardNavigate } from '../../routes/useDashboardNavigate';
import { useFilteredNavItems } from '../../routes/navPermissions';
import RequirePermission from '../../routes/RequirePermission';
import DashboardLayout from '../shared/DashboardLayout';
import {
    LayoutDashboardIcon, BookIcon, UserIcon, FileTextIcon, ClipboardIcon,
    ShieldIcon, BellIcon
} from '../Icons';
import AdminDashboardHomePage from './DashboardHomePage';
import AcademicsPage from './Pages/AcademicsPage';
import FacultyListingPage from './Pages/FacultyListingPage';
import StudentsListingPage from './Pages/StudentsListingPage';
import EnrollmentsListingPage from './Pages/EnrollmentsListingPage';
import ExaminationsListingPage from './Pages/ExaminationsListingPage';
import AttendanceListingPage from './Pages/AttendanceListingPage';
import NotificationsListingPage from './Pages/NotificationsListingPage';
import ComplaintsListingPage from './Pages/ComplaintsListingPage';
import AdmissionsReviewPage from './Pages/AdmissionsReviewPage';
import CredentialsPage from './Pages/CredentialsPage';
import RepeatRequestsPage from './Pages/RepeatRequestsPage';
import TeacherCourseManagementPage from './Pages/TeacherCourseManagementPage';
import RolePermissionsPage from './Pages/RolePermissionsPage';
import AcademicStandingPage from './Pages/AcademicStandingPage';
import AcademicProgressPage from './Pages/AcademicProgressPage';
import AcademicPolicyPage from './Pages/AcademicPolicyPage';
import GraduationAuditPage from './Pages/GraduationAuditPage';
import FeeStructurePage from './Pages/FeeStructurePage';
import ChangePasswordPage from '../applicant/Pages/ChangePasswordPage';

const ADMIN_BASE = '/admin';

const AdminDashboard = () => {
    const { logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const onNavigate = useDashboardNavigate(ADMIN_BASE);
    const currentPage = pageIdFromPath(location.pathname, ADMIN_BASE);

    const handleLogout = async (e) => {
        e.preventDefault();
        await logout();
        navigate('/');
    };

    const navItems = useMemo(() => [
        { id: 'home', label: 'Dashboard', icon: <LayoutDashboardIcon />, always: true },
        {
            id: 'academics-menu', label: 'Academics', icon: <BookIcon size={20} />,
            permissions: ['academics.view_department', 'academics.view_program', 'academics.view_course'],
            children: [
                { id: 'academics', label: 'Departments & Programs', permissions: ['academics.view_department', 'academics.view_program', 'academics.view_course'] },
                { id: 'academic-policy', label: 'Academic Policy', permission: 'academics.view_program' },
            ]
        },
        { id: 'credentials', label: 'Create Credentials', icon: <ShieldIcon size={20} />, permission: 'accounts.create_credentials' },
        { id: 'faculty', label: 'Faculty', icon: <UserIcon size={20} />, permission: 'faculty.view_faculty' },
        { id: 'teacher-courses', label: 'Teacher Courses', icon: <ClipboardIcon size={20} />, permission: 'faculty.view_faculty' },
        { id: 'admissions', label: 'Admissions', icon: <FileTextIcon />, permission: 'admissions.view_application' },
        { id: 'students', label: 'Students', icon: <UserIcon size={20} />, permission: 'students.view_student' },
        { id: 'academic-standing', label: 'Academic Standing', icon: <ClipboardIcon size={20} />, permission: 'students.view_student' },
        { id: 'academic-progress', label: 'Academic Progress', icon: <ClipboardIcon size={20} />, permission: 'enrollments.view_enrollment' },
        { id: 'graduation-audit', label: 'Graduation Audit', icon: <FileTextIcon size={20} />, permission: 'students.view_student' },
        { id: 'enrollments', label: 'Enrollments', icon: <FileTextIcon />, permission: 'enrollments.view_enrollment' },
        { id: 'repeat-requests', label: 'Repeat Requests', icon: <FileTextIcon />, permission: 'enrollments.view_enrollment' },
        { id: 'examinations', label: 'Results & Marks', icon: <FileTextIcon />, permission: 'examinations.view_examination' },
        { id: 'attendance', label: 'Attendance', icon: <ClipboardIcon size={20} />, permission: 'attendance.view_attendance' },
        { id: 'fee-structures', label: 'Fee Structures', icon: <FileTextIcon />, permission: 'fees.manage_fees' },
        { id: 'notifications', label: 'Notifications', icon: <BellIcon size={20} />, permissions: ['announcements.view_announcement', 'announcements.manage_announcement'] },
        { id: 'complaints', label: 'Complaints', icon: <BellIcon size={20} />, permissions: ['complaints.view_complaint', 'complaints.manage_complaint'] },
        { id: 'role-permissions', label: 'Role Permissions', icon: <ShieldIcon size={20} />, permission: 'system.manage_role_permissions' },
        { id: 'change-password', label: 'Change Password', icon: <ShieldIcon />, always: true },
    ], []);

    const filteredNavItems = useFilteredNavItems(navItems);

    return (
        <DashboardLayout
            roleLabel="Administrator"
            navItems={filteredNavItems}
            currentPage={currentPage}
            onNavigate={onNavigate}
            onLogout={handleLogout}
        >
            <Routes>
                <Route index element={<AdminDashboardHomePage onNavigate={onNavigate} />} />
                <Route path="academics" element={
                    <RequirePermission permissions={['academics.view_department', 'academics.view_program', 'academics.view_course']}>
                        <AcademicsPage />
                    </RequirePermission>
                } />
                <Route path="academic-policy" element={
                    <RequirePermission permission="academics.view_program">
                        <AcademicPolicyPage />
                    </RequirePermission>
                } />
                <Route path="credentials" element={
                    <RequirePermission permission="accounts.create_credentials">
                        <CredentialsPage />
                    </RequirePermission>
                } />
                <Route path="faculty" element={
                    <RequirePermission permission="faculty.view_faculty">
                        <FacultyListingPage />
                    </RequirePermission>
                } />
                <Route path="teacher-courses" element={
                    <RequirePermission permission="faculty.view_faculty">
                        <TeacherCourseManagementPage />
                    </RequirePermission>
                } />
                <Route path="admissions" element={
                    <RequirePermission permission="admissions.view_application">
                        <AdmissionsReviewPage />
                    </RequirePermission>
                } />
                <Route path="students" element={
                    <RequirePermission permission="students.view_student">
                        <StudentsListingPage />
                    </RequirePermission>
                } />
                <Route path="academic-standing" element={
                    <RequirePermission permission="students.view_student">
                        <AcademicStandingPage />
                    </RequirePermission>
                } />
                <Route path="academic-progress" element={
                    <RequirePermission permission="enrollments.view_enrollment">
                        <AcademicProgressPage />
                    </RequirePermission>
                } />
                <Route path="graduation-audit" element={
                    <RequirePermission permission="students.view_student">
                        <GraduationAuditPage />
                    </RequirePermission>
                } />
                <Route path="enrollments" element={
                    <RequirePermission permission="enrollments.view_enrollment">
                        <EnrollmentsListingPage />
                    </RequirePermission>
                } />
                <Route path="repeat-requests" element={
                    <RequirePermission permission="enrollments.view_enrollment">
                        <RepeatRequestsPage />
                    </RequirePermission>
                } />
                <Route path="examinations" element={
                    <RequirePermission permission="examinations.view_examination">
                        <ExaminationsListingPage />
                    </RequirePermission>
                } />
                <Route path="attendance" element={
                    <RequirePermission permission="attendance.view_attendance">
                        <AttendanceListingPage />
                    </RequirePermission>
                } />
                <Route path="fee-structures" element={
                    <RequirePermission permission="fees.manage_fees">
                        <FeeStructurePage />
                    </RequirePermission>
                } />
                <Route path="notifications" element={
                    <RequirePermission permissions={['announcements.view_announcement', 'announcements.manage_announcement']}>
                        <NotificationsListingPage />
                    </RequirePermission>
                } />
                <Route path="complaints" element={
                    <RequirePermission permissions={['complaints.view_complaint', 'complaints.manage_complaint']}>
                        <ComplaintsListingPage />
                    </RequirePermission>
                } />
                <Route path="role-permissions" element={
                    <RequirePermission permission="system.manage_role_permissions">
                        <RolePermissionsPage />
                    </RequirePermission>
                } />
                <Route path="change-password" element={<ChangePasswordPage />} />
                <Route path="*" element={<Navigate to={ADMIN_BASE} replace />} />
            </Routes>
        </DashboardLayout>
    );
};

export default AdminDashboard;
