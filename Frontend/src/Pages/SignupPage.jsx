// src/pages/SignupPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { registerUser } from '../services/authService';
import { getPublicAdmissionSettings } from '../services/admissionService';
import { UserIcon, CalendarIcon, MailIcon, LockIcon, EyeIcon, EyeOffIcon } from '../Icons';
import PasswordValidation from '../components/PasswordValidation';
import { 
    getNameError,
    getCNICError,
    getPhoneError,
    getUsernameError,
    getEmailError,
    getDOBError,       
    getPasswordError
} from '../utils/validation';

const SignupPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [admissionsOpen, setAdmissionsOpen] = useState(true);
    const [settingsLoading, setSettingsLoading] = useState(true);
    const [formData, setFormData] = useState({ 
        firstName: '', lastName: '', gender: '', dob: '', cnic: '', phone: '', username: '', email: '', password: '', confirm: '' 
    });
    
    const [submitErrors, setSubmitErrors] = useState({});
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [passwordFocused, setPasswordFocused] = useState(false);
    const [confirmPasswordError, setConfirmPasswordError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        let active = true;
        getPublicAdmissionSettings()
            .then((data) => {
                if (active) setAdmissionsOpen(data?.is_open !== false);
            })
            .catch(() => {
                if (active) setAdmissionsOpen(true);
            })
            .finally(() => {
                if (active) setSettingsLoading(false);
            });
        return () => { active = false; };
    }, []);

    
    const handleFirstNameChange = (e) => {
        const value = e.target.value;
        if (/^[A-Za-z\s]*$/.test(value)) {
            setFormData({...formData, firstName: value});
        }
    };

    const handleLastNameChange = (e) => {
        const value = e.target.value;
        if (/^[A-Za-z\s]*$/.test(value)) {
            setFormData({...formData, lastName: value});
        }
    };

    const handleCNICChange = (e) => {
        const value = e.target.value;
        const digitsOnly = value.replace(/\D/g, '').slice(0, 13);
        setFormData({...formData, cnic: digitsOnly});
    };

    const handlePhoneChange = (e) => {
        const value = e.target.value;
        const digitsOnly = value.replace(/\D/g, '').slice(0, 11);
        setFormData({...formData, phone: digitsOnly});
    };

    const handleUsernameChange = (e) => {
        const value = e.target.value;
        if (/^[a-zA-Z0-9_.]*$/.test(value)) {
            setFormData({...formData, username: value});
        }
    };

    const handleEmailChange = (e) => {
        setFormData({...formData, email: e.target.value});
    };

    const handleDOBChange = (e) => {
        setFormData({...formData, dob: e.target.value});
    };


    const handleSignup = async (e) => {
        e.preventDefault();

        // Use validation.js functions ONLY at submit time
        const errors = {
            firstName: getNameError(formData.firstName),
            lastName: getNameError(formData.lastName),
            cnic: getCNICError(formData.cnic),
            phone: getPhoneError(formData.phone),
            username: getUsernameError(formData.username),
            email: getEmailError(formData.email),
            dob: getDOBError(formData.dob),       
            password: getPasswordError(formData.password)
        };

        setSubmitErrors(errors);

        const hasErrors = Object.values(errors).some(error => error !== '');
        
        if (hasErrors) {
            alert('Please fix the errors in the form');
            return;
        }

        if (formData.gender === '') {
            alert('Please select gender');
            return;
        }

        if (formData.password !== formData.confirm) {
            setConfirmPasswordError('Passwords do not match');
            return;
        }

        if (submitting) return;

        setSubmitting(true);
        try {
            await registerUser(
                formData.username,
                formData.email,
                formData.password,
                formData.confirm,
                {
                    firstName: formData.firstName,
                    lastName: formData.lastName,
                    gender: formData.gender,
                    dob: formData.dob,
                    cnic: formData.cnic,
                    phone: formData.phone,
                }
            );
            alert('Account created! Please log in.');
            navigate('/login', { state: { from: location.state?.from } });
        } catch (error) {
            const data = error.response?.data;
            if (data?.email) {
                alert(Array.isArray(data.email) ? data.email[0] : data.email);
            } else if (data?.username) {
                alert(Array.isArray(data.username) ? data.username[0] : data.username);
            } else if (data?.confirm_password) {
                alert(Array.isArray(data.confirm_password) ? data.confirm_password[0] : data.confirm_password);
            } else if (data?.password) {
                alert(Array.isArray(data.password) ? data.password[0] : data.password);
            } else if (data?.error) {
                alert(data.error);
            } else if (data?.message) {
                alert(data.message);
            } else if (data && typeof data === 'object') {
                const msg = Object.entries(data)
                    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`)
                    .join('\n');
                alert(msg || 'Registration failed. Please try again.');
            } else if (error.message === 'Network Error') {
                alert('Cannot reach the server. Make sure Django is running.');
            } else {
                alert('Registration failed. Please try again.');
            }
        } finally {
            setSubmitting(false);
        }
    };

    if (settingsLoading) {
        return (
            <div className="auth-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
                <p>Loading...</p>
            </div>
        );
    }

    if (!admissionsOpen) {
        return (
            <div className="auth-page">
                <div className="auth-split-container fade-in">
                    <div className="auth-left-panel">
                        <div className="auth-left-content" style={{ textAlign: 'center' }}>
                            <h1 style={{ fontSize: '3rem', textShadow: '0 4px 10px rgba(0,0,0,0.3)' }}>Admission Closed</h1>
                            <p style={{ marginTop: '20px', maxWidth: '320px' }}>
                                New registrations are not being accepted at this time.
                            </p>
                        </div>
                    </div>
                    <div className="auth-right-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
                        <div className="form-card" style={{ maxWidth: '480px', width: '100%', textAlign: 'center', padding: '48px 32px' }}>
                            <div style={{
                                width: '72px', height: '72px', borderRadius: '50%',
                                background: '#fff7ed', color: '#ea580c',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                margin: '0 auto 24px', fontSize: '2rem', fontWeight: '700',
                            }}>
                                !
                            </div>
                            <h1 style={{ fontSize: '1.5rem', marginBottom: '12px' }}>Admission Closed</h1>
                            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '24px' }}>
                                Admissions are not open at this time. You cannot register a new account. Please contact the university admissions office for more information.
                            </p>
                            <button type="button" className="login-beautiful-btn" onClick={() => navigate('/login')} style={{ marginBottom: '12px' }}>
                                Back to Sign In
                            </button>
                            <button type="button" className="back-home-btn" onClick={() => navigate('/')}>
                                ← Back to Home
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-page">
            <div className="auth-split-container fade-in">
                <div className="auth-left-panel">
                    <div className="auth-left-content" style={{ textAlign: 'center' }}>
                        <h1 style={{ fontSize: '3rem', textShadow: '0 4px 10px rgba(0,0,0,0.3)' }}>Join the <br />Future</h1>
                        <p style={{ marginTop: '20px', maxWidth: '300px' }}>Apply now and become part of the University of Sialkot community.</p>
                    </div>
                </div>

                <div className="auth-right-panel" style={{ padding: '40px', overflowY: 'auto' }}>
                    <div className="registration-container" style={{ margin: '0 auto' }}>
                        <div className="instructions-card">
                            <h3>INSTRUCTIONS</h3>
                            <div className="instructions-list-container">
                                <div className="instruction-item">
                                    <div className="bullet-icon"></div>
                                    <p>Please enter your name as per written on the Matriculation certificate.</p>
                                </div>
                                <div className="instruction-item">
                                    <div className="bullet-icon"></div>
                                    <p>Please fill the form with original information.</p>
                                </div>
                                <div className="instruction-item">
                                    <div className="bullet-icon"></div>
                                    <p>Please enter authentic email and phone number for verification in next step.</p>
                                </div>
                                <div className="instruction-item">
                                    <div className="bullet-icon"></div>
                                    <p>You will not be able to change the information.</p>
                                </div>
                            </div>
                        </div>

                        <form onSubmit={handleSignup}>
                            <div className="form-grid">
                                {/* First Name */}
                                <div className="form-group">
                                    <label>First Name <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><UserIcon /></div>
                                        <input 
                                            type="text" 
                                            className="form-input-with-icon" 
                                            placeholder="First Name" 
                                            value={formData.firstName}
                                            onChange={handleFirstNameChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.firstName && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.firstName}</p>
                                    )}
                                </div>

                                {/* Last Name */}
                                <div className="form-group">
                                    <label>Last Name <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><UserIcon /></div>
                                        <input 
                                            type="text" 
                                            className="form-input-with-icon" 
                                            placeholder="Last Name" 
                                            value={formData.lastName}
                                            onChange={handleLastNameChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.lastName && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.lastName}</p>
                                    )}
                                </div>

                                {/* Gender */}
                                <div className="form-group">
                                    <label>Gender <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><UserIcon /></div>
                                        <select 
                                            className="form-input-with-icon" 
                                            required 
                                            onChange={(e) => setFormData({...formData, gender: e.target.value})}
                                        >
                                            <option value="">Select Gender</option>
                                            <option value="male">Male</option>
                                            <option value="female">Female</option>
                                            <option value="other">Other</option>
                                        </select>
                                    </div>
                                </div>

                                {/* Date of Birth */}
                                <div className="form-group">
                                    <label>Date of Birth <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><CalendarIcon /></div>
                                        <input 
                                            type="date" 
                                            className="form-input-with-icon" 
                                            required 
                                            value={formData.dob || ''}
                                            onChange={handleDOBChange}
                                            min="1950-01-01"
                                            max={(() => {
                                                const date = new Date();
                                                date.setFullYear(date.getFullYear() - 16);
                                                return date.toISOString().split('T')[0];
                                            })()}
                                        />
                                    </div>
                                    {submitErrors.dob && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.dob}</p>
                                    )}
                                </div>

                                {/* CNIC */}
                                <div className="form-group form-row-full">
                                    <label>CNIC <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <input 
                                            type="text" 
                                            className="form-input-with-icon" 
                                            placeholder="1234512345671" 
                                            value={formData.cnic}
                                            onChange={handleCNICChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.cnic && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.cnic}</p>
                                    )}
                                    <p className="helper-text">Enter CNIC without dashes (13 digits)</p>
                                </div>

                                {/* Phone Number */}
                                <div className="form-group form-row-full">
                                    <label>Phone Number <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <input 
                                            type="tel" 
                                            className="form-input-with-icon" 
                                            placeholder="03001234567" 
                                            value={formData.phone}
                                            onChange={handlePhoneChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.phone && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.phone}</p>
                                    )}
                                    <p className="helper-text">Enter 11 digits (e.g., 03001234567)</p>
                                </div>

                                {/* Username */}
                                <div className="form-group form-row-full">
                                    <label>Username <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><UserIcon /></div>
                                        <input 
                                            type="text" 
                                            className="form-input-with-icon" 
                                            placeholder="Choose a username" 
                                            value={formData.username}
                                            onChange={handleUsernameChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.username && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.username}</p>
                                    )}
                                    <p className="helper-text">Letters, numbers, underscore, dot (3-20 characters)</p>
                                </div>

                                {/* Email */}
                                <div className="form-group form-row-full">
                                    <label>Email Address <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><MailIcon /></div>
                                        <input 
                                            type="email" 
                                            className="form-input-with-icon" 
                                            placeholder="email@example.com" 
                                            value={formData.email}
                                            onChange={handleEmailChange}
                                            required 
                                        />
                                    </div>
                                    {submitErrors.email && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.email}</p>
                                    )}
                                    <p className="helper-text">Email will be used for login</p>
                                </div>

                                {/* Password */}
                                <div className="form-group">
                                    <label>Password <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><LockIcon /></div>
                                        <input 
                                            type={showPassword ? "text" : "password"} 
                                            className="form-input-with-icon" 
                                            placeholder="••••••••" 
                                            required 
                                            onChange={(e) => setFormData({...formData, password: e.target.value})} 
                                            onFocus={() => setPasswordFocused(true)} 
                                            onBlur={() => setPasswordFocused(false)} 
                                        />
                                        <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                                            {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                                        </button>
                                    </div>
                                    {submitErrors.password && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{submitErrors.password}</p>
                                    )}
                                    <PasswordValidation password={formData.password} isVisible={passwordFocused} />
                                </div>

                                {/* Confirm Password */}
                                <div className="form-group">
                                    <label>Confirm Password <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><LockIcon /></div>
                                        <input 
                                            type={showConfirmPassword ? "text" : "password"} 
                                            className="form-input-with-icon" 
                                            placeholder="••••••••" 
                                            required 
                                            onChange={(e) => {
                                                setFormData({...formData, confirm: e.target.value});
                                                setConfirmPasswordError('');
                                            }} 
                                        />
                                        <button type="button" className="password-toggle" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                                            {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                                        </button>
                                    </div>
                                    {confirmPasswordError && (
                                        <p style={{ color: 'red', fontSize: '12px', marginTop: '5px' }}>{confirmPasswordError}</p>
                                    )}
                                </div>
                            </div>

                            <button type="submit" className="register-button" disabled={submitting}>
                                {submitting ? 'REGISTERING...' : 'REGISTER'}
                            </button>
                        </form>

                        <div className="bottom-text">
                            Already have an account?
                            <button type="button" className="login-beautiful-btn" onClick={() => navigate('/login')}>
                                Sign In to Your Account
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SignupPage;