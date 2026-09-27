// src/dashboard/applicant/Dashboard.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pageIdFromPath } from '../../routes/paths';
import { useDashboardNavigate } from '../../routes/useDashboardNavigate';
import { getApplicantProfile, getMyDocuments, getAcademicRecords, getMyApplications, isApplicationLocked, hasRejectedApplication, getApplicationChallanPending, getPublicAdmissionSettings } from '../../services/admissionService';
import { saveFormDraft, clearFormDraft } from '../../utils/formDraft';
import { hasMatricAndInter, isPersonalDetailsComplete, isResidenceDetailsComplete, isEmergencyContactComplete, isGuardianDetailsComplete, isProfileComplete } from '../../utils/validation';
import ThemeToggle from '../../components/ThemeToggle';
import '../../Dashboard.css';


// Import Icons
import { 
    LayoutDashboardIcon, 
    FileTextIcon, 
    UserIcon, 
    MapPinIcon, 
    PhoneIcon, 
    ShieldIcon, 
    LogOutIcon,
    BookIcon,
    FileIcon
} from '../Icons';

// Import Profile Tabs
import PersonalDetailsTab from './ProfileTabs/PersonalDetailsTab';
import ResidenceDetailsTab from './ProfileTabs/ResidenceDetailsTab';
import EmergencyContactTab from './ProfileTabs/EmergencyContactTab';
import GuardianDetailsTab from './ProfileTabs/GuardianDetailsTab';

// Import Pages
import DashboardHomePage from './DashboardHomePage';
import PersonalDocumentsPage from './Pages/PersonalDocumentsPage';
import AcademicInformationPage from './Pages/AcademicInformationPage';
import AddAcademicInfoPage from './Pages/AddAcademicInfoPage';
import AdmissionListingPage from './Pages/AdmissionListingPage';
import AdmissionFormPage from './Pages/AdmissionFormPage';
import ChangePasswordPage from './Pages/ChangePasswordPage';
import RejectedApplicationView from './Pages/RejectedApplicationView';
import ApplicantChallanPanel from './Pages/ApplicantChallanPanel';
import AiRecommendationPage from './Pages/AiRecommendationPage';

// Sequential order of tabs
const TAB_ORDER = ['personal', 'residence', 'emergency', 'guardian'];

// Get the highest completed tab index
const getHighestCompletedTab = (profileData) => {
    if (isPersonalDetailsComplete(profileData)) {
        if (isResidenceDetailsComplete(profileData)) {
            if (isEmergencyContactComplete(profileData)) {
                if (isGuardianDetailsComplete(profileData)) {
                    return 3;
                }
                return 2;
            }
            return 1;
        }
        return 0;
    }
    return -1;
};

// Check if a tab can be accessed (only current or next)
const canAccessTab = (profileData, targetTab) => {
    const targetIndex = TAB_ORDER.indexOf(targetTab);
    const highestCompleted = getHighestCompletedTab(profileData);
    return targetIndex <= highestCompleted + 1;
};

// Get the next required tab to complete
const getNextRequiredTab = (profileData) => {
    if (!isPersonalDetailsComplete(profileData)) return 'personal';
    if (!isResidenceDetailsComplete(profileData)) return 'residence';
    if (!isEmergencyContactComplete(profileData)) return 'emergency';
    if (!isGuardianDetailsComplete(profileData)) return 'guardian';
    return null;
};

// Check if all required documents are uploaded
const hasAllDocuments = (documents) => {
    const requiredDocuments = ['cnic_front', 'cnic_back', 'domicile', 'photograph'];
    const uploadedTypes = documents.map(doc => doc.document_type);
    return requiredDocuments.every(type => uploadedTypes.includes(type));
};

// Check if academic records exist (both Matric and Inter required)
const hasAcademicRecords = (records) => {
    return hasMatricAndInter(records);
};

// ========== PROFILE PAGE ==========

function ApplicantProfilePage({
    activeTab,
    navigateToTab,
    tabLabels,
    getTabStatus,
    canAccessTab,
    profileData,
    renderActiveTab,
}) {
    return (
        <>
            <div className="page-header-minimal">
                <div className="breadcrumb-minimal">DASHBOARD &nbsp;&gt;&nbsp; USER MANAGEMENT &nbsp;&gt;&nbsp; {tabLabels[activeTab]}</div>
                <h1 className="page-title-minimal">Complete Profile</h1>
            </div>
            <div className="step-navigation">
                <div
                    className={`step-item ${activeTab === 'personal' ? 'active' : ''} ${getTabStatus('personal') ? 'completed' : ''}`}
                    onClick={() => navigateToTab('personal')}
                >
                    <div className="step-icon-wrapper"><UserIcon /></div>
                    <span className="step-label">Personal Details</span>
                    {getTabStatus('personal') && <span className="step-check">✓</span>}
                </div>
                <div className="step-connector"></div>
                <div
                    className={`step-item ${activeTab === 'residence' ? 'active' : ''} ${getTabStatus('residence') ? 'completed' : ''} ${!canAccessTab(profileData, 'residence') ? 'disabled' : ''}`}
                    onClick={() => navigateToTab('residence')}
                    style={{ cursor: canAccessTab(profileData, 'residence') ? 'pointer' : 'not-allowed', opacity: canAccessTab(profileData, 'residence') ? 1 : 0.5 }}
                >
                    <div className="step-icon-wrapper"><MapPinIcon /></div>
                    <span className="step-label">Address Details</span>
                    {getTabStatus('residence') && <span className="step-check">✓</span>}
                </div>
                <div className="step-connector"></div>
                <div
                    className={`step-item ${activeTab === 'emergency' ? 'active' : ''} ${getTabStatus('emergency') ? 'completed' : ''} ${!canAccessTab(profileData, 'emergency') ? 'disabled' : ''}`}
                    onClick={() => navigateToTab('emergency')}
                    style={{ cursor: canAccessTab(profileData, 'emergency') ? 'pointer' : 'not-allowed', opacity: canAccessTab(profileData, 'emergency') ? 1 : 0.5 }}
                >
                    <div className="step-icon-wrapper"><PhoneIcon /></div>
                    <span className="step-label">Emergency Contact</span>
                    {getTabStatus('emergency') && <span className="step-check">✓</span>}
                </div>
                <div className="step-connector"></div>
                <div
                    className={`step-item ${activeTab === 'guardian' ? 'active' : ''} ${getTabStatus('guardian') ? 'completed' : ''} ${!canAccessTab(profileData, 'guardian') ? 'disabled' : ''}`}
                    onClick={() => navigateToTab('guardian')}
                    style={{ cursor: canAccessTab(profileData, 'guardian') ? 'pointer' : 'not-allowed', opacity: canAccessTab(profileData, 'guardian') ? 1 : 0.5 }}
                >
                    <div className="step-icon-wrapper"><ShieldIcon /></div>
                    <span className="step-label">Guardian Details</span>
                    {getTabStatus('guardian') && <span className="step-check">✓</span>}
                </div>
            </div>
            {renderActiveTab()}
        </>
    );
}

// ========== MAIN DASHBOARD COMPONENT ==========

const APPLICANT_BASE = '/applicant';

const Dashboard = () => {
    const { token, user: authUser, logout: authLogout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const goToPage = useDashboardNavigate(APPLICANT_BASE);
    const currentPage = pageIdFromPath(location.pathname, APPLICANT_BASE);
    const [activeTab, setActiveTab] = useState('personal');
    const [profileData, setProfileData] = useState({
            firstName: '', lastName: '', fatherName: '', username: '', dob: '', religion: '',
            cellPhone: '', disability: false, gender: '', cnic: '', maritalStatus: '',
            nationality: '', profileImage: null,
            residence: { perm_country: '', perm_state: '', perm_city: '', perm_address: '' },
            emergency: { name: '', relation: '', phone: '' },
            guardian: { name: '', cnic: '', relation: '' },
    });
    const [profileLoaded, setProfileLoaded] = useState(false);
    
    const [documents, setDocuments] = useState([]);
    const [academicRecords, setAcademicRecords] = useState([]);
    const [applications, setApplications] = useState([]);
    const [isLocked, setIsLocked] = useState(false);
    const [isRejected, setIsRejected] = useState(false);
    const [loading, setLoading] = useState(true);
    const [admissionsGloballyOpen, setAdmissionsGloballyOpen] = useState(true);
    
    const [profileOpen, setProfileOpen] = useState(false);
    const [admissionOpen, setAdmissionOpen] = useState(true);
    const studentInfo = authUser || { username: 'Student', user_id: 'N/A' };
    
    const initialLoadDone = useRef(false);
    const isMounted = useRef(true);

    // Function to refresh documents from API
    const refreshDocuments = useCallback(async () => {
        if (!token || !isMounted.current) return;
        try {
            const docs = await getMyDocuments(token);
            if (isMounted.current) {
                setDocuments(Array.isArray(docs) ? docs : []);
            }
        } catch (error) {
            console.error('Failed to refresh documents:', error);
        }
    }, [token]);

    // Function to refresh academic records from API
    const refreshAcademicRecords = useCallback(async () => {
        if (!token || !isMounted.current) return;
        try {
            const records = await getAcademicRecords(token);
            if (isMounted.current) {
                setAcademicRecords(Array.isArray(records) ? records : []);
            }
        } catch (error) {
            console.error('Failed to refresh academic records:', error);
        }
    }, [token]);

    const refreshApplications = useCallback(async () => {
        if (!token || !isMounted.current) return;
        try {
            const apps = await getMyApplications(token);
            const appsArray = Array.isArray(apps) ? apps : (apps?.results || []);
            if (isMounted.current) {
                setApplications(appsArray);
                setIsLocked(isApplicationLocked(appsArray));
                setIsRejected(hasRejectedApplication(appsArray));
            }
        } catch (error) {
            console.error('Failed to refresh applications:', error);
        }
    }, [token]);

    useEffect(() => {
        isMounted.current = true;
        initialLoadDone.current = false;
        setProfileLoaded(false);

        const loadData = async () => {
            if (!token || !authUser?.user_id) {
                if (isMounted.current) setLoading(false);
                return;
            }

            if (initialLoadDone.current) {
                if (isMounted.current) setLoading(false);
                return;
            }
            initialLoadDone.current = true;

            try {
                const settings = await getPublicAdmissionSettings().catch(() => ({ is_open: true }));
                if (isMounted.current) {
                    setAdmissionsGloballyOpen(settings?.is_open !== false);
                }

                const profile = await getApplicantProfile(token, authUser.username);
                if (isMounted.current) {
                    setProfileData(profile);
                    setProfileLoaded(true);
                }

                const docs = await getMyDocuments(token);
                if (isMounted.current) setDocuments(Array.isArray(docs) ? docs : []);

                const records = await getAcademicRecords(token);
                if (isMounted.current) setAcademicRecords(Array.isArray(records) ? records : []);

                const apps = await getMyApplications(token);
                const appsArray = Array.isArray(apps) ? apps : (apps?.results || []);
                if (isMounted.current) {
                    setApplications(appsArray);
                    setIsLocked(isApplicationLocked(appsArray));
                    setIsRejected(hasRejectedApplication(appsArray));
                }
            } catch (error) {
                console.error('Failed to load applicant data:', error);
            } finally {
                if (isMounted.current) setLoading(false);
            }
        };

        loadData();

        return () => {
            isMounted.current = false;
        };
    }, [token, authUser?.user_id, authUser?.username]);

    useEffect(() => {
        if (!profileLoaded || !authUser?.user_id) return;
        saveFormDraft(authUser.user_id, 'profile', profileData);
    }, [profileData, authUser?.user_id, profileLoaded]);

    const handleProfileChange = (key, value) => {
        setProfileData(prev => ({ ...prev, [key]: value }));
    };

    const handleNestedProfileChange = (category, key, value) => {
        setProfileData(prev => ({
            ...prev,
            [category]: { ...prev[category], [key]: value }
        }));
    };

    const handleLogout = async (e) => {
        e.preventDefault();
        await authLogout();
        navigate('/');
    };

    // Tab navigation with sequential validation
    const navigateToTab = (tabName) => {
        if (!canAccessTab(profileData, tabName)) {
            const nextRequired = getNextRequiredTab(profileData);
            alert(`Please complete ${nextRequired === 'personal' ? 'Personal Details' : 
                   nextRequired === 'residence' ? 'Address Details' :
                   nextRequired === 'emergency' ? 'Emergency Contact' : 'Guardian Details'} first.`);
            return;
        }
        setActiveTab(tabName);
        goToPage('profile');
    };

    // Navigation to Personal Documents - requires Personal Details
    const navigateToPersonalDocuments = () => {
        if (!isPersonalDetailsComplete(profileData)) {
            alert('Please complete your Personal Details first before accessing Documents.');
            goToPage('profile');
            setActiveTab('personal');
            return;
        }
        goToPage('personal-docs');
    };

    // Navigation to Academic Information - requires ALL Personal Documents
    const navigateToAcademicInfo = () => {
        if (!isProfileComplete(profileData)) {
            const nextRequired = getNextRequiredTab(profileData);
            alert(`Please complete all profile sections first. Next: ${nextRequired === 'personal' ? 'Personal Details' : 
                   nextRequired === 'residence' ? 'Address Details' :
                   nextRequired === 'emergency' ? 'Emergency Contact' : 'Guardian Details'}`);
            goToPage('profile');
            setActiveTab(nextRequired || 'personal');
            return;
        }
        if (!hasAllDocuments(documents)) {
            alert('Please upload all required Personal Documents (CNIC Front, CNIC Back, Domicile, Photograph) first.');
            goToPage('personal-docs');
            return;
        }
        goToPage('academic-info');
    };

    // Navigation to Application List - requires ALL profile tabs, ALL documents, AND academic records
    const navigateToApplicationList = () => {
        if (!isProfileComplete(profileData)) {
            const nextRequired = getNextRequiredTab(profileData);
            alert(`Please complete all profile sections first. Next: ${nextRequired === 'personal' ? 'Personal Details' : 
                   nextRequired === 'residence' ? 'Address Details' :
                   nextRequired === 'emergency' ? 'Emergency Contact' : 'Guardian Details'}`);
            goToPage('profile');
            setActiveTab(nextRequired || 'personal');
            return;
        }
        if (!hasAllDocuments(documents)) {
            alert('Please upload all required Personal Documents (CNIC Front, CNIC Back, Domicile, Photograph) first.');
            goToPage('personal-docs');
            return;
        }
        if (!hasAcademicRecords(academicRecords)) {
            alert('Please add both Matric and Intermediate academic records before proceeding.');
            goToPage('academic-info');
            return;
        }
        goToPage('application-list');
    };

    // Navigation to New Application - requires ALL profile tabs, ALL documents, AND academic records, AND no existing application
    const navigateToNewApplication = async () => {
        if (!admissionsGloballyOpen) {
            alert('Admissions are currently closed. Application submission is not available.');
            goToPage('application-list');
            return;
        }
        if (isLocked) {
            alert('Your application has already been submitted. You cannot create a new one.');
            goToPage('application-list');
            return;
        }

        // First, check if there's an existing application
        try {
            const existingApps = await getMyApplications(token);
            const appsArray = Array.isArray(existingApps) ? existingApps : (existingApps?.results || []);
            
            if (appsArray.length > 0) {
                alert('You already have a submitted application.');
                goToPage('application-list');
                return;
            }
        } catch (error) {
            console.error('Failed to check existing applications:', error);
            // Continue with other checks even if this fails
        }
        
        if (!isProfileComplete(profileData)) {
            const nextRequired = getNextRequiredTab(profileData);
            alert(`Please complete all profile sections first. Next: ${nextRequired === 'personal' ? 'Personal Details' : 
                   nextRequired === 'residence' ? 'Address Details' :
                   nextRequired === 'emergency' ? 'Emergency Contact' : 'Guardian Details'}`);
            goToPage('profile');
            setActiveTab(nextRequired || 'personal');
            return;
        }
        if (!hasAllDocuments(documents)) {
            alert('Please upload all required Personal Documents (CNIC Front, CNIC Back, Domicile, Photograph) first.');
            goToPage('personal-docs');
            return;
        }
        if (!hasAcademicRecords(academicRecords)) {
            alert('Please add both Matric and Intermediate academic records before proceeding.');
            goToPage('academic-info');
            return;
        }
        goToPage('application-form');
    };

    const tabLabels = {
        personal: 'PERSONAL DETAILS',
        residence: 'ADDRESS DETAILS',
        emergency: 'EMERGENCY CONTACT',
        guardian: 'GUARDIAN DETAILS',
    };

    const renderActiveTab = () => {
        const tabProps = { readOnly: isLocked };
        switch (activeTab) {
            case 'personal':  
                return <PersonalDetailsTab profileData={profileData} updateProfile={handleProfileChange} {...tabProps} />;
            case 'residence': 
                return <ResidenceDetailsTab profileData={profileData} updateProfile={handleNestedProfileChange} {...tabProps} />;
            case 'emergency': 
                return <EmergencyContactTab profileData={profileData} updateProfile={handleNestedProfileChange} {...tabProps} />;
            case 'guardian':  
                return <GuardianDetailsTab profileData={profileData} updateProfile={handleNestedProfileChange} {...tabProps} />;
            default:          
                return <PersonalDetailsTab profileData={profileData} updateProfile={handleProfileChange} {...tabProps} />;
        }
    };

    const getTabStatus = (tabName) => {
        switch(tabName) {
            case 'personal': return isPersonalDetailsComplete(profileData);
            case 'residence': return isResidenceDetailsComplete(profileData);
            case 'emergency': return isEmergencyContactComplete(profileData);
            case 'guardian': return isGuardianDetailsComplete(profileData);
            default: return false;
        }
    };

    if (loading) {
        return (
            <div className="dashboard-layout">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading your profile...</p>
                </div>
            </div>
        );
    }

    const challanApp = getApplicationChallanPending(applications);
    const rejectedApp = applications.find(app => app.status === 'rejected');
    const rejectionReason = rejectedApp?.rejection_message || rejectedApp?.decision?.rejection_reason || '';

    if (isRejected) {
        return (
            <RejectedApplicationView
                username={studentInfo.username}
                rejectionReason={rejectionReason}
                onLogout={handleLogout}
            />
        );
    }

    return (
        <div className="dashboard-layout fade-in">
            <aside className="dashboard-sidebar">
                <div className="sidebar-user-card compact-card">
                    <img 
                        src={profileData.profileImage || "/student-avatar.jpg"} 
                        alt="Student" 
                        className="sidebar-avatar-compact" 
                        onError={(e) => { 
                            e.target.src = `https://ui-avatars.com/api/?name=${studentInfo.username}&background=3B5BDB&color=fff`; 
                        }} 
                    />
                    <div className="sidebar-user-info">
                        <div className="sidebar-user-id-compact">{studentInfo.username}</div>
                        <div className="sidebar-user-role-compact">Student Applicant</div>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    <a 
                        className={`sidebar-link ${currentPage === 'home' ? 'active' : ''}`} 
                        onClick={() => goToPage('home')} 
                        style={{ cursor: 'pointer' }}
                    >
                        <span className="sidebar-link-icon"><LayoutDashboardIcon /></span>
                        Dashboard
                    </a>
                    <a 
                        className={`sidebar-link ${currentPage === 'profile' ? 'active' : ''}`} 
                        onClick={() => goToPage('profile')} 
                        style={{ cursor: 'pointer' }}
                    >
                        <span className="sidebar-link-icon"><UserIcon /></span>
                        Complete Profile
                    </a>
                    <a 
                        className={`sidebar-link dropdown-link ${['personal-docs','academic-info','add-academic', 'application-list', 'application-form'].includes(currentPage) ? 'active' : ''}`} 
                        onClick={() => setAdmissionOpen(!admissionOpen)} 
                        style={{ cursor: 'pointer' }}
                    >
                        <span className="sidebar-link-icon"><FileTextIcon /></span>
                        <span className="sidebar-text-clamp">Admission Management</span>
                        <span className={`sidebar-link-arrow ${admissionOpen ? 'open' : ''}`}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="6 9 12 15 18 9"></polyline>
                            </svg>
                        </span>
                    </a>
                    {admissionOpen && (
                        <div className="sidebar-submenu">
                            <a 
                                className={`sidebar-sublink ${currentPage === 'personal-docs' ? 'active' : ''}`} 
                                onClick={navigateToPersonalDocuments}
                                style={{ cursor: isPersonalDetailsComplete(profileData) ? 'pointer' : 'not-allowed', opacity: isPersonalDetailsComplete(profileData) ? 1 : 0.5 }}
                            >
                                Personal Documents
                                {!isPersonalDetailsComplete(profileData) && <span style={{ marginLeft: '8px', fontSize: '10px' }}>🔒</span>}
                            </a>
                            <a 
                                className={`sidebar-sublink ${currentPage === 'academic-info' || currentPage === 'add-academic' ? 'active' : ''}`} 
                                onClick={navigateToAcademicInfo}
                                style={{ cursor: hasAllDocuments(documents) ? 'pointer' : 'not-allowed', opacity: hasAllDocuments(documents) ? 1 : 0.5 }}
                            >
                                Academic Information
                                {!hasAllDocuments(documents) && <span style={{ marginLeft: '8px', fontSize: '10px' }}>🔒</span>}
                            </a>
                            <a 
                                className={`sidebar-sublink ${currentPage === 'application-list' ? 'active' : ''}`} 
                                onClick={navigateToApplicationList}
                                style={{ cursor: isProfileComplete(profileData) && hasAllDocuments(documents) && hasAcademicRecords(academicRecords) ? 'pointer' : 'not-allowed', opacity: isProfileComplete(profileData) && hasAllDocuments(documents) && hasAcademicRecords(academicRecords) ? 1 : 0.5 }}
                            >
                                Application List
                                {(!isProfileComplete(profileData) || !hasAllDocuments(documents) || !hasAcademicRecords(academicRecords)) && <span style={{ marginLeft: '8px', fontSize: '10px' }}>🔒</span>}
                            </a>
                            <a 
                                className={`sidebar-sublink ${currentPage === 'application-form' ? 'active' : ''}`} 
                                onClick={navigateToNewApplication}
                                style={{ cursor: isLocked || !(isProfileComplete(profileData) && hasAllDocuments(documents) && hasAcademicRecords(academicRecords)) ? 'not-allowed' : 'pointer', opacity: isLocked || !(isProfileComplete(profileData) && hasAllDocuments(documents) && hasAcademicRecords(academicRecords)) ? 0.5 : 1, display: isLocked ? 'none' : undefined }}
                            >
                                New Application
                                {(!isProfileComplete(profileData) || !hasAllDocuments(documents) || !hasAcademicRecords(academicRecords)) && <span style={{ marginLeft: '8px', fontSize: '10px' }}>🔒</span>}
                            </a>
                        </div>
                    )}
                    <a 
                        className={`sidebar-link ${currentPage === 'change-password' ? 'active' : ''}`} 
                        onClick={() => goToPage('change-password')} 
                        style={{ cursor: 'pointer' }}
                    >
                        <span className="sidebar-link-icon"><ShieldIcon /></span>
                        Change Password
                    </a>
                </nav>
            </aside>

            <main className="dashboard-main">
                <header className="dashboard-header">
                    <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="header-logo-icon" style={{ display: 'flex', alignItems: 'center' }}>
                        <img src="/campus360-logo.png" alt="Campus 360" style={{ height: '36px', objectFit: 'contain', borderRadius: '5px'}} />
                        </div>
                        <div className="header-logo-text" style={{ fontWeight: '700', fontSize: '1.25rem', color: '#1e293b', letterSpacing: '-0.5px' }}>
                            Campus 360
                        </div>
                    </div>
                    <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <ThemeToggle />
                        <div className="header-profile" onClick={() => setProfileOpen(!profileOpen)}>
                            <img 
                                src={profileData.profileImage || "/student-avatar.jpg"} 
                                alt={studentInfo.username} 
                                title={studentInfo.username} 
                                className="header-avatar" 
                                onError={(e) => { 
                                    e.target.src = `https://ui-avatars.com/api/?name=${studentInfo.username}&background=3B5BDB&color=fff`; 
                                }} 
                            />
                            <div className={`dropdown-menu ${profileOpen ? 'show' : ''}`}>
                                <a href="#" className="dropdown-item" onClick={(e) => { 
                                    e.preventDefault(); 
                                    goToPage('profile'); 
                                    setProfileOpen(false); 
                                }}>
                                    <UserIcon /> Profile
                                </a>
                                <div className="dropdown-divider"></div>
                                <a href="#" onClick={handleLogout} className="dropdown-item text-danger">
                                    <LogOutIcon /> Logout
                                </a>
                            </div>
                        </div>
                    </div>
                </header>

                <div className="dashboard-content-wrapper">
                    {challanApp && (
                        <ApplicantChallanPanel application={challanApp} onChallanUploaded={refreshApplications} />
                    )}
                    {isLocked && !challanApp && (
                        <div style={{
                            background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px',
                            padding: '14px 18px', marginBottom: '20px', color: 'var(--text-primary)',
                        }}>
                            <strong>Application Submitted</strong> — Your application is under review. You cannot make changes to your profile, documents, or academic records.
                        </div>
                    )}

                    <Routes>
                        <Route
                            index
                            element={
                                <DashboardHomePage
                                    onNavigate={goToPage}
                                    studentInfo={studentInfo}
                                    isLocked={isLocked}
                                    applications={applications}
                                />
                            }
                        />
                        <Route
                            path="profile"
                            element={
                                <ApplicantProfilePage
                                    activeTab={activeTab}
                                    navigateToTab={navigateToTab}
                                    tabLabels={tabLabels}
                                    getTabStatus={getTabStatus}
                                    canAccessTab={canAccessTab}
                                    profileData={profileData}
                                    renderActiveTab={renderActiveTab}
                                />
                            }
                        />
                        <Route
                            path="personal-docs"
                            element={<PersonalDocumentsPage onDocumentChange={refreshDocuments} readOnly={isLocked} />}
                        />
                        <Route
                            path="academic-info"
                            element={
                                <AcademicInformationPage
                                    onAddClick={() => goToPage('add-academic')}
                                    onAcademicRecordChange={refreshAcademicRecords}
                                    readOnly={isLocked}
                                />
                            }
                        />
                        <Route
                            path="add-academic"
                            element={<AddAcademicInfoPage onCancel={() => goToPage('academic-info')} />}
                        />
                        <Route
                            path="ai-recommendation"
                            element={
                                applications.length > 0 || isLocked ? (
                                    <Navigate to={`${APPLICANT_BASE}/application-list`} replace />
                                ) : (
                                    <AiRecommendationPage />
                                )
                            }
                        />
                        <Route
                            path="application-list"
                            element={
                                <AdmissionListingPage
                                    onCreateNew={navigateToNewApplication}
                                    onAiRecommendation={() => goToPage('ai-recommendation')}
                                    readOnly={isLocked}
                                    admissionsOpen={admissionsGloballyOpen}
                                />
                            }
                        />
                        <Route
                            path="application-form"
                            element={
                                !admissionsGloballyOpen ? (
                                    <Navigate to={`${APPLICANT_BASE}/application-list`} replace />
                                ) : (
                                    <AdmissionFormPage
                                        onCancel={() => goToPage('application-list')}
                                        onSubmitted={refreshApplications}
                                    />
                                )
                            }
                        />
                        <Route path="change-password" element={<ChangePasswordPage />} />
                        <Route path="*" element={<Navigate to={APPLICANT_BASE} replace />} />
                    </Routes>
                </div>

                <footer className="dashboard-footer">
                    <div>2026 &copy; Campus 360. All rights reserved.</div>
                    <div>Developed by Campus 360 Group</div>
                </footer>
            </main>
        </div>
    );
};

export default Dashboard;