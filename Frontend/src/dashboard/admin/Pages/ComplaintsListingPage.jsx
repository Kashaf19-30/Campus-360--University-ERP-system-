import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
    listAllComplaints, listActiveComplaints, listCategories, createCategory,
    adminUpdateComplaintStatus, getComplaintThread, postComplaintMessage,
} from '../../../services/complaintsService';
import { normalizeList } from '../../../services/api';
import { PageHeader, useTableFilter, TablePagination, LoadingSpinner, EmptyRow, useToast, formatDate, getStatusBadgeClass, TableSearchBar } from '../../shared/helpers';
import ModalPortal from '../../shared/ModalPortal';
import { PlusIcon, BellIcon, XIcon } from '../../Icons';

const ComplaintsListingPage = () => {
    const { token } = useAuth();
    const { showToast, Toast } = useToast();
    const [activeTab, setActiveTab] = useState('complaints');
    const [complaintTab, setComplaintTab] = useState('active');
    const [complaints, setComplaints] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [selectedComplaint, setSelectedComplaint] = useState(null);
    const [statusForm, setStatusForm] = useState({ status: 'in_progress', admin_response: '' });
    const [thread, setThread] = useState(null);
    const [threadLoading, setThreadLoading] = useState(false);
    const [newMessage, setNewMessage] = useState('');
    const [sendingMessage, setSendingMessage] = useState(false);
    const [formData, setFormData] = useState({ category_name: '', description: '' });
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const fetchComplaints = complaintTab === 'active'
                ? listActiveComplaints(token)
                : listAllComplaints(token);
            const [c, cat] = await Promise.all([fetchComplaints, listCategories(token)]);
            setComplaints(normalizeList(c));
            setCategories(normalizeList(cat));
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { if (token) load(); }, [token, complaintTab]);

    const loadThread = async (complaintId) => {
        setThreadLoading(true);
        try {
            const data = await getComplaintThread(complaintId, token);
            setThread(data);
        } catch (e) {
            showToast('Failed to load message thread', 'error');
        } finally {
            setThreadLoading(false);
        }
    };

    const openComplaintReview = (item) => {
        setSelectedComplaint(item);
        setStatusForm({
            status: item.status === 'rejected' ? 'rejected' : item.status === 'resolved' ? 'resolved' : 'in_progress',
            admin_response: item.admin_response || '',
        });
        setNewMessage('');
        loadThread(item.complaint_id);
    };

    const isClosedComplaint = selectedComplaint && ['resolved', 'rejected', 'closed'].includes(selectedComplaint.status);

    const closeComplaintReview = () => {
        setSelectedComplaint(null);
        setThread(null);
        setNewMessage('');
    };

    const handleSendMessage = async () => {
        if (!selectedComplaint || !newMessage.trim()) return;
        setSendingMessage(true);
        try {
            await postComplaintMessage(selectedComplaint.complaint_id, { message_text: newMessage.trim() }, token);
            setNewMessage('');
            await loadThread(selectedComplaint.complaint_id);
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to send message');
        } finally {
            setSendingMessage(false);
        }
    };

    const displayedComplaints = complaintTab === 'active'
        ? complaints.filter(c => !['resolved', 'rejected', 'closed'].includes(c.status))
        : complaintTab === 'rejected'
            ? complaints.filter(c => c.status === 'rejected')
            : complaints;

    const currentData = activeTab === 'complaints' ? displayedComplaints : categories;
    const searchFields = activeTab === 'complaints' ? ['subject', 'status', 'category_name'] : ['category_name'];
    const { search, setSearch, page, setPage, paginated, filtered, totalPages, pageSize } = useTableFilter(currentData, searchFields);

    const handleCreateCategory = async () => {
        setSubmitting(true);
        try {
            await createCategory(formData, token);
            showToast('Category created');
            setShowModal(false);
            load();
        } catch (e) { alert('Failed to create category'); }
        finally { setSubmitting(false); }
    };

    const handleStatusUpdate = async () => {
        if (!selectedComplaint) return;
        if (statusForm.status === 'resolved' && !statusForm.admin_response.trim()) {
            alert('Please write a response message when resolving.');
            return;
        }
        if (statusForm.status === 'rejected' && !statusForm.admin_response.trim()) {
            alert('Please write a reason when rejecting.');
            return;
        }
        try {
            await adminUpdateComplaintStatus(selectedComplaint.complaint_id, statusForm, token);
            showToast('Complaint status updated');
            closeComplaintReview();
            load();
        } catch (e) {
            alert(e.response?.data?.error || 'Failed to update status');
        }
    };

    if (loading) return <LoadingSpinner message="Loading complaints..." />;

    return (
        <div className="page-container fade-in">
            {Toast}
            <PageHeader breadcrumb="DASHBOARD > COMPLAINTS" title="Complaints Management" />
            <div className="application-tabs">
                <button className={`app-tab ${activeTab === 'complaints' ? 'active' : ''}`} onClick={() => { setActiveTab('complaints'); setPage(1); }}>Complaints</button>
                <button className={`app-tab ${activeTab === 'categories' ? 'active' : ''}`} onClick={() => { setActiveTab('categories'); setPage(1); }}>Categories</button>
            </div>
            {activeTab === 'complaints' && (
                <div className="application-tabs" style={{ marginBottom: '12px' }}>
                    <button className={`app-tab ${complaintTab === 'active' ? 'active' : ''}`} onClick={() => setComplaintTab('active')}>Active</button>
                    <button className={`app-tab ${complaintTab === 'rejected' ? 'active' : ''}`} onClick={() => setComplaintTab('rejected')}>Rejected</button>
                    <button className={`app-tab ${complaintTab === 'all' ? 'active' : ''}`} onClick={() => setComplaintTab('all')}>All</button>
                </div>
            )}
            <div className="form-card">
                {activeTab === 'categories' && (
                    <div className="table-toolbar">
                        <button className="btn-add" onClick={() => setShowModal(true)}><PlusIcon /> <span>Add Category</span></button>
                    </div>
                )}
                {(activeTab === 'complaints' || activeTab === 'categories') && (
                    <TableSearchBar search={search} onSearchChange={(v) => { setSearch(v); setPage(1); }}
                        placeholder={activeTab === 'complaints' ? 'Search subject, category...' : 'Search category...'} />
                )}
                <div className="data-table-wrapper">
                    {activeTab === 'complaints' ? (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Subject</th><th>Category</th><th>Submitted By</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={7} icon={<BellIcon size={20} />} title="No complaints found" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.complaint_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{item.subject}</td>
                                        <td>{item.category_name || '—'}</td>
                                        <td>{item.submitted_by_username || item.submitted_by || '—'}</td>
                                        <td>{formatDate(item.submitted_at || item.created_at)}</td>
                                        <td><span className={getStatusBadgeClass(item.status)}>{item.status === 'in_progress' ? 'UNDER REVIEW' : item.status?.toUpperCase()}</span></td>
                                        <td>
                                            <button className="action-btn view-btn" onClick={() => openComplaintReview(item)}>Review</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <table className="data-table">
                            <thead><tr><th>Sr#</th><th>Category Name</th><th>Description</th></tr></thead>
                            <tbody>
                                {paginated.length === 0 ? (
                                    <EmptyRow colSpan={3} icon={<BellIcon size={20} />} title="No categories found" />
                                ) : paginated.map((item, i) => (
                                    <tr key={item.category_id || i}>
                                        <td>{(page - 1) * pageSize + i + 1}</td>
                                        <td>{item.category_name}</td>
                                        <td>{item.description || '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
                {filtered.length > 0 && <TablePagination page={page} totalPages={totalPages} total={filtered.length} pageSize={pageSize} onPageChange={setPage} />}
            </div>

            <ModalPortal
                isOpen={!!selectedComplaint}
                render={() => (
                <div className="modal-overlay" onClick={closeComplaintReview}>
                    <div className="glass-modal glass-modal-lg" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>{selectedComplaint?.subject}</h3>
                            <button type="button" className="close-btn" onClick={closeComplaintReview}><XIcon /></button>
                        </div>
                        <div className="modal-body">
                            <p><strong>From:</strong> {selectedComplaint?.submitted_by_username || 'Student'}</p>
                            <p style={{ marginTop: 8 }}><strong>Status:</strong> {selectedComplaint?.status?.toUpperCase()}</p>
                            <p style={{ marginTop: 12 }}>{selectedComplaint?.description}</p>

                            {!isClosedComplaint && (
                                <>
                                    <div className="field-group" style={{ marginTop: 16 }}>
                                        <label className="field-label">Update Status</label>
                                        <select className="field-input field-select" value={statusForm.status} onChange={e => setStatusForm({ ...statusForm, status: e.target.value })}>
                                            <option value="in_progress">Under Review</option>
                                            <option value="resolved">Resolve</option>
                                            <option value="rejected">Reject</option>
                                        </select>
                                    </div>
                                    {(statusForm.status === 'resolved' || statusForm.status === 'rejected') && (
                                        <div className="field-group">
                                            <label className="field-label">Response Message <span className="required">*</span></label>
                                            <textarea className="field-input field-textarea" rows={3} value={statusForm.admin_response} onChange={e => setStatusForm({ ...statusForm, admin_response: e.target.value })} />
                                        </div>
                                    )}
                                    <button type="button" className="btn-primary" style={{ marginTop: 12 }} onClick={handleStatusUpdate}>Submit Decision</button>
                                </>
                            )}

                            {isClosedComplaint && selectedComplaint?.admin_response && (
                                <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                                    <strong>Admin Response:</strong>
                                    <p style={{ marginTop: 6 }}>{selectedComplaint.admin_response}</p>
                                </div>
                            )}

                            <h4 style={{ margin: '16px 0 8px' }}>Message Thread</h4>
                            <div style={{ maxHeight: 220, overflowY: 'auto', marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {threadLoading ? (
                                    <LoadingSpinner message="Loading thread..." />
                                ) : (thread?.messages || []).length === 0 ? (
                                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No messages yet.</p>
                                ) : (
                                    (thread?.messages || []).map(msg => (
                                        <div key={msg.message_id} style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-medium)' }}>
                                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                                                {msg.sender_username || 'User'}
                                                <span style={{ fontWeight: 400, marginLeft: 8, color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{formatDate(msg.sent_at)}</span>
                                            </div>
                                            <div>{msg.message_text}</div>
                                        </div>
                                    ))
                                )}
                            </div>
                            {!isClosedComplaint && (
                                <>
                                    <div className="field-group">
                                        <label className="field-label">Reply</label>
                                        <textarea className="field-input field-textarea" rows={2} value={newMessage} onChange={e => setNewMessage(e.target.value)} placeholder="Write a message..." />
                                    </div>
                                    <button type="button" className="btn-secondary" onClick={handleSendMessage} disabled={sendingMessage || !newMessage.trim()}>
                                        {sendingMessage ? 'Sending...' : 'Send Message'}
                                    </button>
                                </>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="btn-secondary" onClick={closeComplaintReview}>Close</button>
                        </div>
                    </div>
                </div>
                )}
            />

            <ModalPortal isOpen={showModal} render={() => (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="glass-modal">
                        <div className="modal-header"><h3>Add Category</h3><button className="close-btn" onClick={() => setShowModal(false)}><XIcon /></button></div>
                        <div className="modal-body">
                            <div className="field-group"><label className="field-label">Category Name</label><input className="field-input" value={formData.category_name} onChange={e => setFormData({ ...formData, category_name: e.target.value })} /></div>
                            <div className="field-group"><label className="field-label">Description</label><textarea className="field-input field-textarea" value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} /></div>
                        </div>
                        <div className="modal-footer"><button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button><button className="btn-primary" onClick={handleCreateCategory} disabled={submitting}>{submitting ? 'Saving...' : 'Save'}</button></div>
                    </div>
                </div>
            )} />
        </div>
    );
};

export default ComplaintsListingPage;
