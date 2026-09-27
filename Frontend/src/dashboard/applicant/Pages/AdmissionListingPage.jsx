import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { getMyApplications, getApplicantProfile, getMyDocuments, deleteApplication as deleteApplicationApi } from '../../../services/admissionService';
import {
    isPersonalDetailsComplete,
    isResidenceDetailsComplete,
    isEmergencyContactComplete,
    isGuardianDetailsComplete,
    arePersonalDocumentsComplete,
} from '../../../utils/validation';
import { CheckIcon, AlertCircleIcon, PlusIcon, FileTextIcon, TrashIcon } from '../../Icons';

const EyeIcon = ({ size = 16 }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
        <circle cx="12" cy="12" r="3"></circle>
    </svg>
);

const AdmissionListingPage = ({ onCreateNew, onAiRecommendation, readOnly = false, admissionsOpen = true }) => {
    const { token } = useAuth();
    const [applications, setApplications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [checklistItems, setChecklistItems] = useState([
        { label: 'Personal Details', status: 'pending', key: 'personal' },
        { label: 'Residence Details', status: 'pending', key: 'residence' },
        { label: 'Emergency Contact', status: 'pending', key: 'emergency' },
        { label: 'Guardian Details', status: 'pending', key: 'guardian' },
        { label: 'Personal Documents (CNIC, Domicile, Photograph)', status: 'pending', key: 'documents' },
    ]);

    const loadChecklistStatus = async () => {
        try {
            const profile = await getApplicantProfile(token);
            const hasPersonalData = profile && (
                profile.firstName || profile.first_name ||
                profile.lastName || profile.last_name ||
                profile.cnic
            );

            if (!profile || !hasPersonalData) {
                setChecklistItems([
                    { label: 'Personal Details', status: 'pending', key: 'personal' },
                    { label: 'Residence Details', status: 'pending', key: 'residence' },
                    { label: 'Emergency Contact', status: 'pending', key: 'emergency' },
                    { label: 'Guardian Details', status: 'pending', key: 'guardian' },
                    { label: 'Personal Documents (CNIC, Domicile, Photograph)', status: 'pending', key: 'documents' },
                ]);
                return;
            }

            const docs = await getMyDocuments(token);
            const docsArray = Array.isArray(docs) ? docs : (docs?.results || []);
            const updatedChecklist = [
                {
                    label: 'Personal Details',
                    status: isPersonalDetailsComplete(profile) ? 'completed' : 'pending',
                    key: 'personal',
                },
                {
                    label: 'Residence Details',
                    status: isResidenceDetailsComplete(profile) ? 'completed' : 'pending',
                    key: 'residence',
                },
                {
                    label: 'Emergency Contact',
                    status: isEmergencyContactComplete(profile) ? 'completed' : 'pending',
                    key: 'emergency',
                },
                {
                    label: 'Guardian Details',
                    status: isGuardianDetailsComplete(profile) ? 'completed' : 'pending',
                    key: 'guardian',
                },
                {
                    label: 'Personal Documents (CNIC, Domicile, Photograph)',
                    status: arePersonalDocumentsComplete(docsArray) ? 'completed' : 'pending',
                    key: 'documents',
                },
            ];
            setChecklistItems(updatedChecklist);

            const completedCount = updatedChecklist.filter((item) => item.status === 'completed').length;
            localStorage.setItem('profileCompletionPercentage', (completedCount / updatedChecklist.length) * 100);
        } catch (error) {
            console.error('Failed to load checklist status:', error);
            setChecklistItems([
                { label: 'Personal Details', status: 'pending', key: 'personal' },
                { label: 'Residence Details', status: 'pending', key: 'residence' },
                { label: 'Emergency Contact', status: 'pending', key: 'emergency' },
                { label: 'Guardian Details', status: 'pending', key: 'guardian' },
                { label: 'Personal Documents (CNIC, Domicile, Photograph)', status: 'pending', key: 'documents' },
            ]);
        }
    };

    const loadApplications = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getMyApplications(token);
            const appsArray = Array.isArray(data) ? data : (data?.results || []);
            setApplications(appsArray);
        } catch (error) {
            console.error('Failed to load applications:', error);
            setError(error.response?.data?.message || error.message || 'Failed to load applications');
            setApplications([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) {
            loadApplications();
            loadChecklistStatus();
        }
    }, [token]);

    const handleDeleteApplication = async (appId, appNumber) => {
        if (!confirm(`Are you sure you want to delete application ${appNumber}? This action cannot be undone.`)) {
            return;
        }
        try {
            await deleteApplicationApi(appId, token);
            alert('Application deleted successfully!');
            await loadApplications();
            await loadChecklistStatus();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to delete application');
        }
    };

    const getStatusBadgeClass = (status) => {
        switch (status?.toLowerCase()) {
            case 'approved':
                return 'status-badge approved';
            case 'rejected':
                return 'status-badge rejected';
            case 'under_review':
                return 'status-badge under-review';
            default:
                return 'status-badge pending';
        }
    };

    const getStatusText = (status) => {
        switch (status?.toLowerCase()) {
            case 'approved':
                return 'APPROVED';
            case 'rejected':
                return 'REJECTED';
            case 'under_review':
                return 'UNDER REVIEW';
            default:
                return 'PENDING';
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return '—';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-PK', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    };

    // Calculate how many items are completed
    const completedCount = checklistItems.filter(item => item.status === 'completed').length;
    const totalCount = checklistItems.length;

    if (loading) {
        return (
            <div className="page-container fade-in">
                <div className="loading-spinner">Loading applications...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page-container fade-in">
                <div className="error-message" style={{ textAlign: 'center', padding: '40px' }}>
                    <p>Error loading applications: {error}</p>
                    <button className="btn-verify" onClick={loadApplications}>Try Again</button>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
                <div>
                    <div className="breadcrumb-minimal">DASHBOARD &gt; ADMISSION MANAGEMENT &gt; APPLICATIONS</div>
                    <h1 className="page-title-minimal">Admission Management</h1>
                </div>
                <button
                    type="button"
                    className="btn-ai-recommend"
                    onClick={onAiRecommendation}
                    disabled={applications.length > 0 || readOnly}
                    title={
                        applications.length > 0
                            ? 'AI recommendations are unavailable after you submit an application'
                            : 'Get AI-powered degree recommendations based on your profile'
                    }
                    style={{
                        whiteSpace: 'nowrap',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 8,
                        opacity: applications.length > 0 || readOnly ? 0.55 : 1,
                        cursor: applications.length > 0 || readOnly ? 'not-allowed' : 'pointer',
                    }}
                >
                    <span aria-hidden="true">✨</span> AI Degree Recommendation
                </button>
            </div>

            {!admissionsOpen && (
                <div style={{ marginBottom: 16, padding: '14px 16px', background: '#fef3c7', borderRadius: 8, color: '#92400e' }}>
                    <strong>Admissions are closed.</strong> You can update your profile, but new applications cannot be submitted until admissions reopen.
                </div>
            )}

            {/* Checklist Section */}
            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><CheckIcon /></div>
                    <h2 className="section-title">
                        Profile Completion Checklist 
                        <span style={{ fontSize: '0.8rem', marginLeft: '10px', color: '#64748b' }}>
                            ({completedCount}/{totalCount} completed)
                        </span>
                    </h2>
                </div>
                <div className="checklist-grid">
                    {checklistItems.map((item, i) => (
                        <div key={i} className={`checklist-item ${item.status}`}>
                            <div className="checklist-icon">
                                {item.status === 'completed' ? <CheckIcon /> : <AlertCircleIcon />}
                            </div>
                            <span className="checklist-label">{item.label}</span>
                            <span className="checklist-status-text">{item.status.toUpperCase()}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Applications Table */}
            <div className="form-card">
                <div className="table-toolbar">
                    <h2 className="section-title" style={{ margin: 0 }}>My Applications</h2>
                    <button 
                        className="btn-add" 
                        onClick={onCreateNew} 
                        disabled={applications.length > 0 || readOnly || !admissionsOpen}
                        style={readOnly || !admissionsOpen ? { display: 'none' } : undefined}
                        title={
                            !admissionsOpen
                                ? 'Admissions are currently closed'
                                : applications.length > 0
                                    ? 'You can only create one application'
                                    : 'Create new admission application'
                        }
                    >
                        <PlusIcon /> <span>Create New Application</span>
                        {applications.length > 0 && <span style={{ fontSize: '12px', marginLeft: '8px' }}>(Only one allowed)</span>}
                        {completedCount !== totalCount && <span style={{ fontSize: '12px', marginLeft: '8px' }}>(Complete profile first)</span>}
                    </button>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th>
                                <th>App No</th>
                                <th>App Type</th>
                                <th>Submission Date</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {applications.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="empty-row">
                                        <FileTextIcon />
                                        <p>No application found</p>
                                        <span>Click "Create New Application" to start your admission journey.</span>
                                    </td>
                                </tr>
                            ) : (
                                applications.map((app, index) => (
                                    <tr key={app.id}>
                                        <td>{index + 1}</td>
                                        <td><span className="app-number">{app.application_number}</span></td>
                                        <td><span className="app-type-badge">{app.admission_type || 'Regular'}</span></td>
                                        <td>{formatDate(app.submitted_at)}</td>
                                        <td>
                                            <span className={getStatusBadgeClass(app.status)}>
                                                {getStatusText(app.status)}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button 
                                                    className="action-btn view-btn"
                                                    onClick={() => alert(`Application: ${app.application_number}\nStatus: ${app.status}\nType: ${app.admission_type}`)}
                                                    title="View Details"
                                                >
                                                    <EyeIcon size={16} />
                                                </button>
                                                {!readOnly && (
                                                <button 
                                                    className="action-btn danger"
                                                    onClick={() => handleDeleteApplication(app.id, app.application_number)}
                                                    title="Delete Application"
                                                >
                                                    <TrashIcon size={16} />
                                                </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                
                {applications.length > 0 && (
                    <div className="table-pagination">
                        <span className="pagination-info">
                            Showing {applications.length} of {applications.length} entries
                        </span>
                        <div className="pagination-controls">
                            <button className="pagination-btn" disabled>Previous</button>
                            <button className="pagination-btn active">1</button>
                            <button className="pagination-btn" disabled>Next</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdmissionListingPage;