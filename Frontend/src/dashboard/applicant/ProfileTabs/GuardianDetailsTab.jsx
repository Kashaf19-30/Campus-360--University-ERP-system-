// src/dashboard/applicant/ProfileTabs/GuardianDetailsTab.jsx
import React, { useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { saveApplicantProfile, prepareProfileForBackend } from '../../../services/admissionService';
import { clearFormDraft } from '../../../utils/formDraft';
import { UserIcon, ShieldIcon } from '../../Icons';
import { getNameError, getCNICError } from '../../../utils/validation';

const GuardianDetailsTab = ({ profileData, updateProfile, readOnly = false }) => {
    const { token, user } = useAuth();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const guardianData = profileData.guardian || {};

    const validateField = (key, value) => {
        switch (key) {
            case 'name':
                return getNameError(value, 'Guardian name');
            case 'cnic':
                return getCNICError(value);
            case 'relation':
                if (!value) return 'Relation is required';
                return '';
            default:
                return '';
        }
    };

    const handleFieldChange = (key, val) => {
        updateProfile('guardian', key, val);
        const error = validateField(key, val);
        setErrors(prev => ({ ...prev, [key]: error }));
    };

    const handleBlur = (key) => {
        setTouched(prev => ({ ...prev, [key]: true }));
        const error = validateField(key, guardianData[key]);
        setErrors(prev => ({ ...prev, [key]: error }));
    };

    const getFieldStatus = (key) => {
        if (!touched[key]) return null;
        if (errors[key]) return 'error';
        if (guardianData[key]) return 'success';
        return null;
    };

    const getInputClass = (key) => {
        const status = getFieldStatus(key);
        if (status === 'error') return 'field-input error';
        if (status === 'success') return 'field-input success';
        return 'field-input';
    };

    const getSelectClass = (key) => {
        const status = getFieldStatus(key);
        if (status === 'error') return 'field-input field-select error';
        if (status === 'success') return 'field-input field-select success';
        return 'field-input field-select';
    };

    const handleCNICChange = (e) => {
        const val = e.target.value.replace(/\D/g, '').slice(0, 13);
        handleFieldChange('cnic', val);
    };

    const validateForm = () => {
        const newErrors = {
            name: validateField('name', guardianData.name),
            cnic: validateField('cnic', guardianData.cnic),
            relation: validateField('relation', guardianData.relation),
        };
        
        setErrors(newErrors);
        setTouched({ name: true, cnic: true, relation: true });
        
        return Object.keys(newErrors).every(key => !newErrors[key]);
    };

    const handleSubmit = async () => {
        if (!validateForm()) {
            alert('Please fix the errors in the form');
            return;
        }

        setIsSubmitting(true);
        try {
            const payload = prepareProfileForBackend(profileData);
            await saveApplicantProfile(payload, token);
            if (user?.user_id) clearFormDraft(user.user_id, 'profile');
            alert('Guardian details saved to database successfully!');
        } catch (error) {
            console.error('Failed to save guardian details:', error);
            alert('Failed to save: ' + (error.response?.data?.message || error.message));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="tab-content-area fade-in" style={readOnly ? { pointerEvents: 'none', opacity: 0.92 } : undefined}>
            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><ShieldIcon /></div>
                    <h2 className="section-title">Guardian Information</h2>
                </div>
                
                <div className="info-banner compact">
                    <span>ℹ️</span>
                    <span>Guardian information is required for students under 18 years of age.</span>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Guardian Name <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="guardianName"
                            className={getInputClass('name')}
                            placeholder="Full Name" 
                            value={guardianData.name || ''} 
                            onChange={(e) => handleFieldChange('name', e.target.value)}
                            onBlur={() => handleBlur('name')}
                        />
                        {touched.name && errors.name && (
                            <div className="error-message">{errors.name}</div>
                        )}
                    </div>

                    <div className="field-group">
                        <label className="field-label">Relation <span className="required">*</span></label>
                        <select 
                            name="guardianRelation"
                            className={getSelectClass('relation')}
                            value={guardianData.relation || ''} 
                            onChange={(e) => handleFieldChange('relation', e.target.value)}
                            onBlur={() => handleBlur('relation')}
                        >
                            <option value="">Select Relation</option>
                            <option value="father">Father</option>
                            <option value="mother">Mother</option>
                            <option value="brother">Brother</option>
                            <option value="sister">Sister</option>
                            <option value="grandfather">Grandfather</option>
                            <option value="grandmother">Grandmother</option>
                            <option value="uncle">Uncle</option>
                            <option value="aunt">Aunt</option>
                            <option value="other">Other</option>
                        </select>
                        {touched.relation && errors.relation && (
                            <div className="error-message">{errors.relation}</div>
                        )}
                    </div>
                </div>

                <div className="field-group">
                    <label className="field-label">Guardian CNIC <span className="required">*</span></label>
                    <input 
                        type="text" 
                        name="guardianCnic"
                        className={getInputClass('cnic')}
                        placeholder="0000000000000" 
                        value={guardianData.cnic || ''} 
                        onChange={handleCNICChange}
                        onBlur={() => handleBlur('cnic')}
                    />
                    {touched.cnic && errors.cnic && (
                        <div className="error-message">{errors.cnic}</div>
                    )}
                    <p className="helper-text">Enter 13-digit CNIC without dashes</p>
                </div>
            </div>

            <div className="form-actions">
                {!readOnly && (
                <button className="btn-save" onClick={handleSubmit} disabled={isSubmitting}>
                    {isSubmitting ? 'Saving...' : 'Submit Details'}
                </button>
                )}
            </div>
        </div>
    );
};

export default GuardianDetailsTab;