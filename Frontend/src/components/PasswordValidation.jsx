// src/components/PasswordValidation.jsx
import React from 'react';

const PasswordValidation = ({ password, isVisible }) => {
    if (password === undefined) return null;
    
    const criteria = [
        { id: 'length', label: 'Minimum 8 characters', met: password.length >= 8 },
        { id: 'upperlower', label: 'Uppercase + lowercase', met: /[A-Z]/.test(password) && /[a-z]/.test(password) },
        { id: 'number', label: 'Number', met: /[0-9]/.test(password) },
        { id: 'symbol', label: 'Special character', met: /[^A-Za-z0-9]/.test(password) }
    ];
    
    const allMet = criteria.every(c => c.met);
    
    return (
        <div className={`password-floating-helper ${isVisible ? 'visible' : ''}`}>
            {password.length > 0 && allMet ? (
                <div className="strong-password-success" style={{ margin: 0 }}>Password looks good ✔</div>
            ) : (
                <ul className="password-criteria-list">
                    {criteria.map(c => (
                         <li key={`${c.id}-${c.met}`} className={`password-criteria-item ${c.met ? 'criteria-met' : 'criteria-unmet'}`}>
                             <span style={{ fontWeight: 'bold' }}>{c.met ? '✓' : '✗'}</span> <span>{c.label}</span>
                         </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default PasswordValidation;