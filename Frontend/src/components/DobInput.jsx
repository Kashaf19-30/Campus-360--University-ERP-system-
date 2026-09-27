import React, { useState, useEffect } from 'react';

const CalendarIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
);

/**
 * Advanced DOB Input Component
 * Enforces university age requirements (18-50) and provides live feedback.
 */
const DobInput = ({ value, onChange, label = "Date of Birth", required = false, className = "" }) => {
    const [age, setAge] = useState(null);
    const [error, setError] = useState("");

    // University requirements
    const MIN_AGE = 18;
    const MAX_AGE = 50;

    useEffect(() => {
        if (!value) {
            setAge(null);
            setError("");
            return;
        }

        const today = new Date();
        const birthDate = new Date(value);
        
        // Basic Age Calculation
        let calculatedAge = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        // Exact birthday adjustment
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            calculatedAge--;
        }

        setAge(calculatedAge);

        // Validation against university policies
        if (calculatedAge < MIN_AGE) {
            setError(`Eligibility Warning: Minimum admission age is ${MIN_AGE} years.`);
        } else if (calculatedAge > MAX_AGE) {
            setError(`Eligibility Warning: Maximum admission age is ${MAX_AGE} years.`);
        } else {
            setError("");
        }
    }, [value]);

    // Max selectable date is today (cannot be born in the future)
    const todayStr = new Date().toISOString().split('T')[0];
    
    // Min selectable date is 100 years ago (historical limit)
    const minLimitDate = new Date();
    minLimitDate.setFullYear(minLimitDate.getFullYear() - 100);
    const minLimitStr = minLimitDate.toISOString().split('T')[0];

    return (
        <div className={`dob-input-container ${className}`} style={{ marginBottom: '20px', position: 'relative' }}>
            <label style={{ 
                display: 'block', 
                marginBottom: '8px', 
                fontSize: '0.9rem', 
                fontWeight: '600', 
                color: error ? '#ef4444' : '#1e293b' 
            }}>
                {label} {required && <span style={{ color: '#ef4444' }}>*</span>}
            </label>
            
            <div style={{ position: 'relative' }}>
                <div style={{ 
                    position: 'absolute', 
                    left: '12px', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    color: error ? '#ef4444' : '#64748b', 
                    display: 'flex',
                    zIndex: 2 
                }}>
                    <CalendarIcon />
                </div>
                <input 
                    type="date" 
                    value={value || ''}
                    max={todayStr}
                    min={minLimitStr}
                    onChange={(e) => onChange(e.target.value)}
                    required={required}
                    style={{ 
                        width: '100%', 
                        padding: '12px 12px 12px 42px', 
                        borderRadius: '10px', 
                        border: `1.5px solid ${error ? '#fca5a5' : '#e2e8f0'}`, 
                        backgroundColor: error ? '#fff1f2' : '#ffffff',
                        fontSize: '0.95rem',
                        color: '#1e293b',
                        transition: 'all 0.2s ease',
                        boxShadow: error ? '0 0 0 3px rgba(239, 68, 68, 0.08)' : 'none',
                        outline: 'none'
                    }}
                    onFocus={(e) => {
                        if (!error) e.target.style.borderColor = '#3B5BDB';
                        if (!error) e.target.style.boxShadow = '0 0 0 3px rgba(59, 91, 219, 0.1)';
                    }}
                    onBlur={(e) => {
                        if (!error) e.target.style.borderColor = '#e2e8f0';
                        if (!error) e.target.style.boxShadow = 'none';
                    }}
                />
            </div>
            
            <div style={{ 
                marginTop: '8px', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                minHeight: '20px' 
            }}>
                {error ? (
                    <span style={{ color: '#ef4444', fontSize: '0.8rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                         {error}
                    </span>
                ) : age !== null ? (
                    <span style={{ 
                        color: '#10b981', 
                        fontSize: '0.85rem', 
                        fontWeight: '700',
                        background: '#dcfce7',
                        padding: '2px 8px',
                        borderRadius: '4px'
                    }}>
                        Calculated Age: {age} Years
                    </span>
                ) : (
                    <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Please select your birth date using the calendar.</span>
                )}
            </div>
        </div>
    );
};

export default DobInput;
