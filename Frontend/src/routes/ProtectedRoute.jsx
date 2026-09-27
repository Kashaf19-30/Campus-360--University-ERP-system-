import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { dashboardPathForRole } from './paths';
import { LoadingSpinner } from '../dashboard/shared/helpers';

export default function ProtectedRoute({ children, allowedRoles }) {
    const { user, token, authReady, logout } = useAuth();
    const location = useLocation();

    if (token && !authReady) {
        return <LoadingSpinner message="Loading your session..." />;
    }

    if (!user) {
        const from = location.pathname + location.search;
        return <Navigate to="/login" state={{ from }} replace />;
    }

    if (!user.user_type) {
        logout();
        const from = location.pathname + location.search;
        return <Navigate to="/login" state={{ from }} replace />;
    }

    if (allowedRoles?.length && !allowedRoles.includes(user.user_type)) {
        return <Navigate to={dashboardPathForRole(user.user_type)} replace />;
    }

    return children;
}
