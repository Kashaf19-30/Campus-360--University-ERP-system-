import React, { useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { completeTeacherOnboarding } from '../../../services/facultyService';
import { LoadingSpinner } from '../../shared/helpers';
import { UserIcon } from '../../Icons';
import {
    getCNICError, getPhoneError, getNameError,
} from '../../../utils/validation';

const TeacherOnboardingPage = ({ onComplete }) => {
    const { token } = useAuth();
    const [submitting, setSubmitting] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({});
    const [form, setForm] = useState({
        qualification: '',
        specialization: '',
        cnic: '',
        date_of_birth: '',
        gender: 'Male',
        phone_number: '',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        emergency_contact_relation: 'Parent',
        current_address: '',
        permanent_address: '',
    });

    const validate = () => {
        const errors = {};
        if (!form.qualification.trim()) errors.qualification = 'Qualification is required.';
        if (!form.specialization.trim()) errors.specialization = 'Specialization is required.';
        const cnicErr = getCNICError(form.cnic);
        if (cnicErr) errors.cnic = cnicErr;
        const phoneErr = getPhoneError(form.phone_number);
        if (phoneErr) errors.phone_number = phoneErr;
        const emPhoneErr = form.emergency_contact_phone ? getPhoneError(form.emergency_contact_phone) : '';
        if (emPhoneErr) errors.emergency_contact_phone = emPhoneErr;
        const emNameErr = form.emergency_contact_name ? getNameError(form.emergency_contact_name) : '';
        if (emNameErr) errors.emergency_contact_name = emNameErr;
        if (!form.date_of_birth) errors.date_of_birth = 'Date of birth is required.';
        if (!form.current_address.trim()) errors.current_address = 'Current address is required.';
        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validate()) {
            alert('Please fix the highlighted fields.');
            return;
        }
        setSubmitting(true);
        try {
            await completeTeacherOnboarding(form, token);
            alert('Profile completed! Welcome to Campus 360.');
            onComplete?.();
        } catch (err) {
            const data = err.response?.data;
            alert(data?.error || Object.values(data || {}).flat().join(', ') || 'Failed to save profile');
        } finally {
            setSubmitting(false);
        }
    };

    const renderError = (key) => fieldErrors[key] ? <span className="field-error">{fieldErrors[key]}</span> : null;

    return (
        <div className="page-container fade-in">
            <div className="form-card" style={{ maxWidth: '800px', margin: '30px auto', borderTop: '4px solid var(--primary)' }}>
                <div className="section-header">
                    <div className="section-header-icon"><UserIcon /></div>
                    <div>
                        <h2 className="section-title">Complete Your Faculty Profile</h2>
                        <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                            Department, designation, and office details were set when your account was created.
                        </p>
                    </div>
                </div>

                <form onSubmit={handleSubmit} style={{ marginTop: '24px' }}>
                    <div className="two-column-grid">
                        <div className="field-group">
                            <label className="field-label">Qualification *</label>
                            <input className="field-input" value={form.qualification} onChange={e => setForm({ ...form, qualification: e.target.value })} placeholder="e.g. MS Computer Science" required />
                            {renderError('qualification')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">Specialization *</label>
                            <input className="field-input" value={form.specialization} onChange={e => setForm({ ...form, specialization: e.target.value })} placeholder="e.g. Machine Learning" required />
                            {renderError('specialization')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">CNIC *</label>
                            <input className="field-input" value={form.cnic} onChange={e => setForm({ ...form, cnic: e.target.value.replace(/\D/g, '').slice(0, 13) })} placeholder="3520212345671" required />
                            {renderError('cnic')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">Date of Birth *</label>
                            <input type="date" className="field-input" value={form.date_of_birth} onChange={e => setForm({ ...form, date_of_birth: e.target.value })} required />
                            {renderError('date_of_birth')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">Gender</label>
                            <select className="field-input field-select" value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}>
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                        <div className="field-group">
                            <label className="field-label">Phone *</label>
                            <input className="field-input" value={form.phone_number} onChange={e => setForm({ ...form, phone_number: e.target.value.replace(/\D/g, '').slice(0, 11) })} placeholder="03001234567" required />
                            {renderError('phone_number')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">Emergency Contact Name</label>
                            <input className="field-input" value={form.emergency_contact_name} onChange={e => setForm({ ...form, emergency_contact_name: e.target.value })} />
                            {renderError('emergency_contact_name')}
                        </div>
                        <div className="field-group">
                            <label className="field-label">Emergency Phone</label>
                            <input className="field-input" value={form.emergency_contact_phone} onChange={e => setForm({ ...form, emergency_contact_phone: e.target.value.replace(/\D/g, '').slice(0, 11) })} />
                            {renderError('emergency_contact_phone')}
                        </div>
                        <div className="field-group" style={{ gridColumn: '1 / -1' }}>
                            <label className="field-label">Current Address *</label>
                            <input className="field-input" value={form.current_address} onChange={e => setForm({ ...form, current_address: e.target.value })} required />
                            {renderError('current_address')}
                        </div>
                        <div className="field-group" style={{ gridColumn: '1 / -1' }}>
                            <label className="field-label">Permanent Address</label>
                            <input className="field-input" value={form.permanent_address} onChange={e => setForm({ ...form, permanent_address: e.target.value })} placeholder="Same as current if blank" />
                        </div>
                    </div>
                    <div className="form-actions">
                        <button type="submit" className="btn-save" disabled={submitting}>
                            {submitting ? 'Saving...' : 'Complete Profile & Enter Dashboard'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default TeacherOnboardingPage;
