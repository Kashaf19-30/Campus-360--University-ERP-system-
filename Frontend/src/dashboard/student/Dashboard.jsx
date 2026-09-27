import React, { useState, useEffect, useMemo } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pageIdFromPath } from '../../routes/paths';
import { useDashboardNavigate } from '../../routes/useDashboardNavigate';
import { useFilteredNavItems } from '../../routes/navPermissions';
import RequirePermission from '../../routes/RequirePermission';
import { getMyStudentProfile, updateMyStudentProfile } from '../../services/studentsService';
import DashboardLayout from '../shared/DashboardLayout';
import { LayoutDashboardIcon, BookIcon, ClipboardIcon, FileTextIcon, BellIcon, ShieldIcon, UserIcon } from '../Icons';
import StudentDashboardHomePage from './DashboardHomePage';
import MyTranscriptPage from './Pages/MyTranscriptPage';
import { MyEnrollmentsPage, MyGradesPage, MyAttendancePage, MyFeesPage, MyProfilePage, MyComplaintsPage, MyNotificationsPage, MyAnnouncementsPage, MyLeavesPage } from './Pages/StudentModulePages';
import ChangePasswordPage from '../applicant/Pages/ChangePasswordPage';
import { LoadingSpinner } from '../shared/helpers';

const STUDENT_BASE = '/student';

const ProfileCompletionForm = ({ profileForm, setProfileForm, onSubmit, submitting, profileLocked }) => (
    <div className="page-container fade-in">
        <div className="form-card" style={{ maxWidth: '750px', margin: '30px auto', borderTop: '4px solid #ef4444' }}>
            <div className="section-header">
                <div className="section-header-icon" style={{ backgroundColor: '#fee2e2', color: '#ef4444' }}><UserIcon /></div>
                <div>
                    <h2 className="section-title">Complete Your Student Profile</h2>
                    <p style={{ color: '#666', margin: '4px 0 0 0' }}>Before exploring your campus dashboard, please complete your remaining student profile details.</p>
                </div>
            </div>
            {profileLocked && (
                <div style={{ marginTop: 16, padding: '12px 16px', background: '#fef3c7', borderRadius: 6 }}>
                    Your profile is locked by admin. Contact the office to update details.
                </div>
            )}
            <form onSubmit={onSubmit} style={{ marginTop: '20px' }}>
                <div className="two-column-grid" style={{ marginBottom: '20px' }}>
                    <div className="field-group">
                        <label className="field-label">Blood Group <span className="required">*</span></label>
                        <select className="field-input field-select" disabled={profileLocked} value={profileForm.blood_group} onChange={e => setProfileForm({ ...profileForm, blood_group: e.target.value })}>
                            {['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">Guardian Phone Number <span className="required">*</span></label>
                        <input type="text" className="field-input" placeholder="03001234567" disabled={profileLocked} value={profileForm.guardian_phone} onChange={e => setProfileForm({ ...profileForm, guardian_phone: e.target.value })} required />
                    </div>
                    <div className="field-group">
                        <label className="field-label">Guardian Occupation <span className="required">*</span></label>
                        <input type="text" className="field-input" placeholder="e.g. Business / Government Employee" disabled={profileLocked} value={profileForm.guardian_occupation} onChange={e => setProfileForm({ ...profileForm, guardian_occupation: e.target.value })} required />
                    </div>
                    <div className="field-group">
                        <label className="field-label">Residential Address <span className="required">*</span></label>
                        <input type="text" className="field-input" placeholder="Current residential address" disabled={profileLocked} value={profileForm.residential_address} onChange={e => setProfileForm({ ...profileForm, residential_address: e.target.value })} required />
                    </div>
                </div>
                <div className="two-column-grid" style={{ marginBottom: '20px' }}>
                    <div className="field-group">
                        <label className="field-label">Medical Conditions (Optional)</label>
                        <input type="text" className="field-input" placeholder="None or specify" disabled={profileLocked} value={profileForm.medical_conditions} onChange={e => setProfileForm({ ...profileForm, medical_conditions: e.target.value })} />
                    </div>
                    <div className="field-group">
                        <label className="field-label">Disabilities (Optional)</label>
                        <input type="text" className="field-input" placeholder="None or specify" disabled={profileLocked} value={profileForm.disabilities} onChange={e => setProfileForm({ ...profileForm, disabilities: e.target.value })} />
                    </div>
                </div>
                {!profileLocked && (
                <div className="form-actions">
                    <button type="submit" className="btn-save" disabled={submitting}>
                        {submitting ? 'Saving Details...' : 'Save Profile & Continue to Dashboard'}
                    </button>
                </div>
                )}
            </form>
        </div>
    </div>
);

const StudentDashboard = () => {
    const { token, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const onNavigate = useDashboardNavigate(STUDENT_BASE);
    const currentPage = pageIdFromPath(location.pathname, STUDENT_BASE);
    const [loadingProfile, setLoadingProfile] = useState(true);
    const [profileIncomplete, setProfileIncomplete] = useState(false);
    const [submittingProfile, setSubmittingProfile] = useState(false);
    const [profileLocked, setProfileLocked] = useState(false);
    const [registrationNumber, setRegistrationNumber] = useState('');
    const [isGraduated, setIsGraduated] = useState(false);

    const [profileForm, setProfileForm] = useState({
        blood_group: 'A+',
        medical_conditions: '',
        disabilities: '',
        guardian_phone: '',
        guardian_occupation: '',
        residential_address: ''
    });

    const checkProfile = async () => {
        setLoadingProfile(true);
        try {
            const stData = await getMyStudentProfile(token);
            const prof = stData.profile || {};
            if (stData.registration_number) setRegistrationNumber(stData.registration_number);
            setIsGraduated(stData.status === 'graduated');
            setProfileLocked(!!prof.profile_locked);
            if (!prof.blood_group || !prof.guardian_phone || !prof.guardian_occupation || !prof.residential_address) {
                setProfileIncomplete(true);
                setProfileForm({
                    blood_group: prof.blood_group || 'A+',
                    medical_conditions: prof.medical_conditions || '',
                    disabilities: prof.disabilities || '',
                    guardian_phone: prof.guardian_phone || '',
                    guardian_occupation: prof.guardian_occupation || '',
                    residential_address: prof.residential_address || prof.permanent_address || ''
                });
            } else {
                setProfileIncomplete(false);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingProfile(false);
        }
    };

    useEffect(() => {
        if (token) checkProfile();
    }, [token]);

    const handleProfileSubmit = async (e) => {
        e.preventDefault();
        if (!profileForm.blood_group || !profileForm.guardian_phone || !profileForm.guardian_occupation || !profileForm.residential_address) {
            alert('Please fill in all required profile fields.');
            return;
        }
        setSubmittingProfile(true);
        try {
            await updateMyStudentProfile(profileForm, token);
            alert('Profile completed successfully! Welcome to your dashboard.');
            setProfileIncomplete(false);
            navigate(STUDENT_BASE);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to update profile');
        } finally {
            setSubmittingProfile(false);
        }
    };

    const navItems = useMemo(() => {
        const items = [
            { id: 'home', label: 'Dashboard', icon: <LayoutDashboardIcon />, always: true },
            { id: 'profile', label: 'My Profile', icon: <UserIcon />, always: true },
            { id: 'enrollments', label: 'My Enrollments', icon: <BookIcon size={20} />, permission: 'enrollments.view_own_enrollment', alumniHidden: true },
            { id: 'grades', label: 'My Grades', icon: <FileTextIcon />, permission: 'examinations.view_own_grades' },
            { id: 'transcript', label: 'My Transcript', icon: <FileTextIcon />, permission: 'examinations.view_own_grades' },
            { id: 'attendance', label: 'My Attendance', icon: <ClipboardIcon size={20} />, permission: 'attendance.view_own_attendance' },
            { id: 'fees', label: 'My Fees', icon: <FileTextIcon />, permission: 'fees.view_own_fees', alumniHidden: true },
            { id: 'complaints', label: 'My Complaints', icon: <BellIcon size={20} />, permissions: ['complaints.view_own_complaint', 'complaints.create_complaint'] },
            { id: 'announcements', label: 'Announcements', icon: <BellIcon size={20} />, permission: 'announcements.view_announcement' },
            { id: 'leaves', label: 'Leave Applications', icon: <ClipboardIcon size={20} />, always: true, alumniHidden: true },
            { id: 'notifications', label: 'Notifications', icon: <BellIcon size={20} />, permission: 'announcements.view_announcement' },
            { id: 'change-password', label: 'Change Password', icon: <ShieldIcon />, always: true },
        ];
        return isGraduated ? items.filter(item => !item.alumniHidden) : items;
    }, [isGraduated]);

    const filteredNavItems = useFilteredNavItems(navItems);

    const handleLogout = async (e) => {
        e.preventDefault();
        await logout();
        navigate('/');
    };

    if (loadingProfile) return <LoadingSpinner message="Checking student profile status..." />;

    const profileFormEl = (
        <ProfileCompletionForm
            profileForm={profileForm}
            setProfileForm={setProfileForm}
            onSubmit={handleProfileSubmit}
            submitting={submittingProfile}
            profileLocked={profileLocked}
        />
    );

    return (
        <DashboardLayout
            roleLabel={isGraduated ? 'Alumni' : 'Student'}
            navItems={filteredNavItems}
            currentPage={currentPage}
            onNavigate={onNavigate}
            sidebarSubLabel={registrationNumber}
            onLogout={handleLogout}
        >
            {profileIncomplete && (
                <div style={{
                    margin: '0 0 16px', padding: '12px 16px', borderRadius: 8,
                    background: '#fef3c7', border: '1px solid #fcd34d', color: '#92400e',
                }}>
                    Complete your student profile to unlock full dashboard features.
                    {currentPage !== 'home' && (
                        <button
                            type="button"
                            className="btn-save"
                            style={{ marginLeft: 12, padding: '4px 12px', fontSize: '0.85rem' }}
                            onClick={() => navigate(STUDENT_BASE)}
                        >
                            Complete now
                        </button>
                    )}
                </div>
            )}
            {profileIncomplete && currentPage === 'home' ? (
                profileFormEl
            ) : (
                <Routes>
                    <Route index element={<StudentDashboardHomePage onNavigate={onNavigate} isGraduated={isGraduated} />} />
                    <Route path="profile" element={<MyProfilePage />} />
                    {!isGraduated && (
                        <Route path="enrollments" element={
                            <RequirePermission permission="enrollments.view_own_enrollment">
                                <MyEnrollmentsPage />
                            </RequirePermission>
                        } />
                    )}
                    <Route path="grades" element={
                        <RequirePermission permission="examinations.view_own_grades">
                            <MyGradesPage />
                        </RequirePermission>
                    } />
                    <Route path="transcript" element={
                        <RequirePermission permission="examinations.view_own_grades">
                            <MyTranscriptPage />
                        </RequirePermission>
                    } />
                    <Route path="attendance" element={
                        <RequirePermission permission="attendance.view_own_attendance">
                            <MyAttendancePage />
                        </RequirePermission>
                    } />
                    {!isGraduated && (
                        <Route path="fees" element={
                            <RequirePermission permission="fees.view_own_fees">
                                <MyFeesPage />
                            </RequirePermission>
                        } />
                    )}
                    <Route path="complaints" element={
                        <RequirePermission permissions={['complaints.view_own_complaint', 'complaints.create_complaint']}>
                            <MyComplaintsPage />
                        </RequirePermission>
                    } />
                    <Route path="announcements" element={
                        <RequirePermission permission="announcements.view_announcement">
                            <MyAnnouncementsPage />
                        </RequirePermission>
                    } />
                    {!isGraduated && <Route path="leaves" element={<MyLeavesPage />} />}
                    <Route path="notifications" element={
                        <RequirePermission permission="announcements.view_announcement">
                            <MyNotificationsPage />
                        </RequirePermission>
                    } />
                    <Route path="change-password" element={<ChangePasswordPage />} />
                    <Route path="*" element={<Navigate to={STUDENT_BASE} replace />} />
                </Routes>
            )}
        </DashboardLayout>
    );
};

export default StudentDashboard;
