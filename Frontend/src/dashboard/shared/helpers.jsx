import { useState, useCallback } from 'react';
import { CheckIcon } from '../Icons';

export const useToast = () => {
    const [toast, setToast] = useState(null);

    const showToast = useCallback((message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    }, []);

    const Toast = toast ? (
        <div className={`toast ${toast.type} fade-in-up`}>
            <CheckIcon />
            <span>{toast.message}</span>
        </div>
    ) : null;

    return { showToast, Toast };
};

export const TableSearchBar = ({ search, onSearchChange, placeholder = 'Search...' }) => (
    <div className="table-toolbar">
        <div className="table-search search-bar" style={{ maxWidth: 360 }}>
            <input
                type="text"
                className="search-input"
                placeholder={placeholder}
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
            />
        </div>
    </div>
);

export const useTableFilter = (items, searchFields = []) => {
    const [search, setSearch] = useState('');
    const [page, setPage] = useState(1);
    const pageSize = 10;

    const filtered = items.filter(item => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return searchFields.some(field => {
            const val = item[field];
            return val && val.toString().toLowerCase().includes(q);
        });
    });

    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

    return { search, setSearch, page, setPage, filtered, paginated, totalPages, pageSize };
};

export const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-PK', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });
};

/** User-facing semester label — curriculum semester number only. */
export const formatCurriculumSemester = (itemOrNumber) => {
    if (itemOrNumber == null) return '—';
    if (typeof itemOrNumber === 'object') {
        const item = itemOrNumber;
        if (item.semester_label) return item.semester_label;
        if (item.curriculum_semester != null) return `Semester ${item.curriculum_semester}`;
        if (item.current_semester != null) return `Semester ${item.current_semester}`;
        if (item.semester_number != null) return `Semester ${item.semester_number}`;
        if (typeof item.semester_name === 'string' && /^Semester\s+\d+/i.test(item.semester_name)) {
            return item.semester_name;
        }
        return '—';
    }
    return `Semester ${itemOrNumber}`;
};

export const getStatusBadgeClass = (status) => {
    const s = status?.toLowerCase()?.replace(/\s+/g, '_');
    switch (s) {
        case 'approved': case 'verified': case 'active': case 'paid': case 'resolved':
            return 'status-badge approved';
        case 'rejected': case 'inactive': case 'cancelled':
            return 'status-badge rejected';
        case 'under_review': case 'in_progress': case 'pending':
            return 'status-badge under-review';
        default:
            return 'status-badge pending';
    }
};

export const PageHeader = ({ breadcrumb, title }) => (
    <div className="page-header-minimal">
        <div className="breadcrumb-minimal">{breadcrumb}</div>
        <h1 className="page-title-minimal">{title}</h1>
    </div>
);

export const TablePagination = ({ page, totalPages, total, pageSize, onPageChange }) => (
    <div className="table-pagination">
        <span className="pagination-info">
            Showing {Math.min((page - 1) * pageSize + 1, total)}–{Math.min(page * pageSize, total)} of {total} entries
        </span>
        <div className="pagination-controls">
            <button className="pagination-btn" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
                <button key={p} className={`pagination-btn ${page === p ? 'active' : ''}`} onClick={() => onPageChange(p)}>{p}</button>
            ))}
            <button className="pagination-btn" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
        </div>
    </div>
);

export const LoadingSpinner = ({ message = 'Loading...' }) => (
    <div className="page-container fade-in">
        <div className="loading-spinner">{message}</div>
    </div>
);

export const EmptyRow = ({ colSpan, icon, title, subtitle }) => (
    <tr>
        <td colSpan={colSpan} className="empty-row">
            {icon}
            <p>{title}</p>
            {subtitle && <span>{subtitle}</span>}
        </td>
    </tr>
);

/** Teacher offering dropdown / table label (Regular vs Repeat). */
export const formatOfferingLabel = (offering) => {
    if (!offering) return '—';
    if (offering.display_label) return offering.display_label;
    const kind = offering.offering_type_label
        || (offering.repeat_offering ? 'Repeat' : 'Regular');
    const code = offering.course_code || 'Course';
    const name = offering.course_name || offering.program_code || '';
    return name ? `${code} — ${name} (${kind})` : `${code} (${kind})`;
};
