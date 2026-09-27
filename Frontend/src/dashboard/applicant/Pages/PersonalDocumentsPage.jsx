// src/dashboard/Pages/PersonalDocumentsPage.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { getApplicantProfile, getMyDocuments, uploadDocument, deleteDocument } from '../../../services/admissionService';
import { InfoIcon, FileIcon, UploadIcon, XIcon, TrashIcon, CheckIcon } from '../../Icons';
import { getDocumentUploadError, isValidDocumentUpload } from '../../../utils/validation';

const PersonalDocumentsPage = ({ onDocumentChange, readOnly = false }) => {
    const navigate = useNavigate();
    const { token } = useAuth();
    const [documents, setDocuments] = useState([]);
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [selectedDocType, setSelectedDocType] = useState('');
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [profileComplete, setProfileComplete] = useState(false);
    const [errors, setErrors] = useState({});
    const [touched, setTouched] = useState({});
    const fileInputRef = useRef(null);
    const isMounted = useRef(true);

    const documentTypeOptions = [
        { value: 'cnic_front', label: 'CNIC Front', required: true },
        { value: 'cnic_back', label: 'CNIC Back', required: true },
        { value: 'domicile', label: 'Domicile', required: true },
        { value: 'photograph', label: 'Photograph', required: true },
    ];

    const MAX_DOCUMENTS = 4;
    const REQUIRED_DOCUMENTS = documentTypeOptions.filter(opt => opt.required).map(opt => opt.value);

    const refreshDocuments = useCallback(async () => {
        if (!token || !isMounted.current) return;
        try {
            const data = await getMyDocuments(token);
            let docsArray = [];
            if (Array.isArray(data)) {
                docsArray = data;
            } else if (data && data.results && Array.isArray(data.results)) {
                docsArray = data.results;
            } else if (data && typeof data === 'object') {
                docsArray = [data];
            }
            setDocuments(docsArray);
            if (onDocumentChange && isMounted.current) onDocumentChange();
        } catch (error) {
            console.error('Failed to refresh documents:', error);
        }
    }, [token, onDocumentChange]);

    useEffect(() => {
        isMounted.current = true;
        
        const checkProfile = async () => {
            if (!token || !isMounted.current) return;
            try {
                const profile = await getApplicantProfile(token);
                if (isMounted.current) {
                    const isComplete = profile.firstName && profile.lastName && profile.cnic;
                    setProfileComplete(isComplete);
                    if (!isComplete) alert('Please complete your Personal Details before uploading documents.');
                }
            } catch (error) {
                console.error('Profile check failed:', error);
                if (isMounted.current) setProfileComplete(false);
            }
        };
        
        const loadDocs = async () => {
            if (!token || !isMounted.current) return;
            setLoading(true);
            await refreshDocuments();
            if (isMounted.current) setLoading(false);
        };
        
        checkProfile();
        loadDocs();
        
        return () => { isMounted.current = false; };
    }, [token, refreshDocuments]);

    const handleDrag = (e) => { 
        e.preventDefault(); 
        e.stopPropagation(); 
        setDragActive(e.type === 'dragenter' || e.type === 'dragover'); 
    };
    
    const handleDrop = (e) => { 
        e.preventDefault(); 
        setDragActive(false); 
        if (e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
            setTouched(prev => ({ ...prev, file: true }));
            setErrors(prev => ({ ...prev, file: '' }));
        }
    };
    
    const handleFile = (e) => { 
        if (e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
            setTouched(prev => ({ ...prev, file: true }));
            setErrors(prev => ({ ...prev, file: '' }));
        }
    };

    const handleDocTypeChange = (value) => {
        setSelectedDocType(value);
        setTouched(prev => ({ ...prev, docType: true }));
        setErrors(prev => ({ ...prev, docType: '' }));
    };

    const validateUpload = () => {
        const newErrors = {};
        
        if (!profileComplete) newErrors.profile = 'Please complete personal details first';
        if (!selectedFile) newErrors.file = 'Please select a file to upload';
        if (!selectedDocType) newErrors.docType = 'Please select a document type';
        if (selectedFile && !isValidDocumentUpload(selectedFile, selectedDocType)) {
            newErrors.file = getDocumentUploadError(selectedFile, selectedDocType);
        }
        if (documents.length >= MAX_DOCUMENTS) newErrors.limit = `Maximum ${MAX_DOCUMENTS} documents allowed`;
        
        const alreadyExists = documents.some(doc => doc.document_type === selectedDocType);
        if (alreadyExists) newErrors.exists = 'You have already uploaded this document type';
        
        setErrors(newErrors);
        setTouched({ file: true, docType: true, profile: true });
        
        return Object.keys(newErrors).length === 0;
    };

    const handleSave = async () => {
        if (!validateUpload()) return;
        
        setUploading(true);
        try {
            const res = await uploadDocument({ document_type: selectedDocType, file: selectedFile }, token);
            alert(res?.message || 'Document uploaded successfully!');
            setSelectedFile(null);
            setSelectedDocType('');
            if (fileInputRef.current) fileInputRef.current.value = '';
            await refreshDocuments();
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Failed to upload document: ' + (error.response?.data?.error || error.message));
        } finally {
            setUploading(false);
        }
    };

    const handleRemove = async (documentId) => {
        if (!confirm('Are you sure you want to delete this document?')) return;
        try {
            await deleteDocument(documentId, token);
            alert('Document deleted successfully!');
            await refreshDocuments();
        } catch (error) {
            console.error('Delete failed:', error);
            alert('Failed to delete document');
        }
    };

    const isDocRejected = (doc) => {
        const remarks = (doc.verification_remarks || '').toLowerCase();
        return remarks.includes('reject') || remarks.includes('rejected');
    };

    const getStatusBadgeClass = (doc) => {
        if (doc.is_verified === true) return 'status-badge verified';
        if (isDocRejected(doc)) return 'status-badge rejected';
        return 'status-badge pending';
    };

    const getStatusText = (doc) => {
        if (doc.is_verified === true) return 'VERIFIED';
        if (isDocRejected(doc)) return 'REJECTED';
        return 'PENDING';
    };

    const getDocumentTypeDisplay = (docType) => {
        const option = documentTypeOptions.find(opt => opt.value === docType);
        return option ? option.label : docType;
    };

    const getDocumentId = (doc) => doc.document_id || doc.id;

    const getUploadedCount = () => documents.filter(doc => REQUIRED_DOCUMENTS.includes(doc.document_type)).length;
    const isAllDocumentsUploaded = getUploadedCount() === REQUIRED_DOCUMENTS.length;

    if (loading) {
        return <div className="page-container fade-in"><div className="loading-spinner">Loading documents...</div></div>;
    }

    if (!profileComplete) {
        return (
            <div className="page-container fade-in">
                <div className="form-card" style={{ textAlign: 'center', padding: '60px' }}>
                    <InfoIcon size={48} />
                    <h2 style={{ marginTop: '20px', color: '#ef4444' }}>Profile Incomplete</h2>
                    <p style={{ marginTop: '10px', color: '#64748b' }}>
                        Please complete your Personal Details before uploading documents.
                    </p>
                    <button className="btn-primary" onClick={() => navigate('/applicant/profile')} style={{ marginTop: '20px' }}>
                        Go to Complete Profile
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal">
                <div className="breadcrumb-minimal">DASHBOARD &gt; ADMISSION MANAGEMENT &gt; PERSONAL DOCUMENTS</div>
                <h1 className="page-title-minimal">Personal Documents</h1>
            </div>

            {/* Progress Banner */}
            <div className={`progress-banner ${isAllDocumentsUploaded ? 'complete' : 'incomplete'}`}>
                <div className="progress-banner-icon">{isAllDocumentsUploaded ? <CheckIcon /> : <InfoIcon />}</div>
                <div className="progress-banner-content">
                    <strong>{getUploadedCount()} of {REQUIRED_DOCUMENTS} required documents uploaded</strong>
                    <div className="progress-banner-bar">
                        <div className="progress-banner-fill" style={{ width: `${(getUploadedCount() / REQUIRED_DOCUMENTS) * 100}%` }}></div>
                    </div>
                </div>
            </div>

            <div className="info-banner">
                <InfoIcon />
                <div>
                    <strong>Instructions:</strong>
                    <ul className="info-list">
                        <li>Maximum {MAX_DOCUMENTS} documents allowed</li>
                        <li>Required documents: CNIC Front, CNIC Back, Domicile, Photograph</li>
                        <li>Each document type can only be uploaded once</li>
                        <li>Each file size must be ≤ 1 MB</li>
                        <li>Supported formats: PDF, JPG, PNG</li>
                    </ul>
                </div>
            </div>

            <div className="form-card" style={readOnly ? { display: 'none' } : undefined}>
                <div className="section-header">
                    <div className="section-header-icon"><FileIcon /></div>
                    <h2 className="section-title">Upload Document</h2>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Document Type <span className="required">*</span></label>
                        <select 
                            className={`field-input field-select ${touched.docType && errors.docType ? 'error' : ''} ${touched.docType && !errors.docType && selectedDocType ? 'success' : ''}`}
                            value={selectedDocType}
                            onChange={(e) => handleDocTypeChange(e.target.value)}
                            onBlur={() => setTouched(prev => ({ ...prev, docType: true }))}
                        >
                            <option value="">Select Document Type</option>
                            {documentTypeOptions.map(option => (
                                <option key={option.value} value={option.value} disabled={documents.some(doc => doc.document_type === option.value)}>
                                    {option.label} {option.required && '(Required)'}
                                    {documents.some(doc => doc.document_type === option.value) && " ✓"}
                                </option>
                            ))}
                        </select>
                        {touched.docType && errors.docType && <div className="error-message">{errors.docType}</div>}
                    </div>

                    <div className="field-group">
                        <label className="field-label">File Upload <span className="required">*</span></label>
                        <div 
                            className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''} ${touched.file && errors.file ? 'error' : ''}`}
                            onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input type="file" ref={fileInputRef} onChange={handleFile} style={{ display: 'none' }} accept=".pdf,.jpg,.jpeg,.png" />
                            {selectedFile ? (
                                <div className="file-selected">
                                    <FileIcon />
                                    <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                                    <button className="file-remove-btn" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}>
                                        <XIcon />
                                    </button>
                                </div>
                            ) : (
                                <div className="file-drop-content">
                                    <UploadIcon />
                                    <p><strong>Click to upload</strong> or drag and drop</p>
                                    <span className="file-hint">PDF, JPG, PNG (max 1 MB)</span>
                                </div>
                            )}
                        </div>
                        {touched.file && errors.file && <div className="error-message">{errors.file}</div>}
                    </div>
                </div>

                {errors.limit && <div className="error-message">{errors.limit}</div>}
                {errors.exists && <div className="error-message">{errors.exists}</div>}

                <div className="form-actions">
                    <button className="btn-verify" onClick={() => { setSelectedFile(null); setSelectedDocType(''); if (fileInputRef.current) fileInputRef.current.value = ''; setErrors({}); setTouched({}); }}>
                        Cancel
                    </button>
                    <button className="btn-save" onClick={handleSave} disabled={!selectedFile || !selectedDocType || uploading}>
                        {uploading ? 'Uploading...' : 'Upload Document'}
                    </button>
                </div>
            </div>

            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><FileIcon /></div>
                    <h2 className="section-title">Uploaded Documents ({documents.length}/{MAX_DOCUMENTS})</h2>
                </div>
                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr><th>Document Type</th><th>File Name</th><th>Status</th><th>Uploaded At</th>{!readOnly && <th>Action</th>}</tr>
                        </thead>
                        <tbody>
                            {documents.length === 0 ? (
                                <tr><td colSpan="5" className="empty-row">No documents found</td></tr>
                            ) : (
                                documents.map((doc) => (
                                    <tr key={getDocumentId(doc)}>
                                        <td>{getDocumentTypeDisplay(doc.document_type)} {REQUIRED_DOCUMENTS.includes(doc.document_type) && <span className="required-badge">Required</span>}</td>
                                        <td>{doc.file_name}</td>
                                        <td><span className={getStatusBadgeClass(doc)}>{getStatusText(doc)}</span></td>
                                        <td>{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}</td>
                                        {!readOnly && (
                                        <td><button className="action-btn danger" onClick={() => handleRemove(getDocumentId(doc))}><TrashIcon /></button></td>
                                        )}
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default PersonalDocumentsPage;