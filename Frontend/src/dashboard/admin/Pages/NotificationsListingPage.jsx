import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { listAnnouncements, createAnnouncement } from '../../../services/notificationsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, formatDate } from '../../shared/helpers';
import SystemNotificationsInbox from '../../shared/SystemNotificationsInbox';
import ModalPortal from '../../shared/ModalPortal';
import { PlusIcon, BellIcon, XIcon } from '../../Icons';

const NotificationsListingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [tab, setTab] = useState('inbox');
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ title: '', message: '', target_audience: 'all' });
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try { setItems(normalizeList(await listAnnouncements(token))); }
        catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { if (token) load(); }, [token]);

    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(items, ['title', 'content']);

    const handleSubmit = async () => {
        if (!formData.title.trim() || !formData.message.trim()) {
            alert('Title and message are required.');
            return;
        }
        setSubmitting(true);
        try {
            await createAnnouncement({
                title: formData.title.trim(),
                content: formData.message.trim(),
                target_audience: formData.target_audience,
                announcement_type: 'general',
            }, token);
            showToast('Announcement published');
            setShowModal(false);
            setFormData({ title: '', message: '', target_audience: 'all' });
            load();
        } catch (err) {
            const msg = err.response?.data?.error
                || Object.values(err.response?.data || {}).flat().join(', ')
                || 'Failed to send notification';
            alert(msg);
        } finally { setSubmitting(false); }
    };

    if (loading && tab === 'announcements') return <LoadingSpinner message="Loading announcements..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > NOTIFICATIONS" title="Announcements & Notifications" />
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                <button type="button" className={tab === 'inbox' ? 'btn-save' : 'btn-secondary'} onClick={() => setTab('inbox')}>System Inbox</button>
                <button type="button" className={tab === 'announcements' ? 'btn-save' : 'btn-secondary'} onClick={() => setTab('announcements')}>Announcements</button>
            </div>
            {tab === 'inbox' ? (
                <SystemNotificationsInbox />
            ) : (
            <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Publish campus-wide announcements. Recipients also receive an inbox notification automatically.
            </p>
            <div className="form-card">
                <div className="table-toolbar">
                    <div className="table-search search-bar" style={{ maxWidth: 360 }}>
                        <input type="text" placeholder="Search..." className="search-input" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
                    </div>
                    <button className="btn-add" onClick={() => setShowModal(true)}><PlusIcon /> <span>Send Announcement</span></button>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead><tr><th>Sr#</th><th>Title</th><th>Message</th><th>Audience</th><th>Date</th></tr></thead>
                        <tbody>
                            {paginated.length === 0 ? (
                                <EmptyRow colSpan={5} icon={<BellIcon size={20} />} title="No announcements" />
                            ) : paginated.map((item, i) => (
                                <tr key={item.announcement_id || i}>
                                    <td>{(page - 1) * pageSize + i + 1}</td>
                                    <td>{item.title || '—'}</td>
                                    <td>{(item.content || '').substring(0, 60)}{(item.content || '').length > 60 ? '...' : ''}</td>
                                    <td>{item.target_audience || 'all'}</td>
                                    <td>{formatDate(item.published_date || item.created_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header"><h3>Send Announcement</h3><button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button></div>
                        <div className="modal-body">
                            <div className="field-group"><label className="field-label">Title</label><input className="field-input" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} /></div>
                            <div className="field-group"><label className="field-label">Message</label><textarea className="field-input field-textarea" value={formData.message} onChange={e => setFormData({ ...formData, message: e.target.value })} /></div>
                            <div className="field-group">
                                <label className="field-label">Audience</label>
                                <select className="field-input field-select" value={formData.target_audience} onChange={e => setFormData({ ...formData, target_audience: e.target.value })}>
                                    <option value="all">Everyone</option>
                                    <option value="students">Students</option>
                                    <option value="faculty">Teachers</option>
                                </select>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn-primary" onClick={handleSubmit} disabled={submitting}>{submitting ? 'Sending...' : 'Publish'}</button>
                        </div>
                    </div>
                </div>
            )} />
            </>
            )}
        </div>
    );
};

export default NotificationsListingPage;
