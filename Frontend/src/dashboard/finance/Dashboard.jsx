import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pageIdFromPath } from '../../routes/paths';
import { useDashboardNavigate } from '../../routes/useDashboardNavigate';
import RequirePermission from '../../routes/RequirePermission';
import { useFilteredNavItems } from '../../routes/navPermissions';
import DashboardLayout from '../shared/DashboardLayout';
import {
    PageHeader, useToast, LoadingSpinner, useTableFilter,
    TablePagination, EmptyRow, TableSearchBar, getStatusBadgeClass,
} from '../shared/helpers';
import { listDepartments, listPrograms } from '../../services/academicsService';
import { normalizeList } from '../../services/api';
import { getFinanceDashboard, listChallans, markAdmissionPaid, markChallanPaid } from '../../services/financeService';
import { FileTextIcon, LayoutDashboardIcon, ShieldIcon } from '../Icons';
import ChangePasswordPage from '../applicant/Pages/ChangePasswordPage';
import FeeStructurePage from '../admin/Pages/FeeStructurePage';

const FINANCE_BASE = '/finance';
const curriculumSemesters = [1, 2, 3, 4, 5, 6, 7, 8];

const FinanceFeesContent = ({ tab }) => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState({ new_admissions: [], enrolled_students: [], summary: {} });
    const [departments, setDepartments] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [filters, setFilters] = useState({ department: '', program: '', semester: '', curriculum_semester: '' });
    const [pendingOnly, setPendingOnly] = useState(true);

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const qs = new URLSearchParams();
            if (filters.department) qs.set('department', filters.department);
            if (filters.program) qs.set('program', filters.program);
            if (filters.semester) qs.set('semester', filters.semester);
            if (filters.curriculum_semester) qs.set('curriculum_semester', filters.curriculum_semester);
            const q = qs.toString() ? `?${qs.toString()}` : '';
            const res = await getFinanceDashboard(token, q);
            setData(res);
        } catch (e) {
            console.error(e);
            showToast('Failed to load finance data', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, filters, showToast]);

    useEffect(() => { load(); }, [load]);

    useEffect(() => {
        if (!token) return;
        listDepartments(token).then(d => setDepartments(normalizeList(d))).catch(console.error);
    }, [token]);

    useEffect(() => {
        if (!token || !filters.department) { setPrograms([]); return; }
        listPrograms(token, filters.department).then(d => setPrograms(normalizeList(d))).catch(console.error);
    }, [token, filters.department]);

    const admissionRows = data.new_admissions || [];
    const enrolledRows = (data.enrolled_students || []).filter(row =>
        !pendingOnly || row.fee_status !== 'paid'
    );

    const admissionFilter = useTableFilter(admissionRows, ['application_number', 'applicant_name', 'program_name', 'department_name']);
    const enrolledFilter = useTableFilter(enrolledRows, ['registration_number', 'student_name', 'program_name', 'department_name']);

    const handleAdmissionPaid = async (appId) => {
        try {
            const res = await markAdmissionPaid(appId, true, token);
            showToast(res.message);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update admission fee');
        }
    };

    const handleChallanPaid = async (challanId) => {
        try {
            const res = await markChallanPaid(challanId, true, token);
            showToast(res.message);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update challan');
        }
    };

    const summary = data.summary || {};

    const filterBar = (
        <div className="filter-bar" style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <select className="field-input field-select" value={filters.department}
                onChange={e => setFilters(f => ({ ...f, department: e.target.value, program: '' }))}>
                <option value="">All departments</option>
                {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
            </select>
            <select className="field-input field-select" value={filters.program} disabled={!filters.department}
                onChange={e => setFilters(f => ({ ...f, program: e.target.value }))}>
                <option value="">All programs</option>
                {programs.map(p => <option key={p.program_id} value={p.program_id}>{p.program_name}</option>)}
            </select>
            {tab === 'enrolled' && (
                <>
                    <select className="field-input field-select" value={filters.curriculum_semester}
                        onChange={e => setFilters(f => ({ ...f, curriculum_semester: e.target.value }))}>
                        <option value="">All semesters</option>
                        {curriculumSemesters.map(n => <option key={n} value={n}>Semester {n}</option>)}
                    </select>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.9rem' }}>
                        <input type="checkbox" checked={pendingOnly} onChange={e => setPendingOnly(e.target.checked)} />
                        Unpaid only
                    </label>
                </>
            )}
        </div>
    );

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="FINANCE" title="Finance Officer Dashboard" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, maxWidth: 720 }}>
                Mark admission and semester fee challans as paid. Students cannot enroll or advance until fees are cleared.
            </p>

            <div className="stats-grid" style={{ marginBottom: 20 }}>
                <div className="stat-card"><span>Pending Admissions</span><strong>{summary.pending_admissions ?? 0}</strong></div>
                <div className="stat-card"><span>Enrolled Students</span><strong>{summary.enrolled_total ?? 0}</strong></div>
                <div className="stat-card"><span>Fees Paid</span><strong>{summary.fees_paid ?? 0}</strong></div>
                <div className="stat-card"><span>Fees Unpaid</span><strong>{summary.fees_unpaid ?? 0}</strong></div>
            </div>

            {filterBar}

            {loading ? <LoadingSpinner message="Loading..." /> : (
                <div className="form-card">
                    {tab === 'admissions' ? (
                        <>
                            <TableSearchBar
                                search={admissionFilter.search}
                                onSearchChange={(v) => { admissionFilter.setSearch(v); admissionFilter.setPage(1); }}
                                placeholder="Search application, applicant, program..."
                            />
                            <div className="data-table-wrapper">
                                <table className="data-table">
                                    <thead>
                                        <tr><th>Sr#</th><th>Application</th><th>Applicant</th><th>Department</th><th>Program</th><th>Challan</th><th>Amount</th><th>Action</th></tr>
                                    </thead>
                                    <tbody>
                                        {admissionFilter.paginated.length === 0 ? (
                                            <EmptyRow colSpan={8} icon={<FileTextIcon size={20} />} title="No pending admission fees" />
                                        ) : admissionFilter.paginated.map((row, i) => (
                                            <tr key={row.application_id}>
                                                <td>{(admissionFilter.page - 1) * admissionFilter.pageSize + i + 1}</td>
                                                <td>{row.application_number}</td>
                                                <td>{row.applicant_name}</td>
                                                <td>{row.department_name || '—'}</td>
                                                <td>{row.program_name}</td>
                                                <td>{row.challan_number}</td>
                                                <td>Rs. {row.challan_amount}</td>
                                                <td>
                                                    <button type="button" className="btn-save small" onClick={() => handleAdmissionPaid(row.application_id)}>Mark Paid</button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {admissionFilter.filtered.length > 0 && (
                                <TablePagination page={admissionFilter.page} totalPages={admissionFilter.totalPages}
                                    total={admissionFilter.filtered.length} pageSize={admissionFilter.pageSize}
                                    onPageChange={admissionFilter.setPage} />
                            )}
                        </>
                    ) : (
                        <>
                            <TableSearchBar
                                search={enrolledFilter.search}
                                onSearchChange={(v) => { enrolledFilter.setSearch(v); enrolledFilter.setPage(1); }}
                                placeholder="Search reg #, student, program..."
                            />
                            <div className="data-table-wrapper">
                                <table className="data-table">
                                    <thead>
                                        <tr><th>Sr#</th><th>Reg #</th><th>Student</th><th>Department</th><th>Program</th><th>Fee Sem</th><th>Challan</th><th>Status</th><th>Action</th></tr>
                                    </thead>
                                    <tbody>
                                        {enrolledFilter.paginated.length === 0 ? (
                                            <EmptyRow colSpan={9} icon={<FileTextIcon size={20} />} title="No matching fee records" />
                                        ) : enrolledFilter.paginated.map((row, i) => (
                                            <tr key={row.student_id}>
                                                <td>{(enrolledFilter.page - 1) * enrolledFilter.pageSize + i + 1}</td>
                                                <td>{row.registration_number}</td>
                                                <td>{row.student_name}</td>
                                                <td>{row.department_name || '—'}</td>
                                                <td>{row.program_name}</td>
                                                <td>
                                                    {row.curriculum_semester ?? row.current_semester}
                                                    {row.promotion_pending ? ' (promotion)' : ''}
                                                </td>
                                                <td>{row.challan_number || '—'}</td>
                                                <td><span className={getStatusBadgeClass(row.fee_status)}>{row.fee_status?.toUpperCase()}</span></td>
                                                <td>
                                                    {row.challan_id ? (
                                                        <button type="button" className="btn-save small" disabled={row.fee_status === 'paid'}
                                                            onClick={() => handleChallanPaid(row.challan_id)}>Mark Paid</button>
                                                    ) : '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {enrolledFilter.filtered.length > 0 && (
                                <TablePagination page={enrolledFilter.page} totalPages={enrolledFilter.totalPages}
                                    total={enrolledFilter.filtered.length} pageSize={enrolledFilter.pageSize}
                                    onPageChange={enrolledFilter.setPage} />
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

const FinanceChallansPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [rows, setRows] = useState([]);
    const [statusFilter, setStatusFilter] = useState('');

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const q = statusFilter ? `?status=${statusFilter}` : '';
            const res = await listChallans(token, q);
            setRows(normalizeList(res));
        } catch (e) {
            console.error(e);
            showToast('Failed to load challans', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, statusFilter, showToast]);

    useEffect(() => { load(); }, [load]);

    const tableFilter = useTableFilter(rows, ['challan_number', 'student_reg', 'student_name', 'semester_name']);

    const handleMarkPaid = async (challanId) => {
        try {
            const res = await markChallanPaid(challanId, true, token);
            showToast(res.message);
            load();
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to update challan');
        }
    };

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="FINANCE" title="Challan Register" />
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, maxWidth: 720 }}>
                View all generated semester fee challans and mark payments.
            </p>
            <div className="filter-bar" style={{ marginBottom: 16 }}>
                <select className="field-input field-select" value={statusFilter}
                    onChange={e => setStatusFilter(e.target.value)}>
                    <option value="">All statuses</option>
                    <option value="pending">Pending</option>
                    <option value="paid">Paid</option>
                    <option value="overdue">Overdue</option>
                </select>
            </div>
            {loading ? <LoadingSpinner message="Loading challans..." /> : (
                <div className="form-card">
                    <TableSearchBar
                        search={tableFilter.search}
                        onSearchChange={(v) => { tableFilter.setSearch(v); tableFilter.setPage(1); }}
                        placeholder="Search challan #, reg #, student..."
                    />
                    <div className="data-table-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Sr#</th><th>Challan #</th><th>Reg #</th><th>Student</th>
                                    <th>Term</th><th>Amount</th><th>Due</th><th>Status</th><th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tableFilter.paginated.length === 0 ? (
                                    <EmptyRow colSpan={9} icon={<FileTextIcon size={20} />} title="No challans found" />
                                ) : tableFilter.paginated.map((row, i) => (
                                    <tr key={row.challan_id}>
                                        <td>{(tableFilter.page - 1) * tableFilter.pageSize + i + 1}</td>
                                        <td>{row.challan_number}</td>
                                        <td>{row.student_reg || '—'}</td>
                                        <td>{row.student_name || '—'}</td>
                                        <td>{row.semester_name || '—'}</td>
                                        <td>Rs. {row.total_amount}</td>
                                        <td>{row.due_date || '—'}</td>
                                        <td><span className={getStatusBadgeClass(row.status)}>{row.status?.toUpperCase()}</span></td>
                                        <td>
                                            {row.status !== 'paid' ? (
                                                <button type="button" className="btn-save small" onClick={() => handleMarkPaid(row.challan_id)}>Mark Paid</button>
                                            ) : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {tableFilter.filtered.length > 0 && (
                        <TablePagination page={tableFilter.page} totalPages={tableFilter.totalPages}
                            total={tableFilter.filtered.length} pageSize={tableFilter.pageSize}
                            onPageChange={tableFilter.setPage} />
                    )}
                </div>
            )}
        </div>
    );
};

const FinanceDashboard = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const onNavigate = useDashboardNavigate(FINANCE_BASE);
    const currentPage = pageIdFromPath(location.pathname, FINANCE_BASE);

    const handleLogout = async (e) => {
        e.preventDefault();
        await logout();
        navigate('/');
    };

    const navItems = useMemo(() => [
        { id: 'admissions', label: 'Admission Fees', icon: <FileTextIcon size={20} />, always: true },
        { id: 'enrolled', label: 'Semester Fees', icon: <LayoutDashboardIcon size={20} />, always: true },
        { id: 'challans', label: 'Challan Register', icon: <FileTextIcon size={20} />, always: true },
        { id: 'fee-structures', label: 'Fee Structures', icon: <FileTextIcon size={20} />, permission: 'fees.manage_fees' },
        { id: 'change-password', label: 'Change Password', icon: <ShieldIcon size={20} />, always: true },
    ], []);

    const filteredNavItems = useFilteredNavItems(navItems);

    return (
        <DashboardLayout
            roleLabel="Finance Officer"
            navItems={filteredNavItems}
            currentPage={currentPage}
            onNavigate={onNavigate}
            onLogout={handleLogout}
            sidebarSubLabel={user?.email}
        >
            <Routes>
                <Route index element={<Navigate to={`${FINANCE_BASE}/admissions`} replace />} />
                <Route path="admissions" element={
                    <RequirePermission permission="fees.view_fees">
                        <FinanceFeesContent tab="admissions" />
                    </RequirePermission>
                } />
                <Route path="enrolled" element={
                    <RequirePermission permission="fees.view_fees">
                        <FinanceFeesContent tab="enrolled" />
                    </RequirePermission>
                } />
                <Route path="challans" element={
                    <RequirePermission permission="fees.view_fees">
                        <FinanceChallansPage />
                    </RequirePermission>
                } />
                <Route path="fee-structures" element={
                    <RequirePermission permission="fees.manage_fees">
                        <FeeStructurePage />
                    </RequirePermission>
                } />
                <Route path="change-password" element={<ChangePasswordPage />} />
                <Route path="*" element={<Navigate to={`${FINANCE_BASE}/admissions`} replace />} />
            </Routes>
        </DashboardLayout>
    );
};

export default FinanceDashboard;
