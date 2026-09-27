import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '../../services/notificationsService';
import { normalizeList } from '../../services/api';
import { useTableFilter, TablePagination, LoadingSpinner, EmptyRow, formatDate } from './helpers';
import ModalPortal from './ModalPortal';
import { BellIcon, XIcon } from '../Icons';

const SystemNotificationsInbox = ({ breadcrumb = 'DASHBOARD > NOTIFICATIONS', title = 'System Notifications' }) => {
    const { token } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);

    const load = () => listNotifications(token).then(d => setItems(normalizeList(d)));

    useEffect(() => {
        if (token) load().finally(() => setLoading(false));
    }, [token]);

    const { search, setSearch, paginated, filtered, page, setPage, totalPages, pageSize } = useTableFilter(
        items,
        ['title', 'message', 'type_name'],
    );

    const openNotification = async (item) => {
        setSelected(item);
        if (!item.is_read) {
            await markNotificationRead(item.notification_id, token).catch(() => {});
            load();
        }
    };

    const handleMarkAllRead = async () => {
        await markAllNotificationsRead(token).catch(() => {});
        load();
    };

    if (loading) return <LoadingSpinner message="Loading notifications..." />;

    return (
        <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                Automated alerts from admissions, finance, academic progress, examinations, attendance, and complaints.
            </p>
            <div style={{ marginBottom: 12 }}>
                <button type="button" className="btn-secondary small" onClick={handleMarkAllRead}>Mark all as read</button>
            </div>
            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input
                            type="text"
                            placeholder="Search notifications..."
                            className="search-input"
                            value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1); }}
                        />
                    </div>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th>
                                <th>Type</th>
                                <th>Title</th>
                                <th>Preview</th>
                                <th>Date</th>
                                <th>Read</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={6} icon={<BellIcon size={20} />} title="No system notifications" />
                            ) : paginated.map((item, i) => (
                                <tr key={item.notification_id || i} style={{ cursor: 'pointer' }} onClick={() => openNotification(item)}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td>{item.type_name || item.notification_type_name || '—'}</td>
                                    <td>{item.title || '—'}</td>
                                    <td>{(item.message || '').substring(0, 50)}{(item.message || '').length > 50 ? '…' : ''}</td>
                                    <td>{formatDate(item.created_at)}</td>
                                    <td>{item.is_read ? 'Yes' : 'No'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && (
                    <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />
                )}
            </div>
            <ModalPortal isOpen={!!selected} render={() => (
                <div className="modal-overlay" onClick={() => setSelected(null)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>{selected?.title || 'Notification'}</h3>
                            <button type="button" className="close-btn" onClick={() => setSelected(null)}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            <p style={{ color: 'var(--text-secondary)' }}>{formatDate(selected?.created_at)}</p>
                            <p style={{ whiteSpace: 'pre-wrap' }}>{selected?.message}</p>
                        </div>
                    </div>
                </div>
            )} />
        </>
    );
};

export default SystemNotificationsInbox;
