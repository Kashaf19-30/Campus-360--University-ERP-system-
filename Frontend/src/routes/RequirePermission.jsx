import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { canAccessRoute } from './navPermissions';

/**
 * Gate a dashboard page by RBAC permission(s).
 * Redirects to dashboard home when access is denied.
 */
export default function RequirePermission({
    permission,
    permissions,
    always,
    redirectTo = '..',
    children,
}) {
    const { hasPermission } = useAuth();
    const allowed = canAccessRoute({ permission, permissions, always }, hasPermission);

    if (!allowed) {
        return <Navigate to={redirectTo} replace />;
    }

    return children;
}
