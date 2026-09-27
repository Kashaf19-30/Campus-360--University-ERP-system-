const TOKEN_KEY = 'token';
const USER_KEY = 'user';

/** Auth data in sessionStorage — cleared when the browser tab closes. */
export function getStoredToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
}

export function persistAuth(user, token) {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
    if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    else sessionStorage.removeItem(USER_KEY);
}

export function clearAuthStorage() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
}

/** Migrate legacy localStorage auth sessions once. */
export function migrateLegacyAuthStorage() {
    if (!sessionStorage.getItem(TOKEN_KEY)) {
        const legacyToken = localStorage.getItem('token');
        if (legacyToken) sessionStorage.setItem(TOKEN_KEY, legacyToken);
    }
    if (!sessionStorage.getItem(USER_KEY)) {
        const legacyUser = localStorage.getItem('user');
        if (legacyUser) sessionStorage.setItem(USER_KEY, legacyUser);
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}
