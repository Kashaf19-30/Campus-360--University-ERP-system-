import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestPasswordReset } from '../services/authService';
import { MailIcon } from '../Icons';

const ForgotPasswordPage = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [devResetLink, setDevResetLink] = useState('');
    const [devToken, setDevToken] = useState('');

    const handleReset = async (e) => {
        e.preventDefault();
        if (!email) {
            setError('Please enter your email.');
            return;
        }
        setLoading(true);
        setError('');
        setMessage('');
        setDevResetLink('');
        setDevToken('');
        try {
            const data = await requestPasswordReset(email);
            setMessage(data.message || 'If an account exists for this email, a reset link has been sent.');
            if (data.reset_link) {
                setDevResetLink(data.reset_link);
            }
            if (data.reset_token) {
                setDevToken(data.reset_token);
            }
        } catch (err) {
            setError(err.response?.data?.email?.[0] || err.response?.data?.error || 'Unable to process request.');
        } finally {
            setLoading(false);
        }
    };

    const openResetPage = () => {
        if (devToken) {
            navigate(`/reset-password?token=${encodeURIComponent(devToken)}`);
            return;
        }
        if (devResetLink) {
            window.location.href = devResetLink;
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
                        <h2 style={{ marginTop: '20px' }}>Reset Your Password</h2>
                        <p className="subtitle">
                            Enter your email. In development, a reset link appears below (email is sent once SMTP is configured).
                        </p>

                        <form onSubmit={handleReset}>
                            <div className="form-group" style={{ marginBottom: '25px' }}>
                                <label>Email Address <span className="required">*</span></label>
                                <div className="input-wrapper">
                                    <div className="input-icon"><MailIcon /></div>
                                    <input
                                        type="email"
                                        className="form-input-with-icon"
                                        placeholder="yourname@campus.edu"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        disabled={loading}
                                    />
                                </div>
                            </div>

                            {error && <div className="api-error-message">{error}</div>}
                            {message && <div className="auth-success-message">{message}</div>}

                            {(devResetLink || devToken) && (
                                <div className="auth-reset-link-panel">
                                    <p>Development reset link (configure SMTP in production):</p>
                                    {devResetLink && (
                                        <a
                                            href={devResetLink}
                                            className="auth-reset-link-url"
                                            onClick={(e) => { e.preventDefault(); openResetPage(); }}
                                        >
                                            {devResetLink}
                                        </a>
                                    )}
                                    <button type="button" className="login-btn-full" onClick={openResetPage}>
                                        Open reset page
                                    </button>
                                </div>
                            )}

                            <button type="submit" className="login-btn-full" disabled={loading}>
                                {loading ? 'Sending...' : 'SEND RESET LINK'}
                            </button>
                        </form>

                        <div className="register-link">
                            Don&apos;t have an account?{' '}
                            <button type="button" className="link-btn" onClick={() => navigate('/signup')}>
                                Register Now
                            </button>
                        </div>

                        <button type="button" className="back-home-btn" onClick={() => navigate('/login')}>
                            ← Back to Login
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ForgotPasswordPage;
