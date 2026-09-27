// src/dashboard/Pages/ChangePasswordPage.jsx
import React, { useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { changePassword } from '../../../services/authService';
import { LockIcon, EyeIcon, EyeOffIcon, CheckIcon } from '../../Icons';
import { isValidPassword, getPasswordError } from '../../../utils/validation';
import PasswordValidation from '../../../components/PasswordValidation';

const ChangePasswordPage = () => {
    const { token } = useAuth();
    const [formData, setFormData] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [passwordFocused, setPasswordFocused] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);

    const validateField = (name, value) => {
        switch (name) {
            case 'currentPassword':
                if (!value) return 'Current password is required';
                return '';
            case 'newPassword':
                return getPasswordError(value);
            case 'confirmPassword':
                if (!value) return 'Please confirm your password';
                if (value !== formData.newPassword) return 'Passwords do not match';
                return '';
            default:
                return '';
        }
    };

    const handleFieldChange = (name, value) => {
        setFormData(prev => ({ ...prev, [name]: value }));
        const error = validateField(name, value);
        setErrors(prev => ({ ...prev, [name]: error }));
        
        // Clear confirm password error when new password changes
        if (name === 'newPassword' && formData.confirmPassword) {
            const confirmError = formData.confirmPassword !== value ? 'Passwords do not match' : '';
            setErrors(prev => ({ ...prev, confirmPassword: confirmError }));
        }
    };

    const handleBlur = (name) => {
        setTouched(prev => ({ ...prev, [name]: true }));
        const error = validateField(name, formData[name]);
        setErrors(prev => ({ ...prev, [name]: error }));
    };

    const getFieldStatus = (name) => {
        if (!touched[name]) return null;
        if (errors[name]) return 'error';
        if (formData[name]) return 'success';
        return null;
    };

    const getInputClass = (name) => {
        const status = getFieldStatus(name);
        if (status === 'error') return 'field-input error';
        if (status === 'success') return 'field-input success';
        return 'field-input';
    };

    const validateForm = () => {
        const newErrors = {
            currentPassword: validateField('currentPassword', formData.currentPassword),
            newPassword: validateField('newPassword', formData.newPassword),
            confirmPassword: validateField('confirmPassword', formData.confirmPassword),
        };
        
        setErrors(newErrors);
        setTouched({ currentPassword: true, newPassword: true, confirmPassword: true });
        
        return Object.keys(newErrors).every(key => !newErrors[key]);
    };

    const handleSubmit = async () => {
        if (!validateForm()) return;
        
        setIsSubmitting(true);
        try {
            await changePassword(formData.currentPassword, formData.newPassword, token);
            setSuccess(true);
            setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
            setTouched({});
            setTimeout(() => setSuccess(false), 5000);
        } catch (error) {
            const msg = error.response?.data?.error
                || error.response?.data?.old_password?.[0]
                || error.response?.data?.new_password?.[0]
                || 'Failed to change password. Please try again.';
            alert(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal">
                <div className="breadcrumb-minimal">DASHBOARD &gt; SETTINGS &gt; CHANGE PASSWORD</div>
                <h1 className="page-title-minimal">Change Password</h1>
            </div>

            <div className="form-card" style={{ maxWidth: '550px', margin: '0 auto' }}>
                <div className="section-header">
                    <div className="section-header-icon"><LockIcon /></div>
                    <h2 className="section-title">Update Your Password</h2>
                </div>

                <div className="info-banner compact">
                    <span>🔒</span>
                    <span>Choose a strong password with at least 8 characters, including uppercase, lowercase, number, and special character.</span>
                </div>

                {success && (
                    <div className="success-banner">
                        <CheckIcon />
                        <span>Password updated successfully!</span>
                    </div>
                )}

                <div className="field-group">
                    <label className="field-label">Current Password <span className="required">*</span></label>
                    <div className="input-wrapper">
                        <input 
                            type={showCurrentPassword ? "text" : "password"}
                            name="currentPassword"
                            className={getInputClass('currentPassword')}
                            placeholder="Enter current password" 
                            value={formData.currentPassword}
                            onChange={(e) => handleFieldChange('currentPassword', e.target.value)}
                            onBlur={() => handleBlur('currentPassword')}
                            disabled={isSubmitting}
                        />
                        <button type="button" className="password-toggle" onClick={() => setShowCurrentPassword(!showCurrentPassword)}>
                            {showCurrentPassword ? <EyeOffIcon /> : <EyeIcon />}
                        </button>
                    </div>
                    {touched.currentPassword && errors.currentPassword && <div className="error-message">{errors.currentPassword}</div>}
                </div>

                <div className="field-group">
                    <label className="field-label">New Password <span className="required">*</span></label>
                    <div className="input-wrapper">
                        <input 
                            type={showNewPassword ? "text" : "password"}
                            name="newPassword"
                            className={getInputClass('newPassword')}
                            placeholder="Enter new password" 
                            value={formData.newPassword}
                            onChange={(e) => handleFieldChange('newPassword', e.target.value)}
                            onFocus={() => setPasswordFocused(true)}
                            onBlur={() => {
                                setPasswordFocused(false);
                                handleBlur('newPassword');
                            }}
                            disabled={isSubmitting}
                        />
                        <button type="button" className="password-toggle" onClick={() => setShowNewPassword(!showNewPassword)}>
                            {showNewPassword ? <EyeOffIcon /> : <EyeIcon />}
                        </button>
                    </div>
                    {touched.newPassword && errors.newPassword && <div className="error-message">{errors.newPassword}</div>}
                    <PasswordValidation password={formData.newPassword} isVisible={passwordFocused} />
                </div>

                <div className="field-group">
                    <label className="field-label">Confirm New Password <span className="required">*</span></label>
                    <div className="input-wrapper">
                        <input 
                            type={showConfirmPassword ? "text" : "password"}
                            name="confirmPassword"
                            className={getInputClass('confirmPassword')}
                            placeholder="Confirm new password" 
                            value={formData.confirmPassword}
                            onChange={(e) => handleFieldChange('confirmPassword', e.target.value)}
                            onBlur={() => handleBlur('confirmPassword')}
                            disabled={isSubmitting}
                        />
                        <button type="button" className="password-toggle" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                            {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                        </button>
                    </div>
                    {touched.confirmPassword && errors.confirmPassword && <div className="error-message">{errors.confirmPassword}</div>}
                </div>

                <div className="form-actions" style={{ marginTop: '20px' }}>
                    <button className="btn-verify" onClick={() => { setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' }); setErrors({}); setTouched({}); }} disabled={isSubmitting}>
                        Clear
                    </button>
                    <button className="btn-save" onClick={handleSubmit} disabled={isSubmitting}>
                        {isSubmitting ? 'Updating...' : 'Update Password'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChangePasswordPage;