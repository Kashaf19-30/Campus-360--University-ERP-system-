import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { getCurrentUser, logoutUser, refreshAuthToken } from '../services/authService';
import { setUnauthorizedHandler, setTokenUpdateHandler } from '../services/api';
import {
    getStoredToken, getStoredUser, persistAuth, clearAuthStorage, migrateLegacyAuthStorage,
} from '../utils/authStorage';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    migrateLegacyAuthStorage();

    const [user, setUser] = useState(() => getStoredUser());
    const [token, setToken] = useState(() => getStoredToken());
    const [authReady, setAuthReady] = useState(() => !getStoredToken());

    const applyUser = useCallback((data) => {
        setUser((prev) => ({
            ...prev,
            ...data,
            permissions: data.permissions || [],
            roles: data.roles || prev?.roles || [],
        }));
    }, []);

    useEffect(() => {
        persistAuth(user, token);
    }, [user, token]);

    // Always refresh user + permissions from API when a token exists
    useEffect(() => {
        if (!token) {
            setAuthReady(true);
            return;
        }

        let cancelled = false;
        setAuthReady(false);

        getCurrentUser(token)
            .then((data) => {
                if (cancelled) return;
                applyUser(data);
            })
            .catch(() => {
                if (cancelled) return;
                clearAuthStorage();
                setUser(null);
                setToken(null);
            })
            .finally(() => {
                if (!cancelled) setAuthReady(true);
            });

        return () => { cancelled = true; };
    }, [token, applyUser]);

    const permissions = user?.permissions || [];

    const hasPermission = (perm) => {
        if (!permissions.length) return false;
        if (permissions.includes('*')) return true;
        return permissions.includes(perm);
    };

    const hasAnyPermission = (...perms) => perms.some((p) => hasPermission(p));

    const login = (userData, authToken) => {
        setUser(userData);
        setToken(authToken);
        setAuthReady(false);
    };

    const logout = async () => {
        try {
            if (token) await logoutUser(token);
        } catch {
            // still clear client state
        }
        setUser(null);
        setToken(null);
        setAuthReady(true);
        clearAuthStorage();
        localStorage.removeItem('profileData');
    };

    useEffect(() => {
        setUnauthorizedHandler(() => {
            clearAuthStorage();
            setUser(null);
            setToken(null);
            setAuthReady(true);
        });
        setTokenUpdateHandler((newToken) => setToken(newToken));
        return () => {
            setUnauthorizedHandler(null);
            setTokenUpdateHandler(null);
        };
    }, []);

    // Proactively refresh JWT before the 20-minute expiry while session is active (2h).
    useEffect(() => {
        if (!token) return undefined;
        const intervalMs = 15 * 60 * 1000;
        const id = setInterval(async () => {
            try {
                const data = await refreshAuthToken(token);
                if (data?.token) setToken(data.token);
            } catch {
                // 401 interceptor handles logout on next API call
            }
        }, intervalMs);
        return () => clearInterval(id);
    }, [token]);

    return (
        <AuthContext.Provider value={{
            user, token, permissions, authReady,
            hasPermission, hasAnyPermission, login, logout,
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export default AuthContext;
