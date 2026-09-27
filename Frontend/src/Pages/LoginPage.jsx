// src/pages/LoginPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../services/authService';
import { loginRedirectPath } from '../routes/paths';
import { LockIcon, EyeIcon, EyeOffIcon, MailIcon } from '../Icons';
import PasswordValidation from '../components/PasswordValidation';
import { isValidEmail } from '../utils/validation';

const LoginPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [formData, setFormData] = useState({ email: '', password: '' });
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const [showLogin, setShowLogin] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [passwordFocused, setPasswordFocused] = useState(false);
    const [loading, setLoading] = useState(false);
    const [apiError, setApiError] = useState('');

    const { login } = useAuth();

    useEffect(() => {
        const timer = setTimeout(() => {
            setShowLogin(true);
        }, 300);
        return () => clearTimeout(timer);
    }, []);

    // Real-time validation for email
    const validateEmail = (value) => {
        if (!value) return 'Email is required';
        if (!isValidEmail(value)) return 'Please enter a valid email address';
        return '';
    };

    // Real-time validation for password
    const validatePassword = (value) => {
        if (!value) return 'Password is required';
        return '';
    };

    const handleFieldChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        
        // Clear API error when user starts typing
        if (apiError) setApiError('');
        
        // Real-time validation
        let error = '';
        if (field === 'email') error = validateEmail(value);
        if (field === 'password') error = validatePassword(value);
        
        setErrors(prev => ({ ...prev, [field]: error }));
    };

    const handleBlur = (field) => {
        setTouched(prev => ({ ...prev, [field]: true }));
        
        // Validate on blur
        let error = '';
        if (field === 'email') error = validateEmail(formData.email);
        if (field === 'password') error = validatePassword(formData.password);
        
        setErrors(prev => ({ ...prev, [field]: error }));
    };

    const validateForm = () => {
        const newErrors = {
            email: validateEmail(formData.email),
            password: validatePassword(formData.password)
        };
        
        setErrors(newErrors);
        setTouched({ email: true, password: true });
        
        return !newErrors.email && !newErrors.password;
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setApiError('');

        if (!validateForm()) {
            // Scroll to first error
            const firstErrorField = Object.keys(errors).find(key => errors[key]);
            if (firstErrorField) {
                const element = document.querySelector(`[name="${firstErrorField}"]`);
                if (element) element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        setLoading(true);
        
        try {
            // Dev-only mock login (never enabled in production builds)
            if (import.meta.env.DEV) {
                const mockUserStr = localStorage.getItem('mockUser');
                if (mockUserStr) {
                    const mockUser = JSON.parse(mockUserStr);
                    const emailMatches = mockUser.email === formData.email ||
                                        mockUser.email.split('@')[0] === formData.email;
                    if (emailMatches && mockUser.password === formData.password) {
                        const mockUserData = {
                            user_id: mockUser.user_id || mockUser.name,
                            username: mockUser.username || mockUser.name,
                            user_type: mockUser.user_type || 'applicant',
                        };
                        if (login) login(mockUserData, 'mock-token');
                        navigate(loginRedirectPath(mockUserData.user_type, location.state?.from));
                        setLoading(false);
                        return;
                    }
                }
            }

            // Actual API login
            const data = await loginUser(formData.email.trim(), formData.password);
            if (login) login(data.user, data.token);
            navigate(loginRedirectPath(data.user.user_type, location.state?.from));
            return;
            
        } catch (error) {
            const data = error.response?.data;
            const nonField = data?.non_field_errors?.[0];
            const invalidCreds =
                error.response?.status === 401 ||
                (error.response?.status === 400 &&
                    (nonField?.toLowerCase().includes('invalid') ||
                        nonField?.toLowerCase().includes('password') ||
                        nonField?.toLowerCase().includes('disabled')));

            if (invalidCreds) {
                const msg = typeof nonField === 'string' ? nonField : 'Invalid email or password. Please try again.';
                setApiError(msg);
                setErrors(prev => ({ ...prev, password: 'Invalid credentials' }));
            } else if (data) {
                const fieldMsg = data.email?.[0] || data.password?.[0];
                setApiError(data.message || fieldMsg || nonField || 'Login failed. Please try again.');
            } else {
                setApiError('Cannot connect to server. Please make sure the server is running.');
            }
        } finally {
            setLoading(false);
        }
    };

    const getFieldStatus = (fieldName) => {
        if (!touched[fieldName]) return null;
        if (errors[fieldName]) return 'error';
        if (formData[fieldName] && !errors[fieldName]) return 'success';
        return null;
    };

    const getInputClass = (fieldName) => {
        const status = getFieldStatus(fieldName);
        if (status === 'error') return 'form-input-with-icon error';
        if (status === 'success') return 'form-input-with-icon success';
        return 'form-input-with-icon';
    };

    return (
        <div className="auth-page">
            {!showLogin ? (
                <div className="fade-in" style={{ height: '100vh', width: '100%', pointerEvents: 'none' }} />
            ) : (
                <div className="auth-split-container fade-in">
                    <div className="auth-left-panel">
                        <div className="auth-left-content" style={{ textAlign: 'center' }}>
                            <h1 style={{ fontSize: '3rem', textShadow: '0 4px 10px rgba(0,0,0,0.3)' }}>Welcome To <br />Campus 360</h1>
                            <p style={{ marginTop: '20px', maxWidth: '300px', margin: '20px auto 0' }}>
                                Your gateway to academic excellence and campus management
                            </p>
                        </div>
                    </div>

                    <div className="auth-right-panel">
                        <div className="auth-card">
                            <div className="orbit-branding">
                                <span>Campus 360</span>
                            </div>
                            <h2 style={{ marginTop: '20px' }}>Sign in to Your Account</h2>
                            <p className="subtitle">Enter your credentials to access the portal</p>
                            
                            <form onSubmit={handleLogin}>
                                {/* Email Field */}
                                <div className="form-group">
                                    <label>Email Address <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><MailIcon /></div>
                                        <input 
                                            type="email"
                                            name="email"
                                            className={getInputClass('email')}
                                            placeholder="yourname@campus.edu" 
                                            value={formData.email}
                                            onChange={(e) => handleFieldChange('email', e.target.value)}
                                            onBlur={() => handleBlur('email')}
                                            disabled={loading}
                                        />
                                    </div>
                                    {touched.email && errors.email && (
                                        <div className="error-message">{errors.email}</div>
                                    )}
                                </div>
                                
                                {/* Password Field */}
                                <div className="form-group">
                                    <label>Password <span className="required">*</span></label>
                                    <div className="input-wrapper">
                                        <div className="input-icon"><LockIcon /></div>
                                        <input 
                                            type={showPassword ? "text" : "password"}
                                            name="password"
                                            className={getInputClass('password')}
                                            placeholder="••••••••" 
                                            value={formData.password}
                                            onChange={(e) => handleFieldChange('password', e.target.value)}
                                            onFocus={() => setPasswordFocused(true)}
                                            onBlur={() => {
                                                setPasswordFocused(false);
                                                handleBlur('password');
                                            }}
                                            disabled={loading}
                                        />
                                        <button 
                                            type="button" 
                                            className="password-toggle"
                                            onClick={() => setShowPassword(!showPassword)}
                                            disabled={loading}
                                        >
                                            {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                                        </button>
                                    </div>
                                    {touched.password && errors.password && (
                                        <div className="error-message">{errors.password}</div>
                                    )}
                                    <PasswordValidation password={formData.password} isVisible={passwordFocused} />
                                </div>

                                {/* Forgot Password */}
                                <div className="checkbox-row">
                                    <button 
                                        type="button"
                                        className="forgot-password-link"
                                        onClick={() => navigate('/forgot-password')}
                                        disabled={loading}
                                    >
                                        Forgot Password?
                                    </button>
                                </div>

                                {/* API Error Message */}
                                {apiError && (
                                    <div className="api-error-message">
                                        {apiError}
                                    </div>
                                )}

                                {/* Submit Button */}
                                <button 
                                    type="submit" 
                                    className="login-btn-full" 
                                    disabled={loading}
                                >
                                    {loading ? (
                                        <span className="btn-loading">
                                            <span className="spinner-small"></span>
                                            Signing in...
                                        </span>
                                    ) : (
                                        'Sign In'
                                    )}
                                </button>
                            </form>

                            {/* Register Link */}
                            <div className="register-link">
                                Don't have an account?{' '}
                                <button 
                                    type="button"
                                    className="link-btn"
                                    onClick={() => navigate('/signup')}
                                >
                                    Register Now
                                </button>
                            </div>
                            
                            {/* Back to Home Button */}
                            <button 
                                type="button"
                                className="back-home-btn"
                                onClick={() => navigate('/')}
                            >
                                ← Back to Home
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LoginPage;