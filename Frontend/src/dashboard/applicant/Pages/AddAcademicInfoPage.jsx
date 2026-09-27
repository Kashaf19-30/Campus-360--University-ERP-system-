import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { addAcademicRecord, uploadDocument, deleteDocument, getMyDocuments, getAcademicRecords } from '../../../services/admissionService';
import { getAcademicRecordError } from '../../../utils/validation';
import { saveFormDraft, loadFormDraft, clearFormDraft } from '../../../utils/formDraft';
import { FileIcon, UploadIcon, XIcon, TrashIcon, PlusIcon, InfoIcon } from '../../Icons';

const INITIAL_FIELDS = {
    authority: '',
    qualification_level: '',
    qualification: '',
    institute: '',
    roll_number: '',
    start_year: '',
    end_year: '',
    obtained: '',
    total: '',
};

const AddAcademicInfoPage = ({ onCancel }) => {
    const { token, user } = useAuth();
    const [formFields, setFormFields] = useState(() => {
        const draft = loadFormDraft(user?.user_id, 'academic');
        return draft || INITIAL_FIELDS;
    });
    const [uploadedDocs, setUploadedDocs] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [uploadingDocs, setUploadingDocs] = useState(false);
    const [loadingDocs, setLoadingDocs] = useState(true);
    const [fieldErrors, setFieldErrors] = useState({});
    const [existingRecords, setExistingRecords] = useState([]);
    const fileRef = useRef(null);

    const hasMatricRecord = existingRecords.some(r => r.qualification_level === 'matric');
    const hasInterRecord = existingRecords.some(r => r.qualification_level === 'inter');
    const todayStr = new Date().toISOString().split('T')[0];

    const authorityOptions = [
        { value: 'BISE Lahore', label: 'BISE Lahore' },
        { value: 'BISE Gujranwala', label: 'BISE Gujranwala' },
        { value: 'BISE Faisalabad', label: 'BISE Faisalabad' },
        { value: 'BISE Multan', label: 'BISE Multan' },
        { value: 'BISE Rawalpindi', label: 'BISE Rawalpindi' },
        { value: 'BISE Sargodha', label: 'BISE Sargodha' },
        { value: 'BISE Bahawalpur', label: 'BISE Bahawalpur' },
        { value: 'BISE Dera Ghazi Khan', label: 'BISE Dera Ghazi Khan' },
        { value: 'BISE Sahiwal', label: 'BISE Sahiwal' },
        { value: 'BISE AJK', label: 'BISE AJK' },
    ];

    const qualificationOptions = {
        matric: [
            'Matric Science',
            'Matric Arts',
            'Matric Biology',
            'Matric Computer Science',
            'Matric General Science'
        ],
        inter: [
            'Fsc Pre Medical',
            'Fsc Pre Engineering',
            'ICS Physics',
            'ICS Statistics',
            'ICS Economics',
            'ICOM',
            'FA Arts / Humanities'
        ]
    };

    // Document title options based on qualification level (marksheet OR certificate — not both required)
    const getDocumentTitleOptions = () => {
        if (formFields.qualification_level === 'matric') {
            return [{ value: 'matric_marksheet', label: 'Matric Marksheet' }];
        } else if (formFields.qualification_level === 'inter') {
            return [{ value: 'inter_marksheet', label: 'Inter Marksheet' }];
        }
        return [];
    };

    useEffect(() => {
        if (user?.user_id) {
            saveFormDraft(user.user_id, 'academic', formFields);
        }
    }, [formFields, user?.user_id]);

    useEffect(() => {
        const loadData = async () => {
            if (!token) return;
            try {
                const [allDocs, recordsData] = await Promise.all([
                    getMyDocuments(token),
                    getAcademicRecords(token),
                ]);
                const docsArray = Array.isArray(allDocs) ? allDocs : (allDocs?.results || []);
                const academicDocs = docsArray.filter(doc =>
                    ['matric_marksheet', 'matric_certificate', 'inter_marksheet', 'inter_certificate'].includes(doc.document_type)
                );
                setUploadedDocs(academicDocs);
                const recordsArray = Array.isArray(recordsData) ? recordsData : (recordsData?.results || []);
                setExistingRecords(recordsArray);
            } catch (error) {
                console.error('Failed to load academic data:', error);
            } finally {
                setLoadingDocs(false);
            }
        };
        loadData();
    }, [token]);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(e.type === 'dragenter' || e.type === 'dragover');
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const handleAddDoc = async () => {
        if (!selectedFile) {
            alert('Please select a file first');
            return;
        }
        
        const documentType = document.getElementById('acad-doc-title')?.value;
        if (!documentType || documentType === '') {
            alert('Please select a document title');
            return;
        }
        
        // REMOVED: Maximum 4 documents restriction
        
        if (selectedFile.size > 1048576) {
            alert('File size must be ≤ 1 MB.');
            return;
        }

        // Check if document type already exists (optional - you can remove this too)
        const alreadyExists = uploadedDocs.some(doc => doc.document_type === documentType);
        if (alreadyExists) {
            alert('You have already uploaded this document type. Please remove the existing one first.');
            return;
        }

        setUploadingDocs(true);
        
        try {
            // Upload document to backend
            const result = await uploadDocument({
                document_type: documentType,
                file: selectedFile
            }, token);
            
            // Refresh the list to get the newly uploaded document
            const allDocs = await getMyDocuments(token);
            const docsArray = Array.isArray(allDocs) ? allDocs : (allDocs?.results || []);
            const academicDocs = docsArray.filter(doc => 
                doc.document_type === 'matric_marksheet' || 
                doc.document_type === 'matric_certificate' ||
                doc.document_type === 'inter_marksheet' || 
                doc.document_type === 'inter_certificate'
            );
            setUploadedDocs(academicDocs);
            
            setSelectedFile(null);
            if (fileRef.current) {
                fileRef.current.value = '';
            }
            alert(result?.message || 'Document uploaded successfully!');
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Failed to upload document: ' + (error.response?.data?.error || error.message));
        } finally {
            setUploadingDocs(false);
        }
    };

    const handleRemoveDoc = async (documentId, documentType) => {
        if (!confirm('Are you sure you want to remove this document?')) return;
        
        try {
            await deleteDocument(documentId, token);
            
            // Update local list
            setUploadedDocs(uploadedDocs.filter(doc => doc.document_id !== documentId));
            alert('Document removed successfully');
        } catch (error) {
            console.error('Delete failed:', error);
            alert('Failed to remove document');
        }
    };

    const currentYear = new Date().getFullYear();
    const years = Array.from({ length: 30 }, (_, i) => currentYear - i);

    const validateFields = (fields = formFields) => getAcademicRecordError(fields);

    const updateField = (key, value) => {
        const next = { ...formFields, [key]: value };
        setFormFields(next);
        if (fieldErrors[key]) {
            const errors = validateFields(next);
            setFieldErrors((prev) => ({ ...prev, [key]: errors[key] || '' }));
        }
    };

    const handleFieldBlur = (key) => {
        const errors = validateFields();
        setFieldErrors((prev) => ({ ...prev, [key]: errors[key] || '' }));
    };

    const renderFieldError = (key) => (
        fieldErrors[key] ? <span className="field-error">{fieldErrors[key]}</span> : null
    );

    const formatApiErrors = (data) => {
        if (!data || typeof data !== 'object') return 'Request failed';
        return Object.entries(data).map(([k, v]) => {
            const label = k === 'obtained' ? 'Obtained marks' : k === 'total' ? 'Total marks' : k;
            return `${label}: ${Array.isArray(v) ? v[0] : v}`;
        }).join('\n');
    };

    const handleSubmit = async () => {
        const errors = validateFields();
        setFieldErrors(errors);
        const errorMessages = Object.values(errors).filter(Boolean);
        if (errorMessages.length > 0) {
            alert(errorMessages[0]);
            return;
        }

        const level = formFields.qualification_level;
        const docType = level === 'matric' ? 'matric_marksheet' : level === 'inter' ? 'inter_marksheet' : '';

        if (selectedFile) {
            if (selectedFile.size > 1048576) {
                alert('File size must be ≤ 1 MB.');
                return;
            }
            if (!docType) {
                alert('Select qualification level before choosing a document.');
                return;
            }
        }

        setSubmitting(true);
        try {
            let docs = [...uploadedDocs];
            if (selectedFile && docType) {
                await uploadDocument({ document_type: docType, file: selectedFile }, token);
                const allDocs = await getMyDocuments(token);
                const docsArray = Array.isArray(allDocs) ? allDocs : (allDocs?.results || []);
                docs = docsArray.filter(doc =>
                    ['matric_marksheet', 'matric_certificate', 'inter_marksheet', 'inter_certificate'].includes(doc.document_type)
                );
                setUploadedDocs(docs);
                setSelectedFile(null);
                if (fileRef.current) fileRef.current.value = '';
            }

            const levelDocTypes = level === 'matric'
                ? ['matric_marksheet', 'matric_certificate']
                : level === 'inter'
                    ? ['inter_marksheet', 'inter_certificate']
                    : [];
            const hasLevelDoc = levelDocTypes.some(t => docs.some(d => d.document_type === t));
            if (levelDocTypes.length > 0 && !hasLevelDoc) {
                alert('Select and attach a marksheet file, then save.');
                return;
            }

            const recordData = {
                authority: formFields.authority,
                qualification_level: formFields.qualification_level,
                qualification: formFields.qualification,
                institute: formFields.institute,
                roll_number: formFields.roll_number.trim(),
                start_year: parseInt(formFields.start_year, 10),
                end_year: parseInt(formFields.end_year, 10),
                grading_system: 'marks',
                obtained: parseFloat(formFields.obtained),
                total: parseFloat(formFields.total),
            };

            await addAcademicRecord(recordData, token);
            if (user?.user_id) clearFormDraft(user.user_id, 'academic');
            alert('Academic record and document saved successfully!');
            onCancel();
        } catch (error) {
            console.error('Error saving academic record:', error);
            alert('Failed to save:\n' + formatApiErrors(error.response?.data));
        } finally {
            setSubmitting(false);
        }
    };

    const getQualificationOptions = () => {
        if (formFields.qualification_level === 'matric') {
            return qualificationOptions.matric;
        } else if (formFields.qualification_level === 'inter') {
            return qualificationOptions.inter;
        }
        return [];
    };

    if (loadingDocs) {
        return (
            <div className="page-container fade-in">
                <div className="loading-spinner">Loading documents...</div>
            </div>
        );
    }

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal">
                <div className="breadcrumb-minimal">DASHBOARD &gt; ACADEMIC INFORMATION &gt; ADD NEW</div>
                <h1 className="page-title-minimal">Add Academic Information</h1>
            </div>

            {/* Academic Form */}
            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><FileIcon /></div>
                    <h2 className="section-title">Academic Details</h2>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Issuing Authority (Board/University) <span className="required">*</span></label>
                        <select 
                            className={`field-input field-select${fieldErrors.authority ? ' error' : ''}`}
                            value={formFields.authority} 
                            onChange={(e) => updateField('authority', e.target.value)}
                            onBlur={() => handleFieldBlur('authority')}
                        >
                            <option value="">Select Authority</option>
                            {authorityOptions.map(board => (
                                <option key={board.value} value={board.value}>{board.label}</option>
                            ))}
                        </select>
                        {renderFieldError('authority')}
                    </div>
                    <div className="field-group">
                        <label className="field-label">Qualification Level <span className="required">*</span></label>
                        <select 
                            className={`field-input field-select${fieldErrors.qualification_level ? ' error' : ''}`}
                            value={formFields.qualification_level} 
                            onChange={(e) => {
                                const next = { ...formFields, qualification_level: e.target.value, qualification: '' };
                                setFormFields(next);
                                if (fieldErrors.qualification_level || fieldErrors.qualification) {
                                    const errors = validateFields(next);
                                    setFieldErrors((prev) => ({
                                        ...prev,
                                        qualification_level: errors.qualification_level || '',
                                        qualification: errors.qualification || '',
                                    }));
                                }
                            }}
                            onBlur={() => handleFieldBlur('qualification_level')}
                        >
                            <option value="">Select Level</option>
                            <option value="matric" disabled={hasMatricRecord || hasInterRecord}>
                                Matric{hasMatricRecord ? ' (already added)' : hasInterRecord ? ' (add Inter first — cannot add Matric after Inter)' : ''}
                            </option>
                            <option value="inter" disabled={hasInterRecord || !hasMatricRecord}>
                                Intermediate{hasInterRecord ? ' (already added)' : !hasMatricRecord ? ' (add Matric first)' : ''}
                            </option>
                        </select>
                        {renderFieldError('qualification_level')}
                    </div>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Qualification <span className="required">*</span></label>
                        {getQualificationOptions().length > 0 ? (
                            <select 
                                className={`field-input field-select${fieldErrors.qualification ? ' error' : ''}`}
                                value={formFields.qualification} 
                                onChange={(e) => updateField('qualification', e.target.value)}
                                onBlur={() => handleFieldBlur('qualification')}
                            >
                                <option value="">Select Qualification</option>
                                {getQualificationOptions().map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : (
                            <input 
                                type="text" 
                                className="field-input" 
                                placeholder="Select Qualification Level first" 
                                value={formFields.qualification} 
                                disabled
                            />
                        )}
                        {renderFieldError('qualification')}
                    </div>
                    <div className="field-group">
                        <label className="field-label">Institute <span className="required">*</span></label>
                        <input 
                            type="text" 
                            className={`field-input${fieldErrors.institute ? ' error' : ''}`}
                            placeholder="Enter Institute Name" 
                            value={formFields.institute} 
                            onChange={(e) => updateField('institute', e.target.value)}
                            onBlur={() => handleFieldBlur('institute')}
                        />
                        {renderFieldError('institute')}
                    </div>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Roll No. <span className="required">*</span></label>
                        <input 
                            type="text" 
                            className={`field-input${fieldErrors.roll_number ? ' error' : ''}`}
                            placeholder="Enter Roll No." 
                            maxLength="20"
                            value={formFields.roll_number}
                            onChange={(e) => updateField('roll_number', e.target.value.replace(/[^A-Za-z0-9-]/g, ''))}
                            onBlur={() => handleFieldBlur('roll_number')}
                        />
                        {renderFieldError('roll_number')}
                    </div>
                    <div className="field-group">
                        <label className="field-label">Start Year <span className="required">*</span></label>
                        <select 
                            className={`field-input field-select${fieldErrors.start_year ? ' error' : ''}`}
                            value={formFields.start_year} 
                            onChange={(e) => updateField('start_year', e.target.value)}
                            onBlur={() => handleFieldBlur('start_year')}
                        >
                            <option value="">Select Year</option>
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                        {renderFieldError('start_year')}
                    </div>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">End Year <span className="required">*</span></label>
                        <select 
                            className={`field-input field-select${fieldErrors.end_year ? ' error' : ''}`}
                            value={formFields.end_year} 
                            onChange={(e) => updateField('end_year', e.target.value)}
                            onBlur={() => handleFieldBlur('end_year')}
                        >
                            <option value="">Select Year</option>
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                        {renderFieldError('end_year')}
                    </div>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Obtained Marks <span className="required">*</span></label>
                        <input 
                            type="text" 
                            className={`field-input${fieldErrors.obtained ? ' error' : ''}`}
                            placeholder="e.g. 950" 
                            maxLength="10"
                            value={formFields.obtained}
                            onChange={(e) => {
                                const val = e.target.value.replace(/\D/g, '');
                                updateField('obtained', val);
                            }}
                            onBlur={() => handleFieldBlur('obtained')}
                        />
                        {renderFieldError('obtained')}
                    </div>
                    <div className="field-group">
                        <label className="field-label">Total Marks <span className="required">*</span></label>
                        <input 
                            type="text" 
                            className={`field-input${fieldErrors.total ? ' error' : ''}`}
                            placeholder="e.g. 1100" 
                            maxLength="10"
                            value={formFields.total}
                            onChange={(e) => {
                                const val = e.target.value.replace(/\D/g, '');
                                updateField('total', val);
                            }}
                            onBlur={() => handleFieldBlur('total')}
                        />
                        {renderFieldError('total')}
                    </div>
                </div>
            </div>

            {/* Document Upload Section */}
            <div className="form-card">
                <div className="section-header">
                    <div className="section-header-icon"><UploadIcon /></div>
                    <h2 className="section-title">Academic Documents</h2>
                </div>

                <div className="info-banner compact">
                    <InfoIcon />
                    <span>Upload your academic marksheet (PDF, JPG, or PNG). One document per qualification level. Max 1 MB.</span>
                </div>

                <div className="two-column-grid">
                    <div className="field-group">
                        <label className="field-label">Document Type <span className="required">*</span></label>
                        <select className="field-input field-select" id="acad-doc-title">
                            <option value="">Select Document Type</option>
                            {getDocumentTitleOptions().map(option => (
                                <option 
                                    key={option.value} 
                                    value={option.value}
                                    disabled={uploadedDocs.some(doc => doc.document_type === option.value)}
                                >
                                    {option.label}
                                    {uploadedDocs.some(doc => doc.document_type === option.value) && " (Uploaded)"}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="field-group">
                        <label className="field-label">File Upload <span className="required">*</span></label>
                        <div 
                            className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
                            onDragEnter={handleDrag} 
                            onDragOver={handleDrag} 
                            onDragLeave={handleDrag} 
                            onDrop={handleDrop}
                            onClick={() => fileRef.current?.click()}
                        >
                            <input 
                                type="file" 
                                ref={fileRef} 
                                onChange={handleFileSelect} 
                                style={{ display: 'none' }} 
                                accept=".pdf,.jpg,.jpeg,.png" 
                            />
                            {selectedFile ? (
                                <div className="file-selected">
                                    <FileIcon />
                                    <span>{selectedFile.name}</span>
                                    <button 
                                        className="file-remove-btn" 
                                        onClick={(e) => { 
                                            e.stopPropagation(); 
                                            setSelectedFile(null);
                                            if (fileRef.current) fileRef.current.value = '';
                                        }}
                                    >
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
                    </div>
                </div>

                <div className="form-actions" style={{ justifyContent: 'flex-start', marginTop: '10px' }}>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
                        Attach your marksheet below — it will upload when you click Save Academic Record.
                    </p>
                </div>

                {/* Uploaded Documents Table */}
                {uploadedDocs.length > 0 && (
                    <div className="data-table-wrapper" style={{ marginTop: '20px' }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Document Type</th>
                                    <th>File Name</th>
                                    <th>Status</th>
                                    <th>Uploaded At</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {uploadedDocs.map((doc) => (
                                    <tr key={doc.document_id}>
                                        <td>{
                                            doc.document_type === 'matric_marksheet' ? 'Matric Marksheet' :
                                            doc.document_type === 'matric_certificate' ? 'Matric Certificate' :
                                            doc.document_type === 'inter_marksheet' ? 'Inter Marksheet' :
                                            doc.document_type === 'inter_certificate' ? 'Inter Certificate' : doc.document_type
                                        }</td>
                                        <td>{doc.file_name}</td>
                                        <td>
                                            <span className={`status-badge ${doc.is_verified ? 'approved' : 'pending'}`}>
                                                {doc.is_verified ? 'VERIFIED' : 'PENDING'}
                                            </span>
                                        </td>
                                        <td>{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}</td>
                                        <td>
                                            <button 
                                                className="action-btn danger" 
                                                onClick={() => handleRemoveDoc(doc.document_id, doc.document_type)}
                                            >
                                                <TrashIcon />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="form-actions">
                <button className="btn-verify" onClick={onCancel} disabled={submitting}>
                    Cancel
                </button>
                <button className="btn-save" onClick={handleSubmit} disabled={submitting}>
                    {submitting ? 'Saving...' : 'Save Academic Record & Document'}
                </button>
            </div>
        </div>
    );
};

export default AddAcademicInfoPage;