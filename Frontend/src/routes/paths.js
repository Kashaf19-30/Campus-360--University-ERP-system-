/** Role-based dashboard base paths and navigation helpers. */

export const ROLE_DASHBOARD = {
    admin: '/admin',
    student: '/student',
    teacher: '/teacher',
    applicant: '/applicant',
    finance_officer: '/finance',
};

export function dashboardPathForRole(userType) {
    return ROLE_DASHBOARD[userType] || ROLE_DASHBOARD.applicant;
}

export function isPathForRole(pathname, userType) {
    const base = dashboardPathForRole(userType);
    const path = pathname.replace(/\/$/, '') || '/';
    return path === base || path.startsWith(`${base}/`);
}

export function loginRedirectPath(userType, fromPath) {
    const base = dashboardPathForRole(userType);
    if (!fromPath || fromPath === '/login' || fromPath === '/signup') return base;
    if (isPathForRole(fromPath.split('?')[0], userType)) return fromPath;
    return base;
}

/** Extract nav page id from URL (e.g. /admin/students → students, /admin → home). */
export function pageIdFromPath(pathname, basePath) {
    const base = basePath.replace(/\/$/, '');
    const path = pathname.replace(/\/$/, '') || '/';
    if (path === base) return 'home';
    if (path.startsWith(`${base}/`)) {
        return path.slice(base.length + 1).split('/')[0] || 'home';
    }
    return 'home';
}

export function pathForPage(basePath, pageId) {
    const base = basePath.replace(/\/$/, '');
    if (!pageId || pageId === 'home') return base;
    return `${base}/${pageId}`;
}
