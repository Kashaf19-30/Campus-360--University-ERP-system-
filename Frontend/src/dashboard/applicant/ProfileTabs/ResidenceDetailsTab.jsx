// src/dashboard/applicant/ProfileTabs/ResidenceDetailsTab.jsx
import React, { useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { saveApplicantProfile, prepareProfileForBackend } from '../../../services/admissionService';
import { clearFormDraft } from '../../../utils/formDraft';
import { HomeIcon } from '../../Icons';
import AddressFields from './AddressFields';
import { getSelectionError, getAddressError } from '../../../utils/validation';

const ResidenceDetailsTab = ({ profileData, updateProfile, readOnly = false }) => {
    const { token, user } = useAuth();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const residenceData = profileData.residence || {};

    const handleAddressChange = (key, val) => {
        updateProfile('residence', key, val);
        
        // Clear error for this field when user starts typing
        if (errors[key]) {
            setErrors(prev => ({ ...prev, [key]: '' }));
        }
    };

    const handleBlur = (field) => {
        setTouched(prev => ({ ...prev, [field]: true }));
        
        // Validate on blur
        let error = '';
        if (field === 'perm_country') error = getSelectionError(residenceData.perm_country, 'Country');
        else if (field === 'perm_state') error = getSelectionError(residenceData.perm_state, 'State');
        else if (field === 'perm_city') error = getSelectionError(residenceData.perm_city, 'City');
        else if (field === 'perm_address') error = getAddressError(residenceData.perm_address, 'Address');
        
        if (error) {
            setErrors(prev => ({ ...prev, [field]: error }));
        }
    };

    const validateForm = () => {
        const newErrors = {};
        
        newErrors.perm_country = getSelectionError(residenceData.perm_country, 'Country');
        newErrors.perm_state = getSelectionError(residenceData.perm_state, 'State');
        newErrors.perm_city = getSelectionError(residenceData.perm_city, 'City');
        newErrors.perm_address = getAddressError(residenceData.perm_address, 'Address');
        
        setErrors(newErrors);
        
        // Mark all fields as touched
        setTouched({
            perm_country: true,
            perm_state: true,
            perm_city: true,
            perm_address: true
        });
        
        return Object.keys(newErrors).every(key => !newErrors[key]);
    };

    const handleSubmit = async () => {
        if (!validateForm()) {
            // Scroll to first error
            const firstErrorField = Object.keys(errors).find(key => errors[key]);
            if (firstErrorField) {
                const element = document.querySelector(`[data-field="${firstErrorField}"]`);
                if (element) element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
        
        setIsSubmitting(true);
        try {
            const payload = prepareProfileForBackend(profileData);
            await saveApplicantProfile(payload, token);
            if (user?.user_id) clearFormDraft(user.user_id, 'profile');
            alert('Address details saved to database successfully!');
            // Clear errors after successful save
            setErrors({});
            setTouched({});
        } catch (error) {
            console.error('Failed to save address details:', error);
            const errorMsg = error.response?.data?.message || error.message || 'Failed to save address details';
            alert('Failed to save: ' + errorMsg);
        } finally {
            setIsSubmitting(false);
        }
    };

    const isFormValid = () => {
        return residenceData.perm_country && 
               residenceData.perm_state && 
               residenceData.perm_city && 
               residenceData.perm_address &&
               residenceData.perm_address.trim().length >= 5;
    };

    return (
        <div className="tab-content-area fade-in" style={readOnly ? { pointerEvents: 'none', opacity: 0.92 } : undefined}>
            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><HomeIcon /></div>
                    <h2 className="section-title">Address Information</h2>
                </div>
                
                <div className="info-banner compact">
                    <span>📍</span>
                    <span>Please provide your complete permanent address. This information will be used for official correspondence.</span>
                </div>
                
                <AddressFields 
                    prefix="perm_" 
                    data={residenceData} 
                    onChange={handleAddressChange}
                    onBlur={handleBlur}
                    errors={errors}
                    touched={touched}
                />
                
                {/* Form completion status */}
                {Object.keys(residenceData).some(key => residenceData[key]) && (
                    <div className={`form-status ${isFormValid() ? 'complete' : 'incomplete'}`}>
                        {isFormValid() ? (
                            <span>✓ All address fields are complete</span>
                        ) : (
                            <span>⚠ Please complete all required fields marked with *</span>
                        )}
                    </div>
                )}
            </div>

            <div className="form-actions">
                {!readOnly && (
                <button 
                    className="btn-update" 
                    onClick={handleSubmit} 
                    disabled={isSubmitting}
                >
                    {isSubmitting ? (
                        <span className="btn-loading">
                            <span className="spinner-small"></span>
                            Saving...
                        </span>
                    ) : (
                        'Save Address Details'
                    )}
                </button>
                )}
            </div>
        </div>
    );
};

export default ResidenceDetailsTab;