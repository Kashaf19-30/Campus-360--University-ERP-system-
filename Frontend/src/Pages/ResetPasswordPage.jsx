import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { confirmPasswordReset } from '../services/authService';
import PasswordValidation from '../components/PasswordValidation';
import { patterns } from '../utils/validation';
import { LockIcon, EyeIcon, EyeOffIcon } from '../Icons';

const ResetPasswordPage = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token') || '';

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [passwordFocused, setPasswordFocused] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!token) {
            setError('Invalid or missing reset link. Request a new one from the login page.');
            return;
        }
        if (!patterns.password.test(password)) {
            setError('Password must be at least 8 characters with uppercase, lowercase, number, and special character.');
            return;
        }
        if (password !== confirm) {
            setError('Passwords do not match.');
            return;
        }

        setLoading(true);
        try {
            const data = await confirmPasswordReset(token, password);
            setMessage(data.message || 'Password reset successful. You can now log in.');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setError(
                err.response?.data?.token?.[0]
                || err.response?.data?.new_password?.[0]
                || err.response?.data?.error
                || 'Unable to reset password. The link may have expired.'
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-split-container fade-in">
                <div className="auth-left-panel">
                    <div className="auth-left-content" style={{ textAlign: 'center' }}>
                        <h1 style={{ fontSize: '3rem', textShadow: '0 4px 10px rgba(0,0,0,0.3)' }}>Welcome To <br />Campus 360</h1>
                    </div>
                </div>

                <div className="auth-right-panel">
                    <div className="auth-card" style={{ margin: '0 auto', width: '100%', maxWidth: '400px' }}>
                        <div className="orbit-branding">Campus 360</div>
                        <h2 style={{ marginTop: '20px' }}>Set New Password</h2>
                        <p className="subtitle">Enter a new password for your account.</p>

                        {!token && (
                            <div className="api-error-message">
                                This reset link is invalid.{' '}
                                <Link to="/forgot-password" className="link-btn">Request a new link</Link>.
                            </div>
                        )}

                        <form onSubmit={handleSubmit}>
                            <div className="form-group" style={{ marginBottom: '20px' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--dark-gray)', marginBottom: '5px', display: 'block' }}>
                                    New Password
                                </label>
                                <div className="input-wrapper">
                                    <div className="input-icon"><LockIcon /></div>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        className="form-input-with-icon"
                                        placeholder="Enter new password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        onFocus={() => setPasswordFocused(true)}
                                        onBlur={() => setPasswordFocused(false)}
                                        disabled={!token}
                                    />
                                    <button
                                        type="button"
                                        className="password-toggle"
                                        onClick={() => setShowPassword(v => !v)}
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                                    </button>
                                </div>
                                {passwordFocused && <PasswordValidation password={password} isVisible={passwordFocused} />}
                            </div>

                            <div className="form-group" style={{ marginBottom: '25px' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--dark-gray)', marginBottom: '5px', display: 'block' }}>
                                    Confirm Password
                                </label>
                                <div className="input-wrapper">
                                    <div className="input-icon"><LockIcon /></div>
                                    <input
                                        type={showConfirm ? 'text' : 'password'}
                                        className="form-input-with-icon"
                                        placeholder="Confirm new password"
                                        required
                                        value={confirm}
                                        onChange={(e) => setConfirm(e.target.value)}
                                        disabled={!token}
                                    />
                                    <button
                                        type="button"
                                        className="password-toggle"
                                        onClick={() => setShowConfirm(v => !v)}
                                        tabIndex={-1}
                                    >
                                        {showConfirm ? <EyeOffIcon /> : <EyeIcon />}
                                    </button>
                                </div>
                            </div>

                            {error && <div className="api-error-message">{error}</div>}
                            {message && <div className="auth-success-message">{message}</div>}

                            <button type="submit" className="login-btn-full" disabled={loading || !token}>
                                {loading ? 'Saving...' : 'RESET PASSWORD'}
                            </button>
                        </form>

                        <button type="button" className="back-home-btn" onClick={() => navigate('/login')}>
                            ← Back to Login
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResetPasswordPage;
