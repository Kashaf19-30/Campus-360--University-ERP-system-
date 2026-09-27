import { useNavigate } from 'react-router-dom';
import { pathForPage } from './paths';

/** Navigate within a role dashboard by page id (matches sidebar nav item ids). */
export function useDashboardNavigate(basePath) {
    const navigate = useNavigate();
    return (pageId) => navigate(pathForPage(basePath, pageId));
}
