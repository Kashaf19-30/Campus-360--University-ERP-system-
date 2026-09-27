import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';

/** Return true if user can see a nav item (permission, permissions[], or always). */
export function canSeeNavItem(item, hasPermission) {
    if (item.always) return true;
    if (item.permission) return hasPermission(item.permission);
    if (item.permissions?.length) {
        return item.permissions.some((p) => hasPermission(p));
    }
    return true;
}

/** Filter top-level nav items and nested children by RBAC permissions. */
export function filterNavItems(navItems, hasPermission) {
    if (!Array.isArray(navItems)) return [];

    return navItems
        .map((item) => {
            if (item.children?.length) {
                const children = item.children.filter((child) => canSeeNavItem(child, hasPermission));
                if (!children.length) return null;
                if (!canSeeNavItem(item, hasPermission) && !children.length) return null;
                return { ...item, children };
            }
            return canSeeNavItem(item, hasPermission) ? item : null;
        })
        .filter(Boolean);
}

/** Hook: memoized nav list filtered by current user's permissions. */
export function useFilteredNavItems(navItems) {
    const { hasPermission, permissions } = useAuth();
    return useMemo(
        () => filterNavItems(navItems, hasPermission),
        [navItems, hasPermission, permissions]
    );
}

/** Check route access (single permission or any of a list). */
export function canAccessRoute({ permission, permissions, always }, hasPermission) {
    if (always) return true;
    if (permission) return hasPermission(permission);
    if (permissions?.length) return permissions.some((p) => hasPermission(p));
    return true;
}
