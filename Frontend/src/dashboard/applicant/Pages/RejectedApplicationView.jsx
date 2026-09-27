import React from 'react';
import { LogOutIcon } from '../../Icons';

const RejectedApplicationView = ({ onLogout, username, rejectionReason }) => (
    <div className="dashboard-layout fade-in" style={{ minHeight: '100vh' }}>
        <main className="dashboard-main" style={{ marginLeft: 0, width: '100%' }}>
            <header className="dashboard-header">
                <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <img src="/campus360-logo.png" alt="Campus 360" style={{ height: '36px', objectFit: 'contain', borderRadius: '5px' }} />
                    <div className="header-logo-text" style={{ fontWeight: '700', fontSize: '1.25rem', color: 'var(--text-primary)' }}>
                        Campus 360
                    </div>
                </div>
                <div className="header-right">
                    <button className="btn-verify" onClick={onLogout} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <LogOutIcon /> Logout
                    </button>
                </div>
            </header>

            <div className="dashboard-content-wrapper" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 140px)' }}>
                <div className="form-card" style={{ maxWidth: '560px', textAlign: 'center', padding: '48px 32px' }}>
                    <div style={{
                        width: '72px', height: '72px', borderRadius: '50%',
                        background: '#fef2f2', color: '#dc2626',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        margin: '0 auto 24px', fontSize: '2rem', fontWeight: '700',
                    }}>
                        ✕
                    </div>
                    <h1 style={{ fontSize: '1.5rem', color: 'var(--text-primary)', marginBottom: '12px' }}>
                        Application Rejected
                    </h1>
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '8px' }}>
                        Kindly Contact in University
                    </p>
                    {rejectionReason && (
                        <p style={{ fontSize: '0.95rem', color: 'var(--text-tertiary)', lineHeight: 1.5, marginTop: '12px', padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                            <strong>Reason:</strong> {rejectionReason}
                        </p>
                    )}
                    {username && (
                        <p style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)', marginTop: '16px' }}>
                            Account: {username}
                        </p>
                    )}
                </div>
            </div>
        </main>
    </div>
);

export default RejectedApplicationView;
