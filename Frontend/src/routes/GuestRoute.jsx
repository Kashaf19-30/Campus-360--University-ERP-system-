import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

import { loginRedirectPath } from './paths';



/** Redirect authenticated users away from login/signup to their dashboard. */

export default function GuestRoute({ children }) {

    const { user } = useAuth();
    const location = useLocation();

    if (user?.user_type) {

        return <Navigate to={loginRedirectPath(user.user_type, location.state?.from)} replace />;

    }

    return children;

}

