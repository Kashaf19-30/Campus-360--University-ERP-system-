// src/dashboard/Pages/AcademicInformationPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { getAcademicRecords, getMyDocuments, deleteAcademicRecord } from '../../../services/admissionService';
import { SearchIcon, PlusIcon, InfoIcon, TrashIcon } from '../../Icons';

const AcademicInformationPage = ({ onAddClick, onAcademicRecordChange, readOnly = false }) => {
    const navigate = useNavigate();
    const { token } = useAuth();
    const [search, setSearch] = useState('');
    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(false);
    const [hasDocuments, setHasDocuments] = useState(false);
    const [checkingDocs, setCheckingDocs] = useState(true);

    const fetchRecords = async () => {
        setLoading(true);
        try {
            const data = await getAcademicRecords(token);
            const recordsArray = Array.isArray(data) ? data : data?.results || [];
            setRecords(recordsArray);
            
            // Notify parent component that academic records changed
            if (onAcademicRecordChange) {
                await onAcademicRecordChange();
            }
        } catch (error) {
            console.error('Failed to load records:', error);
            setRecords([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const checkDocuments = async () => {
            try {
                const docs = await getMyDocuments(token);
                const hasDocs = docs && docs.length > 0;
                setHasDocuments(hasDocs);
                
                if (!hasDocs) {
                    setCheckingDocs(false);
                    return;
                }
                
                await fetchRecords();
            } catch (error) {
                console.error('Failed to check documents:', error);
                setHasDocuments(false);
            } finally {
                setCheckingDocs(false);
            }
        };
        
        if (token) {
            checkDocuments();
        } else {
            setCheckingDocs(false);
            setLoading(false);
        }
    }, [token]);

    const handleDeleteRecord = async (recordId, recordTitle) => {
        if (!confirm(`Are you sure you want to delete "${recordTitle}"? This action cannot be undone.`)) {
            return;
        }
        
        setDeleting(true);
        try {
            await deleteAcademicRecord(recordId, token);
            alert('Academic record deleted successfully!');
            await fetchRecords();
        } catch (error) {
            console.error('Delete failed:', error);
            alert('Failed to delete academic record: ' + (error.response?.data?.message || error.message));
        } finally {
            setDeleting(false);
        }
    };

    // Get display name for qualification level
    const getLevelDisplay = (level) => {
        if (level === 'matric') return 'Matric / O-Level';
        if (level === 'inter') return 'Intermediate / A-Level';
        return level || '—';
    };

    const filteredRecords = records.filter(record => {
        const searchLower = search.toLowerCase();
        return (
            (record.authority || '').toLowerCase().includes(searchLower) ||
            (record.institute || '').toLowerCase().includes(searchLower) ||
            (record.qualification || '').toLowerCase().includes(searchLower)
        );
    });

    const getFieldValue = (value, fallback = '—') => {
        return value !== undefined && value !== null && value !== '' ? value : fallback;
    };

    if (checkingDocs) {
        return (
            <div className="page-container fade-in">
                <div className="loading-spinner">Checking requirements...</div>
            </div>
        );
    }

    if (!hasDocuments) {
        return (
            <div className="page-container fade-in">
                <div className="form-card" style={{ textAlign: 'center', padding: '60px' }}>
                    <InfoIcon size={48} />
                    <h2 style={{ marginTop: '20px', color: '#ef4444' }}>Documents Required</h2>
                    <p style={{ marginTop: '10px', color: '#64748b' }}>
                        Please upload your Personal Documents before accessing Academic Information.
                    </p>
                    <p style={{ marginTop: '5px', color: '#64748b', fontSize: '14px' }}>
                        Required documents: CNIC Front, CNIC Back, Domicile, Photograph
                    </p>
                    <button 
                        className="btn-primary" 
                        onClick={() => navigate('/applicant/personal-docs')}
                        style={{ marginTop: '20px' }}
                    >
                        Go to Personal Documents
                    </button>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="page-container fade-in">
                <div className="loading-spinner">Loading academic records...</div>
            </div>
        );
    }

    return (
        <div className="page-container fade-in">
            <div className="page-header-minimal">
                <div className="breadcrumb-minimal">DASHBOARD &gt; ADMISSION MANAGEMENT &gt; ACADEMIC INFORMATION</div>
                <h1 className="page-title-minimal">Academic Information</h1>
            </div>

            <div className="form-card">
                <div className="table-toolbar">
                    <div className="search-bar table-search">
                        <span style={{ color: '#9ca3af', display: 'flex' }}><SearchIcon /></span>
                        <input 
                            type="text" 
                            placeholder="Search records..." 
                            className="search-input" 
                            value={search} 
                            onChange={(e) => setSearch(e.target.value)} 
                        />
                    </div>
                    <button className="btn-add" onClick={onAddClick} disabled={deleting || readOnly} style={readOnly ? { display: 'none' } : undefined}>
                        <PlusIcon /> <span>ADD</span>
                    </button>
                </div>

                <div className="data-table-wrapper">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Sr#</th>
                                <th>Issuing Authority</th>
                                <th>Level</th>
                                <th>Qualification</th>
                                <th>Institute</th>
                                <th>Obtained Marks</th>
                                <th>Total Marks</th>
                                <th>Start Year</th>
                                <th>End Year</th>
                                {!readOnly && <th>Action</th>}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredRecords.length === 0 ? (
                                <tr>
                                    <td colSpan="10" className="empty-row">
                                        {search ? 'No matching records found' : 'No record found'}
                                    </td>
                                </tr>
                            ) : (
                                filteredRecords.map((record, i) => (
                                    <tr key={record.id}>
                                        <td>{i + 1}</td>
                                        <td>{getFieldValue(record.authority)}</td>
                                        <td>{getLevelDisplay(record.qualification_level)}</td>
                                        <td>{getFieldValue(record.qualification)}</td>
                                        <td>{getFieldValue(record.institute)}</td>
                                        <td>{getFieldValue(record.obtained)}</td>
                                        <td>{getFieldValue(record.total)}</td>
                                        <td>{getFieldValue(record.start_year)}</td>
                                        <td>{getFieldValue(record.end_year)}</td>
                                        {!readOnly && (
                                        <td>
                                            <button 
                                                className="action-btn danger" 
                                                onClick={() => handleDeleteRecord(record.id, record.qualification || 'Record')}
                                                disabled={deleting}
                                                title="Delete Record"
                                            >
                                                <TrashIcon />
                                            </button>
                                        </td>
                                        )}
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {filteredRecords.length > 0 && (
                    <div className="table-pagination">
                        <span className="pagination-info">
                            Showing 1 to {filteredRecords.length} of {filteredRecords.length} entries
                        </span>
                        <div className="pagination-controls">
                            <button className="pagination-btn" disabled>Previous</button>
                            <button className="pagination-btn active">1</button>
                            <button className="pagination-btn" disabled>Next</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AcademicInformationPage;