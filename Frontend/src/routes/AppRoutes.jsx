import React, { Suspense, lazy } from 'react';

import { Routes, Route, Navigate } from 'react-router-dom';

import ProtectedRoute from './ProtectedRoute';

import GuestRoute from './GuestRoute';

import ScrollToTop from './ScrollToTop';

import { LoadingSpinner } from '../dashboard/shared/helpers';



import LandingPage from '../Pages/LandingPage';

import LoginPage from '../Pages/LoginPage';

import SignupPage from '../Pages/SignupPage';

import ForgotPasswordPage from '../Pages/ForgotPasswordPage';
import ResetPasswordPage from '../Pages/ResetPasswordPage';

import HistoryPage from '../Pages/HistoryPage';



const AdminDashboard = lazy(() => import('../dashboard/admin/Dashboard'));

const StudentDashboard = lazy(() => import('../dashboard/student/Dashboard'));

const TeacherDashboard = lazy(() => import('../dashboard/teacher/Dashboard'));

const ApplicantDashboard = lazy(() => import('../dashboard/applicant/Dashboard'));
const FinanceDashboard = lazy(() => import('../dashboard/finance/Dashboard'));



import { dashboardPathForRole } from './paths';

import { useAuth } from '../context/AuthContext';



function DashboardRedirect() {

    const { user } = useAuth();

    if (!user) return <Navigate to="/login" replace />;

    if (!user.user_type) return <Navigate to="/login" replace />;

    return <Navigate to={dashboardPathForRole(user.user_type)} replace />;

}



const DashboardFallback = () => (

    <div className="dashboard-layout">

        <LoadingSpinner message="Loading dashboard..." />

    </div>

);



export default function AppRoutes() {

    return (

        <>

            <ScrollToTop />

            <Suspense fallback={<DashboardFallback />}>

                <Routes>

                    <Route path="/" element={<LandingPage />} />

                    <Route path="/history" element={<HistoryPage />} />

                    <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />

                    <Route path="/signup" element={<GuestRoute><SignupPage /></GuestRoute>} />

                    <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
                    <Route path="/reset-password" element={<GuestRoute><ResetPasswordPage /></GuestRoute>} />



                    <Route path="/dashboard" element={<DashboardRedirect />} />



                    <Route path="/admin/*" element={

                        <ProtectedRoute allowedRoles={['admin']}>

                            <AdminDashboard />

                        </ProtectedRoute>

                    } />

                    <Route path="/student/*" element={

                        <ProtectedRoute allowedRoles={['student']}>

                            <StudentDashboard />

                        </ProtectedRoute>

                    } />

                    <Route path="/teacher/*" element={

                        <ProtectedRoute allowedRoles={['teacher']}>

                            <TeacherDashboard />

                        </ProtectedRoute>

                    } />

                    <Route path="/applicant/*" element={

                        <ProtectedRoute allowedRoles={['applicant']}>

                            <ApplicantDashboard />

                        </ProtectedRoute>

                    } />

                    <Route path="/finance/*" element={

                        <ProtectedRoute allowedRoles={['finance_officer']}>

                            <FinanceDashboard />

                        </ProtectedRoute>

                    } />



                    <Route path="*" element={<Navigate to="/" replace />} />

                </Routes>

            </Suspense>

        </>

    );

}

