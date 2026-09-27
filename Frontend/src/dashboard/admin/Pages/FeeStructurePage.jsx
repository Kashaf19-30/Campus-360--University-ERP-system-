import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listDepartments, listPrograms } from '../../../services/academicsService';
import { listFeeStructures, createFeeStructure, deleteFeeStructure } from '../../../services/feesService';
import { normalizeList } from '../../../services/api';
import {
    PageHeader, useTableFilter, TablePagination, LoadingSpinner,
    EmptyRow, useToast, formatDate,
} from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { FileTextIcon, PlusIcon, TrashIcon, XIcon } from '../../Icons';

const FEE_TYPES = [
    { value: 'semester_fee', label: 'Semester Fee' },
    { value: 'admission_fee', label: 'Admission Fee' },
    { value: 'examination_fee', label: 'Examination Fee' },
];

const SEMESTER_OPTIONS = ['', 1, 2, 3, 4, 5, 6, 7, 8];

const FeeStructurePage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [filterDept, setFilterDept] = useState('');
    const [filterProgram, setFilterProgram] = useState('');
    const [filterFeeType, setFilterFeeType] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [formDept, setFormDept] = useState('');
    const [formPrograms, setFormPrograms] = useState([]);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        program: '',
        semester_number: '',
        fee_type: 'semester_fee',
        amount: '',
        effective_from: new Date().toISOString().slice(0, 10),
    });

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterProgram) params.set('program', filterProgram);
            if (filterFeeType) params.set('fee_type', filterFeeType);
            const qs = params.toString() ? `?${params.toString()}` : '';
            const data = await listFeeStructures(token, qs);
            setItems(normalizeList(data));
        } catch (e) {
            console.error(e);
            showToast('Failed to load fee structures', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, filterProgram, filterFeeType, showToast]);

    useEffect(() => { load(); }, [load]);

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !filterDept) { setPrograms([]); return; }
        listPrograms(token, filterDept).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, filterDept]);

    useEffect(() => {
        if (!token || !formDept) { setFormPrograms([]); return; }
        listPrograms(token, formDept).then(d => setFormPrograms(normalizeList(d))).catch(console.error);
    }, [token, formDept]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(
        items,
        ['program_name', 'department_name', 'fee_type', 'fee_type_display'],
    );

    const resetForm = () => {
        setForm({
            program: filterProgram || '',
            semester_number: '',
            fee_type: 'semester_fee',
            amount: '',
            effective_from: new Date().toISOString().slice(0, 10),
        });
    };

    const openModal = () => {
        setFormDept(filterDept || '');
        resetForm();
        setShowModal(true);
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!form.program || !form.amount || !form.effective_from) {
            alert('Program, amount, and effective from date are required.');
            return;
        }
        setSaving(true);
        try {
            await createFeeStructure({
                program: Number(form.program),
                semester_number: form.semester_number ? Number(form.semester_number) : null,
                fee_type: form.fee_type,
                amount: form.amount,
                effective_from: form.effective_from,
            }, token);
            showToast('Fee structure added');
            setShowModal(false);
            resetForm();
            load();
        } catch (err) {
            alert(err.response?.data?.error || JSON.stringify(err.response?.data) || 'Failed to save');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (structureId) => {
        if (!confirm('Delete this fee structure?')) return;
        try {
            await deleteFeeStructure(structureId, token);
            showToast('Fee structure deleted');
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Delete failed');
        }
    };

    const modalPrograms = formPrograms;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > FINANCE" title="Fee Structures" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, maxWidth: 760 }}>
                Configure admission and semester fee amounts per program. When a challan is generated, the system uses the matching structure; otherwise it falls back to the program default.
            </p>

            <div className="filter-bar" style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <select className="field-input field-select" value={filterDept}
                    onChange={e => { setFilterDept(e.target.value); setFilterProgram(''); }}>
                    <option value="">All departments</option>
                    {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                </select>
                <select className="field-input field-select" value={filterProgram} disabled={!filterDept}
                    onChange={e => setFilterProgram(e.target.value)}>
                    <option value="">All programs</option>
                    {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                </select>
                <select className="field-input field-select" value={filterFeeType} onChange={e => setFilterFeeType(e.target.value)}>
                    <option value="">All fee types</option>
                    {FEE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <button type="button" className="btn-save" onClick={openModal}>
                    <PlusIcon size={16} /> Add Fee Structure
                </button>
            </div>

            {loading ? <LoadingSpinner message="Loading fee structures..." /> : (
                <div className="form-card">
                    <div className="table-toolbar">
                        <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                            <input className="search-input" placeholder="Search program, department, fee type..."
                                value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
                        </div>
                    </div>
                    <div className="data-table-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Sr#</th>
                                    <th>Department</th>
                                    <th>Program</th>
                                    <th>Semester</th>
                                    <th>Fee Type</th>
                                    <th>Amount (Rs.)</th>
                                    <th>Effective From</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={8} icon={<FileTextIcon size={20} />} title="No fee structures configured" />
                                ) : paginated.map((row, i) => (
                                    <tr key={row.structure_id}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{row.department_name || '—'}</td>
                                        <td>{row.program_name || '—'}</td>
                                        <td>{row.semester_number ? `Semester ${row.semester_number}` : 'All'}</td>
                                        <td>{row.fee_type_display || row.fee_type}</td>
                                        <td>{row.amount}</td>
                                        <td>{formatDate(row.effective_from)}</td>
                                        <td>
                                            <button type="button" className="action-btn danger" onClick={() => handleDelete(row.structure_id)}>
                                                <TrashIcon />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {filtered.length > 0 && (
                        <TablePagination page={page} totalPages={totalPages} total={filtered.length}
                            pageSize={pageSize} onPageChange={setPage} />
                    )}
                </div>
            )}

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Add Fee Structure</h3>
                            <button type="button" className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div className="field-group" style={{ marginBottom: 16 }}>
                                    <label className="field-label">Department</label>
                                    <select className="field-input field-select" value={formDept}
                                        onChange={e => { setFormDept(e.target.value); setForm(f => ({ ...f, program: '' })); }}>
                                        <option value="">Select department</option>
                                        {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
                                    </select>
                                </div>
                                <div className="field-group" style={{ marginBottom: 16 }}>
                                    <label className="field-label">Program <span className="required">*</span></label>
                                    <select className="field-input field-select" required value={form.program}
                                        onChange={e => setForm(f => ({ ...f, program: e.target.value }))} disabled={!formDept}>
                                        <option value="">Select program</option>
                                        {modalPrograms.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
                                    </select>
                                </div>
                                <div className="two-column-grid" style={{ marginBottom: 16 }}>
                                    <div className="field-group">
                                        <label className="field-label">Curriculum Semester</label>
                                        <select className="field-input field-select" value={form.semester_number}
                                            onChange={e => setForm(f => ({ ...f, semester_number: e.target.value }))}>
                                            <option value="">All semesters</option>
                                            {SEMESTER_OPTIONS.filter(Boolean).map(n => (
                                                <option key={n} value={n}>Semester {n}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="field-group">
                                        <label className="field-label">Fee Type <span className="required">*</span></label>
                                        <select className="field-input field-select" required value={form.fee_type}
                                            onChange={e => setForm(f => ({ ...f, fee_type: e.target.value }))}>
                                            {FEE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                                        </select>
                                    </div>
                                </div>
                                <div className="field-group" style={{ marginBottom: 16 }}>
                                    <label className="field-label">Amount (Rs.) <span className="required">*</span></label>
                                    <input type="number" min="0" step="0.01" className="field-input" required
                                        value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
                                </div>
                                <div className="field-group">
                                    <label className="field-label">Effective From <span className="required">*</span></label>
                                    <input type="date" className="field-input" required
                                        value={form.effective_from} onChange={e => setForm(f => ({ ...f, effective_from: e.target.value }))} />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn-save" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )} />
        </div>
    );
};

export default FeeStructurePage;
