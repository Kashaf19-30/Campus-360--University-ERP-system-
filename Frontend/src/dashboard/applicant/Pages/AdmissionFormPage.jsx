import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext'; 
import { submitApplication, getMyApplications, getAdmissionPrograms, getPublicAdmissionSettings } from '../../../services/admissionService';
import { saveFormDraft, loadFormDraft, clearFormDraft } from '../../../utils/formDraft';
import { PlusIcon, TrashIcon, XIcon, CheckIcon, InfoIcon } from '../../Icons';

const AdmissionFormPage = ({ onCancel, onSubmitted, editApplicationId = null, hasExistingApp = false }) => {
    const [activeTab, setActiveTab] = useState('preferences');
    const [preferences, setPreferences] = useState([]);
    const [availablePrograms, setAvailablePrograms] = useState([]);
    const [programsLoading, setProgramsLoading] = useState(true);
    const [programsError, setProgramsError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [pendingPref, setPendingPref] = useState(null);
    const [showToast, setShowToast] = useState(false);
    const [showSuccessModal, setShowSuccessModal] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [loading, setLoading] = useState(false);
    const [formErrors, setFormErrors] = useState({});
    const [admissionsOpen, setAdmissionsOpen] = useState(true);
    const { token, user } = useAuth();

    const [formData, setFormData] = useState({
        program: '',
        preference: ''
    });

    useEffect(() => {
        getPublicAdmissionSettings()
            .then((data) => setAdmissionsOpen(data?.is_open !== false))
            .catch(() => setAdmissionsOpen(true));
    }, []);

    useEffect(() => {
        const loadPrograms = async () => {
            if (!token) return;
            setProgramsLoading(true);
            setProgramsError(null);
            try {
                const programs = await getAdmissionPrograms(token);
                setAvailablePrograms(Array.isArray(programs) ? programs : []);
                if (!programs?.length) {
                    setProgramsError('No degree programs are open for admission right now. Please contact the admissions office.');
                }
            } catch (error) {
                console.error('Failed to load programs:', error);
                setAvailablePrograms([]);
                setProgramsError(
                    error.response?.data?.error
                    || error.response?.data?.detail
                    || 'Could not load programs. Please refresh and try again.'
                );
            } finally {
                setProgramsLoading(false);
            }
        };
        loadPrograms();
    }, [token]);

    useEffect(() => {
        if (user?.user_id) {
            const draft = loadFormDraft(user.user_id, 'application');
            if (draft?.preferences) setPreferences(draft.preferences);
        }
    }, [user?.user_id]);

    useEffect(() => {
        if (user?.user_id) {
            saveFormDraft(user.user_id, 'application', { preferences });
        }
    }, [preferences, user?.user_id]);

    const getSelectedProgramIds = () => new Set(preferences.map((p) => String(p.program_id)));

    const getSelectablePrograms = () => {
        const taken = getSelectedProgramIds();
        return availablePrograms.filter((p) => !taken.has(String(p.program_id)));
    };

    const getSelectedProgram = (programId) => {
        return availablePrograms.find(p => String(p.program_id) === String(programId));
    };

    const isPreferenceExists = (programId, preference) => {
        const programTaken = programId && preferences.some(p => String(p.program_id) === String(programId));
        const orderTaken = preference && preferences.some(p => p.preference_label === preference || String(p.preference) === String(preference));
        return programTaken || orderTaken;
    };

    const handleAddClick = () => {
        if (!formData.program) {
            alert('Please select a program');
            return;
        }
        if (!formData.preference) {
            alert('Please select a preference');
            return;
        }

        const selectedProgram = getSelectedProgram(formData.program);
        if (!selectedProgram) {
            alert('Please select a valid program');
            return;
        }
        
        if (isPreferenceExists(formData.program, formData.preference)) {
            alert(`This program or preference order has already been added. Please choose different options.`);
            return;
        }

        setPendingPref({
            program_id: selectedProgram.program_id,
            program: selectedProgram.program_name,
            preference: formData.preference,
            preference_order: parseInt(formData.preference),
            department: selectedProgram.department_name
        });
        setShowModal(true);
    };

    const confirmPreference = () => {
        const newPreferences = [...preferences, { 
            id: Date.now(),
            sr: preferences.length + 1,
            program_id: pendingPref.program_id,
            program: pendingPref.program,
            preference: pendingPref.preference_order,
            preference_label: pendingPref.preference,
            department: pendingPref.department
        }];
        
        newPreferences.sort((a, b) => {
            const prefA = parseInt(a.preference);
            const prefB = parseInt(b.preference);
            return prefA - prefB;
        });
        
        newPreferences.forEach((pref, idx) => {
            pref.sr = idx + 1;
        });
        
        setPreferences(newPreferences);
        setShowModal(false);
        setFormData({ program: '', preference: '' });
        
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
    };

    const removePreference = (id) => {
        const newPrefs = preferences
            .filter(p => p.id !== id)
            .map((p, i) => ({ ...p, sr: i + 1 }));
        setPreferences(newPrefs);
    };

    const validateForm = () => {
        const errors = {};
        
        if (preferences.length === 0) {
            errors.preferences = 'Please add at least one program preference';
        }
        
        setFormErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmitApplication = async () => {
        if (!admissionsOpen) {
            alert('Admissions are currently closed. Application submission is not available.');
            return;
        }
        if (!validateForm()) {
            return;
        }
        
        if (preferences.length === 0) {
            alert('Please add at least one program preference before submitting.');
            return;
        }
        
        setSubmitting(true);
        
        try {
            const applicationData = {
                admission_type: 'Regular',
                preferences: preferences.map(p => ({
                    program_id: p.program_id,
                    program: p.program,
                    preference_order: p.preference,
                    preference: p.preference_label || `${p.preference}${p.preference === 1 ? 'st' : p.preference === 2 ? 'nd' : 'rd'} Preference`,
                    department: p.department
                }))
            };
            
            const result = await submitApplication(applicationData, token);

            if (result.rejected) {
                alert(result.message || 'Your application has been rejected due to program requirements.');
                if (user?.user_id) clearFormDraft(user.user_id, 'application');
                if (onSubmitted) onSubmitted();
                onCancel();
                return;
            }
            
            if (user?.user_id) clearFormDraft(user.user_id, 'application');
            setShowSuccessModal(true);
            
            setTimeout(() => {
                setShowSuccessModal(false);
                if (onSubmitted) onSubmitted();
                onCancel();
            }, 3000);
            
        } catch (error) {
            console.error('Submission error:', error);
            const errorMsg = error.response?.data?.message || 
                            error.response?.data?.error || 
                            'Submission failed. Make sure your profile is saved first.';
            alert(errorMsg);
        } finally {
            setSubmitting(false);
        }
    };

    const getNextPreferenceOrder = () => {
        if (preferences.length === 0) return 1;
        if (preferences.length === 1) return 2;
        if (preferences.length === 2) return 3;
        return null;
    };

    const getAvailablePreferences = () => {
        const next = getNextPreferenceOrder();
        return next ? [next] : [];
    };

    if (loading || programsLoading) {
        return (
            <div className="page-container fade-in">
                <div className="loading-spinner">Loading application data...</div>
            </div>
        );
    }

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <div className="breadcrumb-minimal">DASHBOARD &gt; ADMISSION &gt; NEW APPLICATION</div>
                    <h1 className="page-title-minimal">Create Application</h1>
                </div>
                <button className="btn-verify" onClick={onCancel}>Back to List</button>
            </div>

            <div className="form-card fade-in">
                {!admissionsOpen && (
                    <div style={{ marginBottom: 20, padding: '14px 16px', background: '#fef3c7', borderRadius: 8, color: '#92400e' }}>
                        <strong>Admissions Closed</strong> — You can review your profile and documents, but new applications cannot be submitted while the admission window is closed.
                    </div>
                )}
                <div className="info-banner" style={{ marginBottom: '20px' }}>
                    <InfoIcon />
                    <div>
                        <strong>Program Preferences:</strong> Select your 1st preference first, then optionally add 2nd and 3rd preferences in order. Admission type is Regular by default.
                    </div>
                </div>
                {programsError && (
                    <div className="error-message" style={{ marginBottom: '16px', padding: '12px', background: '#fee2e2', borderRadius: '8px', color: '#b91c1c' }}>
                        {programsError}
                    </div>
                )}
                    <div className="two-column-grid">
                        <div className="field-group">
                            <label className="field-label">Pick a Program <span className="required">*</span></label>
                            <select 
                                className="field-input field-select" 
                                value={formData.program}
                                onChange={(e) => setFormData({ ...formData, program: e.target.value })}
                                disabled={programsLoading}
                            >
                                <option value="">
                                    {programsLoading
                                        ? 'Loading programs...'
                                        : getSelectablePrograms().length === 0
                                            ? 'No programs available'
                                            : 'Select Program'}
                                </option>
                                {getSelectablePrograms().map(program => (
                                    <option key={program.program_id} value={String(program.program_id)}>
                                        {program.program_name} ({program.department_name})
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="field-group">
                            <label className="field-label">Pick a Preference <span className="required">*</span></label>
                            <select 
                                className="field-input field-select"
                                value={formData.preference}
                                onChange={(e) => setFormData({...formData, preference: e.target.value})}
                            >
                                <option value="">Select Preference</option>
                                {getAvailablePreferences().map(pref => (
                                    <option key={pref} value={pref}>
                                        {pref}{pref === 1 ? 'st' : pref === 2 ? 'nd' : 'rd'} Preference
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                    
                    <div style={{ marginBottom: '25px' }}>
                        <button 
                            className="btn-add" 
                            disabled={!formData.program || !formData.preference || submitting || preferences.length >= 3}
                            onClick={handleAddClick}
                        >
                            <PlusIcon /> <span>ADD PREFERENCE</span>
                        </button>
                    </div>
                    
                    {formErrors.preferences && (
                        <div className="error-message" style={{ color: 'red', marginBottom: '15px', padding: '10px', background: '#fee2e2', borderRadius: '8px' }}>
                            {formErrors.preferences}
                        </div>
                    )}

                    <div className="data-table-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Sr#</th>
                                    <th>Department</th>
                                    <th>Program</th>
                                    <th>Preference</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {preferences.length === 0 ? (
                                    <tr>
                                        <td colSpan="5" className="empty-row">
                                            No preference added. Please add at least one program preference.
                                        </td>
                                    </tr>
                                ) : (
                                    preferences.map((p) => (
                                        <tr key={p.id}>
                                             <td>{p.sr}</td>
                                             <td>{p.department}</td>
                                             <td><strong>{p.program}</strong></td>
                                             <td><span className="pref-badge">{p.preference_label || p.preference}</span></td>
                                             <td>
                                                <button 
                                                    className="action-btn danger" 
                                                    onClick={() => removePreference(p.id)}
                                                    disabled={submitting}
                                                >
                                                    <TrashIcon />
                                                </button>
                                             </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    
                    {preferences.length > 0 && (
                        <div className="info-banner compact" style={{ marginTop: '20px' }}>
                            <CheckIcon />
                            <span>You have added {preferences.length} preference(s). Select preferences in order: 1st, then 2nd, then 3rd.</span>
                        </div>
                    )}
                    
                    <div className="form-actions" style={{ marginTop: '20px' }}>
                        <button 
                            className="btn-save" 
                            disabled={!admissionsOpen || preferences.length === 0 || submitting}
                            onClick={handleSubmitApplication}
                        >
                            {submitting ? 'Submitting...' : 'Submit Application'}
                        </button>
                    </div>
            </div>

            {/* Success Toast */}
            {showToast && (
                <div className="toast success fade-in-up">
                    <CheckIcon />
                    <span>Program preference added successfully!</span>
                </div>
            )}

            {/* Preference Confirmation Modal */}
            {showModal && (
                <div className="modal-overlay">
                    <div className="modal-content glass-modal fade-up">
                        <div className="modal-header">
                            <h3>Confirm Program Selection</h3>
                            <button className="close-btn" onClick={() => setShowModal(false)}>
                                <XIcon />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="modal-info-item">
                                <label>Department:</label>
                                <span>{pendingPref?.department}</span>
                            </div>
                            <div className="modal-info-item">
                                <label>Selected Program:</label>
                                <span className="highlight-text">{pendingPref?.program}</span>
                            </div>
                            <div className="modal-info-item">
                                <label>Preference Order:</label>
                                <span className="highlight-text">{pendingPref?.preference}</span>
                            </div>
                            <p className="modal-note">
                                Please confirm your selection. Added preferences will be considered during the admission processing.
                                You can reorder preferences by removing and re-adding them.
                            </p>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowModal(false)}>
                                Cancel
                            </button>
                            <button className="btn-primary" onClick={confirmPreference}>
                                Save Preference
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Success Submission Modal */}
            {showSuccessModal && (
                <div className="modal-overlay">
                    <div className="modal-content glass-modal fade-up" style={{ textAlign: 'center', padding: '40px' }}>
                        <div className="success-icon-large fade-in">
                            <CheckIcon size={48} />
                        </div>
                        <h2 style={{ color: '#1e293b', marginBottom: '10px' }}>Application Submitted!</h2>
                        <p style={{ color: '#64748b', marginBottom: '15px' }}>
                            Your admission application has been successfully submitted for processing.
                        </p>
                        <p style={{ color: '#64748b', marginBottom: '30px', fontSize: '14px' }}>
                            You can track your application status in the application list.
                        </p>
                        <button className="btn-primary" onClick={onCancel} style={{ width: '100%' }}>
                            View My Applications
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdmissionFormPage;