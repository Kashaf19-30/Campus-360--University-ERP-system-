// src/dashboard/applicant/ProfileTabs/PersonalDetailsTab.jsx
import React, { useRef, useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { saveApplicantProfile, prepareProfileForBackend } from '../../../services/admissionService';
import { clearFormDraft } from '../../../utils/formDraft';
import { UserIcon, CameraIcon, PhoneIcon, CalendarIcon } from '../../Icons';
import { 
    getNameError, 
    getCNICError, 
    getPhoneError, 
    getDOBError,
    isValidName,
    isValidCNIC,
    isValidPhone,
    isValidDOB
} from '../../../utils/validation';

const PersonalDetailsTab = ({ profileData, updateProfile, readOnly = false }) => {
    const { token, user } = useAuth();
    const fileInputRef = useRef(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});

    const validateField = (name, value) => {
        switch (name) {
            case 'firstName':
                return getNameError(value, 'First name');
            case 'lastName':
                return getNameError(value, 'Last name');
            case 'fatherName':
                return getNameError(value, 'Father name');
            case 'cnic':
                return getCNICError(value);
            case 'cellPhone':
                return getPhoneError(value);
            case 'dob':
                return getDOBError(value);
            case 'gender':
                if (!value) return 'Gender is required';
                return '';
            case 'religion':
                if (!value) return 'Religion is required';
                return '';
            case 'nationality':
                if (!value) return 'Nationality is required';
                return '';
            case 'maritalStatus':
                if (!value) return 'Marital status is required';
                return '';
            default:
                return '';
        }
    };

    const handleFieldChange = (name, value) => {
        updateProfile(name, value);
        const error = validateField(name, value);
        setErrors(prev => ({ ...prev, [name]: error }));
    };

    const handleBlur = (name) => {
        setTouched(prev => ({ ...prev, [name]: true }));
        const error = validateField(name, profileData[name]);
        setErrors(prev => ({ ...prev, [name]: error }));
    };

    const getFieldStatus = (name) => {
        if (!touched[name]) return null;
        if (errors[name]) return 'error';
        if (profileData[name]) return 'success';
        return null;
    };

    const getInputClass = (name) => {
        const status = getFieldStatus(name);
        if (status === 'error') return 'field-input error';
        if (status === 'success') return 'field-input success';
        return 'field-input';
    };

    const getSelectClass = (name) => {
        const status = getFieldStatus(name);
        if (status === 'error') return 'field-input field-select error';
        if (status === 'success') return 'field-input field-select success';
        return 'field-input field-select';
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            if (file.size > 1048576) return alert("File size must be ≤ 1 MB");
            const reader = new FileReader();
            reader.onloadend = () => updateProfile('profileImage', reader.result);
            reader.readAsDataURL(file);
        }
    };

    const validateForm = () => {
        const newErrors = {
            firstName: validateField('firstName', profileData.firstName),
            lastName: validateField('lastName', profileData.lastName),
            fatherName: validateField('fatherName', profileData.fatherName),
            cnic: validateField('cnic', profileData.cnic),
            cellPhone: validateField('cellPhone', profileData.cellPhone),
            dob: validateField('dob', profileData.dob),
            gender: validateField('gender', profileData.gender),
            religion: validateField('religion', profileData.religion),
            nationality: validateField('nationality', profileData.nationality),
            maritalStatus: validateField('maritalStatus', profileData.maritalStatus),
        };
        
        setErrors(newErrors);
        
        // Mark all fields as touched
        const allTouched = {};
        Object.keys(newErrors).forEach(key => { allTouched[key] = true; });
        setTouched(allTouched);
        
        return Object.keys(newErrors).every(key => !newErrors[key]);
    };

    const handleUpdate = async () => {
        if (!validateForm()) {
            alert('Please fix the errors in the form');
            const firstError = Object.keys(errors).find(key => errors[key]);
            if (firstError) {
                const element = document.querySelector(`[name="${firstError}"]`);
                element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        setIsSubmitting(true);
        try {
            const payload = prepareProfileForBackend(profileData);
            await saveApplicantProfile(payload, token);
            if (user?.user_id) clearFormDraft(user.user_id, 'profile');
            alert('Personal details saved to database successfully!');
        } catch (error) {
            console.error('Failed to save:', error);
            const data = error.response?.data;
            let msg = error.message;
            if (data && typeof data === 'object') {
                msg = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`).join('\n');
            }
            alert('Failed to save: ' + msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleCNICChange = (e) => {
        const val = e.target.value.replace(/\D/g, '').slice(0, 13);
        handleFieldChange('cnic', val);
    };

    const handlePhoneChange = (e) => {
        const val = e.target.value.replace(/\D/g, '').slice(0, 11);
        handleFieldChange('cellPhone', val);
    };

    return (
        <div className="form-card fade-in" style={readOnly ? { pointerEvents: 'none', opacity: 0.92 } : undefined}>
            <div className="profile-upload-section">
                <div className="profile-upload-wrapper" title="Upload Photo (optional)" onClick={() => !readOnly && fileInputRef.current?.click()}>
                    {profileData.profileImage && String(profileData.profileImage).startsWith('data:image') ? (
                        <img src={profileData.profileImage} alt="Upload" className="profile-upload-avatar" />
                    ) : (
                        <div className="profile-upload-avatar avatar-initials" style={{ width: 120, height: 120, fontSize: '2rem' }}>
                            {(profileData.firstName?.[0] || profileData.username?.[0] || 'U').toUpperCase()}
                        </div>
                    )}
                    <div className="profile-upload-icon"><CameraIcon /></div>
                    <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept="image/*" onChange={handleImageChange} />
                </div>
            </div>

            <div className="two-column-grid">
                <div className="column">
                    {/* First Name */}
                    <div className="field-group">
                        <label className="field-label">First Name <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="firstName"
                            className={getInputClass('firstName')}
                            placeholder="First Name" 
                            value={profileData.firstName || ''} 
                            onChange={(e) => handleFieldChange('firstName', e.target.value)}
                            onBlur={() => handleBlur('firstName')}
                        />
                        {touched.firstName && errors.firstName && (
                            <div className="error-message">{errors.firstName}</div>
                        )}
                    </div>

                    {/* Last Name */}
                    <div className="field-group">
                        <label className="field-label">Last Name <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="lastName"
                            className={getInputClass('lastName')}
                            placeholder="Last Name" 
                            value={profileData.lastName || ''} 
                            onChange={(e) => handleFieldChange('lastName', e.target.value)}
                            onBlur={() => handleBlur('lastName')}
                        />
                        {touched.lastName && errors.lastName && (
                            <div className="error-message">{errors.lastName}</div>
                        )}
                    </div>

                    {/* Father Name */}
                    <div className="field-group">
                        <label className="field-label">Father Name <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="fatherName"
                            className={getInputClass('fatherName')}
                            placeholder="Father Name" 
                            value={profileData.fatherName || ''} 
                            onChange={(e) => handleFieldChange('fatherName', e.target.value)}
                            onBlur={() => handleBlur('fatherName')}
                        />
                        {touched.fatherName && errors.fatherName && (
                            <div className="error-message">{errors.fatherName}</div>
                        )}
                    </div>

                    {/* Date of Birth */}
                    <div className="field-group">
                        <label className="field-label">Date of Birth <span className="required">*</span></label>
                        <input 
                            type="date" 
                            name="dob"
                            className={getInputClass('dob')}
                            value={profileData.dob || ''} 
                            onChange={(e) => handleFieldChange('dob', e.target.value)}
                            onBlur={() => handleBlur('dob')}
                        />
                        {touched.dob && errors.dob && (
                            <div className="error-message">{errors.dob}</div>
                        )}
                    </div>

                    {/* Religion */}
                    <div className="field-group">
                        <label className="field-label">Religion <span className="required">*</span></label>
                        <select 
                            name="religion"
                            className={getSelectClass('religion')}
                            value={profileData.religion || ''} 
                            onChange={(e) => handleFieldChange('religion', e.target.value)}
                            onBlur={() => handleBlur('religion')}
                        >
                            <option value="">Select Religion</option>
                            <option value="islam">Islam</option>
                            <option value="christianity">Christianity</option>
                            <option value="hinduism">Hinduism</option>
                            <option value="other">Other</option>
                        </select>
                        {touched.religion && errors.religion && (
                            <div className="error-message">{errors.religion}</div>
                        )}
                    </div>

                    {/* Cell Phone */}
                    <div className="field-group">
                        <label className="field-label">Cell Phone <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="cellPhone"
                            className={getInputClass('cellPhone')}
                            placeholder="03000000000" 
                            value={profileData.cellPhone || ''} 
                            onChange={handlePhoneChange}
                            onBlur={() => handleBlur('cellPhone')}
                        />
                        {touched.cellPhone && errors.cellPhone && (
                            <div className="error-message">{errors.cellPhone}</div>
                        )}
                        <p className="helper-text">Enter 11-digit phone number (e.g., 03001234567)</p>
                    </div>
                </div>

                <div className="column">
                    {/* Gender */}
                    <div className="field-group">
                        <label className="field-label">Gender <span className="required">*</span></label>
                        <select 
                            name="gender"
                            className={getSelectClass('gender')}
                            value={profileData.gender || ''} 
                            onChange={(e) => handleFieldChange('gender', e.target.value)}
                            onBlur={() => handleBlur('gender')}
                        >
                            <option value="">Select Gender</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="other">Other</option>
                        </select>
                        {touched.gender && errors.gender && (
                            <div className="error-message">{errors.gender}</div>
                        )}
                    </div>

                    {/* CNIC */}
                    <div className="field-group">
                        <label className="field-label">CNIC <span className="required">*</span></label>
                        <input 
                            type="text" 
                            name="cnic"
                            className={getInputClass('cnic')}
                            placeholder="1234512345671" 
                            value={profileData.cnic || ''} 
                            onChange={handleCNICChange}
                            onBlur={() => handleBlur('cnic')}
                        />
                        {touched.cnic && errors.cnic && (
                            <div className="error-message">{errors.cnic}</div>
                        )}
                        <p className="helper-text">Enter 13-digit CNIC without dashes</p>
                    </div>

                    {/* Marital Status */}
                    <div className="field-group">
                        <label className="field-label">Marital Status <span className="required">*</span></label>
                        <select 
                            name="maritalStatus"
                            className={getSelectClass('maritalStatus')}
                            value={profileData.maritalStatus || ''} 
                            onChange={(e) => handleFieldChange('maritalStatus', e.target.value)}
                            onBlur={() => handleBlur('maritalStatus')}
                        >
                            <option value="">Select Status</option>
                            <option value="single">Single</option>
                            <option value="married">Married</option>
                        </select>
                        {touched.maritalStatus && errors.maritalStatus && (
                            <div className="error-message">{errors.maritalStatus}</div>
                        )}
                    </div>

                    {/* Nationality */}
                    <div className="field-group">
                        <label className="field-label">Nationality <span className="required">*</span></label>
                        <select 
                            name="nationality"
                            className={getSelectClass('nationality')}
                            value={profileData.nationality || ''} 
                            onChange={(e) => handleFieldChange('nationality', e.target.value)}
                            onBlur={() => handleBlur('nationality')}
                        >
                            <option value="">Select Nationality</option>
                            <option value="pakistani">Pakistani</option>
                            <option value="other">Other</option>
                        </select>
                        {touched.nationality && errors.nationality && (
                            <div className="error-message">{errors.nationality}</div>
                        )}
                    </div>
                </div>
            </div>

            <div className="form-actions">
                {!readOnly && (
                <button className="btn-update" onClick={handleUpdate} disabled={isSubmitting}>
                    {isSubmitting ? 'Saving...' : 'Submit Details'}
                </button>
                )}
            </div>
        </div>
    );
};

export default PersonalDetailsTab;