import React, { useState, useRef, useEffect } from 'react';

import { useAuth } from '../../../context/AuthContext';

import { downloadAdmissionChallan } from '../../../services/admissionService';

import { FileIcon } from '../../Icons';



const ApplicantChallanPanel = ({ application }) => {

    const { token } = useAuth();

    const [challanInfo, setChallanInfo] = useState(null);

    const [loading, setLoading] = useState(false);



    useEffect(() => {

        if (!token) return;

        downloadAdmissionChallan(token, 'json')

            .then(res => setChallanInfo(res.data))

            .catch(() => {});

    }, [token, application?.application_number]);



    const handleDownload = async () => {

        setLoading(true);

        try {

            const response = await downloadAdmissionChallan(token, 'pdf');

            const blob = new Blob([response.data], { type: 'application/pdf' });

            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');

            a.href = url;

            a.download = `Admission-Challan-${challanInfo?.challan_number || application?.application_number || 'challan'}.pdf`;

            a.click();

            URL.revokeObjectURL(url);

            if (!challanInfo) {

                const infoRes = await downloadAdmissionChallan(token, 'json');

                setChallanInfo(infoRes.data);

            }

        } catch (error) {

            alert(error.response?.data?.error || 'Failed to download challan PDF');

        } finally {

            setLoading(false);

        }

    };



    const amountDisplay = challanInfo?.amount_display || (application?.challan_amount ? `Rs. ${application.challan_amount}` : null);

    const feeStatus = application?.challan_paid
        ? 'Payment confirmed by Finance — your application will move to admin review.'
        : 'Submit fee at the university finance office. Finance will mark your payment as received.';



    return (

        <div className="form-card" style={{ marginBottom: '20px', border: '2px solid #4169E1', background: 'var(--bg-card)' }}>

            <div className="section-header">

                <div className="section-header-icon"><FileIcon /></div>

                <h2 className="section-title">Admission Fee Challan</h2>

            </div>

            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>

                Your application <strong>{application?.application_number}</strong> has been submitted.

                Download your admission fee challan (PDF), pay at the <strong>university finance office</strong>,

                and wait for Finance to confirm payment. You do not need to upload a paid challan photo.

            </p>

            {challanInfo && (

                <div className="info-banner compact" style={{ marginBottom: '16px', display: 'grid', gap: '4px' }}>

                    <span>Challan: <strong>{challanInfo.challan_number}</strong> | Amount: <strong>{challanInfo.amount_display}</strong></span>

                    <span>Program: <strong>{challanInfo.program_name}</strong> ({challanInfo.program_code})</span>

                    <span>Applicant: <strong>{challanInfo.applicant_name}</strong> | CNIC: {challanInfo.cnic}</span>

                    <span>Due: <strong>{challanInfo.due_date}</strong></span>

                </div>

            )}

            {!challanInfo && amountDisplay && (

                <div className="info-banner compact" style={{ marginBottom: '16px' }}>

                    <span>Amount: <strong>{amountDisplay}</strong></span>

                </div>

            )}

            <div className="info-banner" style={{ marginBottom: '16px', background: application?.challan_paid ? 'var(--gradient-success)' : undefined }}>

                <strong>Status:</strong> {feeStatus}

            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>

                <button className="btn-update" onClick={handleDownload} disabled={loading || application?.challan_paid}>
                    <FileIcon /> {application?.challan_paid ? 'Challan Paid — Download Disabled' : (loading ? 'Preparing PDF...' : 'Download Challan PDF')}
                </button>

            </div>

        </div>

    );

};



export default ApplicantChallanPanel;
