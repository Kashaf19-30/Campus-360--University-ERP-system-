import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { getAcademicPolicy, updateAcademicPolicy } from '../../../services/academicsService';
import { PageHeader, LoadingSpinner, useToast } from '../../shared/helpers';
import { ShieldIcon } from '../../Icons';

const AcademicPolicyPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        min_sgpa_pass: '2.0',
        min_sgpa_probation: '2.0',
        min_cgpa_graduation: '2.0',
        max_consecutive_probation: '2',
        max_course_attempts: '3',
        min_attendance_percentage: '75',
        max_semester_credit_hours: '21',
        max_repeat_credit_hours: '21',
        auto_enroll_failed_prerequisites: true,
        allow_concurrent_prerequisite_enrollment: true,
        soft_prerequisite_enrollment: true,
    });

    useEffect(() => {
        if (!token) return;
        setLoading(true);
        getAcademicPolicy(token)
            .then((data) => {
                setForm({
                    min_sgpa_pass: String(data.min_sgpa_pass ?? '2.0'),
                    min_sgpa_probation: String(data.min_sgpa_probation ?? '2.0'),
                    min_cgpa_graduation: String(data.min_cgpa_graduation ?? '2.0'),
                    max_consecutive_probation: String(data.max_consecutive_probation ?? '2'),
                    max_course_attempts: String(data.max_course_attempts ?? '3'),
                    min_attendance_percentage: String(data.min_attendance_percentage ?? '75'),
                    max_semester_credit_hours: String(data.max_semester_credit_hours ?? '21'),
                    max_repeat_credit_hours: String(data.max_repeat_credit_hours ?? '21'),
                    auto_enroll_failed_prerequisites: data.auto_enroll_failed_prerequisites ?? true,
                    allow_concurrent_prerequisite_enrollment: data.allow_concurrent_prerequisite_enrollment ?? true,
                    soft_prerequisite_enrollment: data.soft_prerequisite_enrollment ?? true,
                });
            })
            .catch(() => showToast('Failed to load policy', 'error'))
            .finally(() => setLoading(false));
    }, [token]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateAcademicPolicy({
                min_sgpa_pass: parseFloat(form.min_sgpa_pass),
                min_sgpa_probation: parseFloat(form.min_sgpa_probation),
                min_cgpa_graduation: parseFloat(form.min_cgpa_graduation),
                max_consecutive_probation: parseInt(form.max_consecutive_probation, 10),
                max_course_attempts: parseInt(form.max_course_attempts, 10),
                min_attendance_percentage: parseFloat(form.min_attendance_percentage),
                max_semester_credit_hours: parseInt(form.max_semester_credit_hours, 10),
                max_repeat_credit_hours: parseInt(form.max_repeat_credit_hours, 10),
                auto_enroll_failed_prerequisites: form.auto_enroll_failed_prerequisites,
                allow_concurrent_prerequisite_enrollment: form.allow_concurrent_prerequisite_enrollment,
                soft_prerequisite_enrollment: form.soft_prerequisite_enrollment,
            }, token);
            showToast('Academic policy saved');
        } catch (e) {
            alert(e.response?.data?.error || JSON.stringify(e.response?.data) || 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <LoadingSpinner message="Loading academic policy..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > ACADEMIC POLICY" title="Academic Policy" />

            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', maxWidth: 720 }}>
                Institution-wide rules for results, enrollment, attendance warnings, and repeat limits.
            </p>

            <div className="form-card" style={{ maxWidth: 560 }}>
                <div className="section-header" style={{ marginBottom: 16 }}>
                    <div className="section-header-icon"><ShieldIcon /></div>
                    <div>
                        <h2 className="section-title">GPA &amp; standing rules</h2>
                    </div>
                </div>

                <div className="field-group">
                    <label className="field-label">Minimum SGPA (clean pass)</label>
                    <input type="number" step="0.01" min="0" max="4" className="field-input"
                        value={form.min_sgpa_pass}
                        onChange={e => setForm({ ...form, min_sgpa_pass: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label">Minimum SGPA for probation (with failed courses)</label>
                    <input type="number" step="0.01" min="0" max="4" className="field-input"
                        value={form.min_sgpa_probation}
                        onChange={e => setForm({ ...form, min_sgpa_probation: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label">Minimum CGPA for graduation</label>
                    <input type="number" step="0.01" min="0" max="4" className="field-input"
                        value={form.min_cgpa_graduation}
                        onChange={e => setForm({ ...form, min_cgpa_graduation: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label">Max consecutive probation semesters</label>
                    <input type="number" min="1" max="8" className="field-input"
                        value={form.max_consecutive_probation}
                        onChange={e => setForm({ ...form, max_consecutive_probation: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label">Max course attempts</label>
                    <input type="number" min="1" max="10" className="field-input"
                        value={form.max_course_attempts}
                        onChange={e => setForm({ ...form, max_course_attempts: e.target.value })} />
                </div>

                <div className="section-header" style={{ margin: '24px 0 16px' }}>
                    <h2 className="section-title">Attendance &amp; enrollment</h2>
                </div>

                <div className="field-group">
                    <label className="field-label">Minimum attendance percentage</label>
                    <input type="number" step="0.1" min="0" max="100" className="field-input"
                        value={form.min_attendance_percentage}
                        onChange={e => setForm({ ...form, min_attendance_percentage: e.target.value })} />
                    <p className="field-hint">Students and teachers are notified when attendance drops below this.</p>
                </div>

                <div className="field-group">
                    <label className="field-label">Max semester credit hours</label>
                    <input type="number" min="1" max="36" className="field-input"
                        value={form.max_semester_credit_hours}
                        onChange={e => setForm({ ...form, max_semester_credit_hours: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label">Max repeat credit hours (admin-approved)</label>
                    <input type="number" min="1" max="36" className="field-input"
                        value={form.max_repeat_credit_hours}
                        onChange={e => setForm({ ...form, max_repeat_credit_hours: e.target.value })} />
                </div>

                <div className="field-group">
                    <label className="field-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={form.auto_enroll_failed_prerequisites}
                            onChange={e => setForm({ ...form, auto_enroll_failed_prerequisites: e.target.checked })} />
                        Auto-enroll failed prerequisites as repeats
                    </label>
                    <p className="field-hint">When OOP needs PF and PF was failed, PF is registered automatically if credit hours allow.</p>
                </div>

                <div className="field-group">
                    <label className="field-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={form.allow_concurrent_prerequisite_enrollment}
                            onChange={e => setForm({ ...form, allow_concurrent_prerequisite_enrollment: e.target.checked })} />
                        Allow concurrent prerequisite + blocked course
                    </label>
                    <p className="field-hint">If under credit cap, enroll both PF (repeat) and OOP in the same semester.</p>
                </div>

                <div className="field-group">
                    <label className="field-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={form.soft_prerequisite_enrollment}
                            onChange={e => setForm({ ...form, soft_prerequisite_enrollment: e.target.checked })} />
                        Soft prerequisite enrollment (recommended for batch promotion)
                    </label>
                    <p className="field-hint">Enroll courses with a warning instead of deferring — batch promotes together; graduation audit still enforces prerequisites.</p>
                </div>

                <div className="form-actions">
                    <button type="button" className="btn-save" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : 'Save Policy'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AcademicPolicyPage;
