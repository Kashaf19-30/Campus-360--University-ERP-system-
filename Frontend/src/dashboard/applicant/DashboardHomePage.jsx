// src/dashboard/applicant/DashboardHomePage.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getApplicantProfile, getMyApplications, getMyDocuments } from '../../services/admissionService';
import { CheckIcon, UserIcon, ClipboardIcon, FileIcon, BellIcon, PlusIcon, ArrowRightIcon, BookIcon } from '../Icons';

const DashboardHomePage = ({ onNavigate, studentInfo }) => {
    const { token } = useAuth();
    const [profileData, setProfileData] = useState(null);
    const [applications, setApplications] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    
    // Required document types for personal documents
    const REQUIRED_DOCUMENTS = ['cnic_front', 'cnic_back', 'domicile', 'photograph'];
    const MAX_DOCUMENTS = REQUIRED_DOCUMENTS.length; // 4 documents

    const [stats, setStats] = useState([
        { label: 'Registration Status', value: 'Not Verified', icon: <CheckIcon />, color: '#10b981', bg: '#f0fdf4' },
        { label: 'Profile Completion', value: '0%', icon: <UserIcon size={20} />, color: '#3b82f6', bg: '#eff6ff', progress: 0 },
        { label: 'Active Applications', value: '0', icon: <ClipboardIcon />, color: '#f59e0b', bg: '#fffbeb' },
        { label: 'Documents Uploaded', value: `0 / ${MAX_DOCUMENTS}`, icon: <FileIcon />, color: '#4169E1', bg: '#eef2ff', progress: 0 },
    ]);

    // Required fields for profile completion calculation
    const requiredFields = [
        'firstName', 'lastName', 'fatherName', 'cnic', 'gender', 'cellPhone', 'dob',
        'religion', 'nationality', 'maritalStatus', 'email'
    ];

    // Calculate profile completion percentage
    const calculateProfileCompletion = (profile) => {
        if (!profile) return 0;
        
        let completedFields = 0;
        
        requiredFields.forEach(field => {
            if (profile[field] && profile[field].toString().trim() !== '') {
                completedFields++;
            }
        });
        
        // Check residence address fields
        if (profile.residence && profile.residence.perm_address && profile.residence.perm_address.trim() !== '') {
            completedFields++;
        }
        
        // Check emergency contact
        if (profile.emergency && profile.emergency.name && profile.emergency.name.trim() !== '') {
            completedFields++;
        }
        
        // Check guardian
        if (profile.guardian && profile.guardian.name && profile.guardian.name.trim() !== '') {
            completedFields++;
        }
        
        const totalFields = requiredFields.length + 3; // +3 for residence, emergency, guardian
        return Math.min(Math.round((completedFields / totalFields) * 100), 100);
    };

    // Get registration status based on profile completion
    const getRegistrationStatus = (completionPercentage) => {
        if (completionPercentage >= 100) return 'Completed';
        if (completionPercentage >= 70) return 'In Progress';
        if (completionPercentage >= 30) return 'Started';
        return 'Not Started';
    };

    const getRegistrationStatusColor = (status) => {
        switch(status) {
            case 'Completed': return '#10b981';
            case 'In Progress': return '#f59e0b';
            case 'Started': return '#3b82f6';
            default: return '#ef4444';
        }
    };

    const getRegistrationStatusBg = (status) => {
        switch(status) {
            case 'Completed': return '#f0fdf4';
            case 'In Progress': return '#fffbeb';
            case 'Started': return '#eff6ff';
            default: return '#fef2f2';
        }
    };

    // Get uploaded document types
    const getUploadedDocumentTypes = (docs) => {
        return docs.map(doc => doc.document_type).filter(type => REQUIRED_DOCUMENTS.includes(type));
    };

    // Get document type display name
    const getDocumentDisplayName = (docType) => {
        const displayNames = {
            'cnic_front': 'CNIC Front',
            'cnic_back': 'CNIC Back',
            'domicile': 'Domicile',
            'photograph': 'Photograph'
        };
        return displayNames[docType] || docType;
    };

    // Load all dashboard data
    useEffect(() => {
        const loadDashboardData = async () => {
            if (!token) return;
            
            setLoading(true);
            try {
                // Load profile
                const profile = await getApplicantProfile(token, studentInfo?.username);
                setProfileData(profile);
                
                // Load applications
                const apps = await getMyApplications(token);
                const appsArray = Array.isArray(apps) ? apps : (apps?.results || []);
                setApplications(appsArray);
                
                // Load personal documents
                const docs = await getMyDocuments(token);
                const docsArray = Array.isArray(docs) ? docs : (docs?.results || []);
                
                // Filter only personal documents (based on required types)
                const personalDocs = docsArray.filter(doc => REQUIRED_DOCUMENTS.includes(doc.document_type));
                setDocuments(personalDocs);
                
                // Calculate stats
                const completionPercentage = calculateProfileCompletion(profile);
                const registrationStatus = getRegistrationStatus(completionPercentage);
                const registrationStatusColor = getRegistrationStatusColor(registrationStatus);
                const registrationStatusBg = getRegistrationStatusBg(registrationStatus);
                
                const activeAppsCount = appsArray.filter(app => 
                    app.status === 'pending' || app.status === 'under_review'
                ).length;
                
                const documentsCount = personalDocs.length;
                const documentsProgress = (documentsCount / MAX_DOCUMENTS) * 100;
                
                // Update stats
                setStats([
                    { 
                        label: 'Registration Status', 
                        value: registrationStatus, 
                        icon: <CheckIcon />, 
                        color: registrationStatusColor, 
                        bg: registrationStatusBg 
                    },
                    { 
                        label: 'Profile Completion', 
                        value: `${completionPercentage}%`, 
                        icon: <UserIcon size={20} />, 
                        color: '#3b82f6', 
                        bg: '#eff6ff', 
                        progress: completionPercentage 
                    },
                    { 
                        label: 'Active Applications', 
                        value: activeAppsCount.toString(), 
                        icon: <ClipboardIcon />, 
                        color: '#f59e0b', 
                        bg: '#fffbeb' 
                    },
                    { 
                        label: 'Documents Uploaded', 
                        value: `${documentsCount} / ${MAX_DOCUMENTS}`, 
                        icon: <FileIcon />, 
                        color: '#4169E1', 
                        bg: '#eef2ff', 
                        progress: documentsProgress 
                    },
                ]);
                
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
            } finally {
                setLoading(false);
            }
        };
        
        loadDashboardData();
    }, [token, studentInfo?.username]);

    // Get missing documents list for notification
    const getMissingDocumentsList = () => {
        const uploadedTypes = documents.map(doc => doc.document_type);
        const missing = REQUIRED_DOCUMENTS.filter(type => !uploadedTypes.includes(type));
        return missing.map(type => getDocumentDisplayName(type));
    };

    if (loading) {
        return (
            <div className="home-dashboard fade-in">
                <div className="loading-spinner">Loading dashboard...</div>
            </div>
        );
    }

    // Get current completion percentage from stats
    const currentCompletionPercentage = stats.find(s => s.label === 'Profile Completion')?.progress || 0;
    const missingDocsList = getMissingDocumentsList();
    const documentsCount = documents.length;

    return (
        <div className="home-dashboard fade-in">
            <div className="welcome-banner fade-up">
                <div className="welcome-text">
                    <h1>Welcome Back, <span className="highlight-text-welcome">{profileData?.firstName || studentInfo?.username || 'Student'}</span> 👋</h1>
                    <p>Track your student portal status and upcoming admission activities from this personalized dashboard.</p>
                </div>
                <div className="welcome-action">
                    <button className="btn-add" onClick={() => onNavigate('profile')}>
                        <PlusIcon /> <span>{profileData?.firstName ? 'Update Profile' : 'Complete Profile'}</span>
                    </button>
                </div>
            </div>

            <div className="stats-grid">
                {stats.map((stat, i) => (
                    <div key={i} className="stat-card fade-up" style={{ animationDelay: `${0.1 * (i + 1)}s` }}>
                        <div className="stat-header">
                            <div className="stat-icon-wrapper" style={{ backgroundColor: stat.bg, color: stat.color }}>
                                {stat.icon}
                            </div>
                            <div className="stat-info">
                                <span className="stat-label">{stat.label}</span>
                                <h3 className="stat-value">{stat.value}</h3>
                            </div>
                        </div>
                        {stat.progress !== undefined && (
                            <div className="stat-progress-container">
                                <div className="stat-progress-bar" style={{ width: `${stat.progress}%`, backgroundColor: stat.color }}></div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="home-content-bottom">
                <div className="home-section activity-section fade-up" style={{ animationDelay: '0.4s' }}>
                    <div className="section-header">
                        <div className="section-header-icon"><BellIcon /></div>
                        <h2 className="section-title">Latest Notifications</h2>
                    </div>
                    <div className="notification-list">
                        <div className="notification-item">
                            <div className="notif-dot info"></div>
                            <div className="notif-content">
                                <span className="notif-title">Welcome to Campus 360!</span>
                                <span className="notif-time">Just now</span>
                            </div>
                        </div>
                        
                        {currentCompletionPercentage < 100 && (
                            <div className="notification-item">
                                <div className="notif-dot alert"></div>
                                <div className="notif-content">
                                    <span className="notif-title">Complete your profile to start applications</span>
                                    <span className="notif-time">Profile completion: {currentCompletionPercentage}%</span>
                                </div>
                            </div>
                        )}
                        
                        {documentsCount < MAX_DOCUMENTS && (
                            <div className="notification-item">
                                <div className="notif-dot alert"></div>
                                <div className="notif-content">
                                    <span className="notif-title">Please upload required documents</span>
                                    <span className="notif-time">
                                        {documentsCount}/{MAX_DOCUMENTS} documents uploaded
                                        {missingDocsList.length > 0 && ` (Missing: ${missingDocsList.join(', ')})`}
                                    </span>
                                </div>
                            </div>
                        )}
                        
                        {applications.length > 0 && applications[0].status === 'pending' && (
                            <div className="notification-item">
                                <div className="notif-dot info"></div>
                                <div className="notif-content">
                                    <span className="notif-title">Your application is under review</span>
                                    <span className="notif-time">Status: {applications[0].status}</span>
                                </div>
                            </div>
                        )}
                        
                        {applications.length > 0 && applications[0].status === 'approved' && (
                            <div className="notification-item">
                                <div className="notif-dot success"></div>
                                <div className="notif-content">
                                    <span className="notif-title">Congratulations! Your application has been approved</span>
                                    <span className="notif-time">Status: {applications[0].status}</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="home-section quick-links-section fade-up" style={{ animationDelay: '0.5s' }}>
                    <div className="section-header">
                        <div className="section-header-icon"><ArrowRightIcon /></div>
                        <h2 className="section-title">Quick Actions</h2>
                    </div>
                    <div className="quick-links-grid">
                        <button className="quick-link-btn" onClick={() => onNavigate('profile')}>
                            <div className="quick-link-icon"><UserIcon size={20} /></div>
                            <span>Complete Profile</span>
                            {currentCompletionPercentage < 100 && (
                                <span className="progress-indicator" style={{ fontSize: '10px', color: '#f59e0b' }}>
                                    {currentCompletionPercentage}%
                                </span>
                            )}
                        </button>
                        <button className="quick-link-btn" onClick={() => onNavigate('application-list')}>
                            <div className="quick-link-icon"><FileIcon /></div>
                            <span>My Applications</span>
                            {applications.length > 0 && (
                                <span className="notification-badge">{applications.length}</span>
                            )}
                        </button>
                        <button className="quick-link-btn" onClick={() => onNavigate('academic-info')}>
                            <div className="quick-link-icon"><BookIcon size={20}/></div>
                            <span>Academic Information</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardHomePage;