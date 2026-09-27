import React, { useState, useEffect, useMemo } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pageIdFromPath } from '../../routes/paths';
import { useDashboardNavigate } from '../../routes/useDashboardNavigate';
import { useFilteredNavItems } from '../../routes/navPermissions';
import RequirePermission from '../../routes/RequirePermission';
import { getMyFacultyProfile } from '../../services/facultyService';
import DashboardLayout from '../shared/DashboardLayout';
import { LayoutDashboardIcon, BookIcon, ClipboardIcon, FileTextIcon, BellIcon, ShieldIcon, UserIcon } from '../Icons';
import TeacherDashboardHomePage from './DashboardHomePage';
import TeacherOnboardingPage from './Pages/TeacherOnboardingPage';
import {
    TeacherSectionsPage, TeacherAttendancePage, TeacherExaminationsPage,
    TeacherNotificationsPage, TeacherLeavesPage, TeacherAnnouncementsPage,
    TeacherProfileModal,
} from './Pages/TeacherModulePages';
import ChangePasswordPage from '../applicant/Pages/ChangePasswordPage';
import { LoadingSpinner } from '../shared/helpers';

const TEACHER_BASE = '/teacher';

const TeacherDashboard = () => {
    const { token, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const onNavigate = useDashboardNavigate(TEACHER_BASE);
    const currentPage = pageIdFromPath(location.pathname, TEACHER_BASE);
    const [loadingProfile, setLoadingProfile] = useState(true);
    const [profileIncomplete, setProfileIncomplete] = useState(false);
    const [showProfileModal, setShowProfileModal] = useState(false);
    const [teacherProfile, setTeacherProfile] = useState(null);
    const [profileModalLoading, setProfileModalLoading] = useState(false);

    const checkProfile = async () => {
        setLoadingProfile(true);
        try {
            const profile = await getMyFacultyProfile(token);
            setProfileIncomplete(!profile.profile_completed);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingProfile(false);
        }
    };

    useEffect(() => {
        if (token) checkProfile();
    }, [token]);

    const openProfileModal = async () => {
        setShowProfileModal(true);
        setProfileModalLoading(true);
        try {
            const profile = await getMyFacultyProfile(token);
            setTeacherProfile(profile);
        } catch (e) {
            console.error(e);
            setTeacherProfile(null);
        } finally {
            setProfileModalLoading(false);
        }
    };

    const navItems = useMemo(() => [
        { id: 'home', label: 'Dashboard', icon: <LayoutDashboardIcon />, always: true },
        { id: 'courses', label: 'My Courses', icon: <BookIcon size={20} />, permission: 'academics.view_offering' },
        { id: 'attendance', label: 'Attendance', icon: <ClipboardIcon size={20} />, permission: 'attendance.mark_attendance' },
        { id: 'examinations', label: 'Examinations', icon: <FileTextIcon />, permission: 'examinations.view_examination' },
        { id: 'leaves', label: 'Leave Requests', icon: <ClipboardIcon size={20} />, permission: 'attendance.mark_attendance' },
        { id: 'announcements', label: 'Announcements', icon: <BellIcon size={20} />, permissions: ['announcements.view_announcement', 'announcements.create_announcement'] },
        { id: 'notifications', label: 'Notifications', icon: <BellIcon size={20} />, permission: 'announcements.view_announcement' },
        { id: 'change-password', label: 'Change Password', icon: <ShieldIcon />, always: true },
    ], []);

    const filteredNavItems = useFilteredNavItems(navItems);

    const handleLogout = async (e) => {
        e.preventDefault();
        await logout();
        navigate('/');
    };

    if (loadingProfile) return <LoadingSpinner message="Loading teacher profile..." />;

    if (profileIncomplete) {
        return (
            <DashboardLayout roleLabel="Teacher" navItems={[{ id: 'home', label: 'Complete Profile', icon: <UserIcon /> }]} currentPage="home" onNavigate={() => {}} onLogout={handleLogout}>
                <TeacherOnboardingPage onComplete={() => { setProfileIncomplete(false); navigate(TEACHER_BASE); }} />
            </DashboardLayout>
        );
    }

    return (
        <>
            <DashboardLayout
                roleLabel="Teacher"
                navItems={filteredNavItems}
                currentPage={currentPage}
                onNavigate={onNavigate}
                onProfileClick={openProfileModal}
                onLogout={handleLogout}
            >
                <Routes>
                    <Route index element={<TeacherDashboardHomePage onNavigate={onNavigate} />} />
                    <Route path="courses" element={
                        <RequirePermission permission="academics.view_offering">
                            <TeacherSectionsPage />
                        </RequirePermission>
                    } />
                    <Route path="attendance" element={
                        <RequirePermission permission="attendance.mark_attendance">
                            <TeacherAttendancePage />
                        </RequirePermission>
                    } />
                    <Route path="examinations" element={
                        <RequirePermission permission="examinations.view_examination">
                            <TeacherExaminationsPage />
                        </RequirePermission>
                    } />
                    <Route path="leaves" element={
                        <RequirePermission permission="attendance.mark_attendance">
                            <TeacherLeavesPage />
                        </RequirePermission>
                    } />
                    <Route path="announcements" element={
                        <RequirePermission permissions={['announcements.view_announcement', 'announcements.create_announcement']}>
                            <TeacherAnnouncementsPage />
                        </RequirePermission>
                    } />
                    <Route path="notifications" element={
                        <RequirePermission permission="announcements.view_announcement">
                            <TeacherNotificationsPage />
                        </RequirePermission>
                    } />
                    <Route path="change-password" element={<ChangePasswordPage />} />
                    <Route path="*" element={<Navigate to={TEACHER_BASE} replace />} />
                </Routes>
            </DashboardLayout>
            {showProfileModal && (
                <TeacherProfileModal
                    profile={teacherProfile}
                    loading={profileModalLoading}
                    onClose={() => { setShowProfileModal(false); setTeacherProfile(null); }}
                />
            )}
        </>
    );
};

export default TeacherDashboard;
