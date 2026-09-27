import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { ALL_PERMISSIONS } from './fixtures';

export function createAuthValue({
  user = null,
  permissions = ALL_PERMISSIONS,
  token = user ? 'test-token' : null,
  authReady = true,
} = {}) {
  const effectivePermissions = user?.permissions ?? permissions;

  const hasPermission = (perm) => {
    if (!effectivePermissions.length) return false;
    if (effectivePermissions.includes('*')) return true;
    return effectivePermissions.includes(perm);
  };

  return {
    user,
    token,
    permissions: effectivePermissions,
    authReady,
    hasPermission,
    hasAnyPermission: (...perms) => perms.some((p) => hasPermission(p)),
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
  };
}

function AppProviders({ authValue, children }) {
  return (
    <ThemeProvider>
      <AuthContext.Provider value={authValue}>
        {children}
      </AuthContext.Provider>
    </ThemeProvider>
  );
}

export function renderWithAuth(ui, {
  user = null,
  permissions = ALL_PERMISSIONS,
  route = '/',
  routes = null,
} = {}) {
  const authValue = createAuthValue({ user, permissions });

  if (routes) {
    return render(
      <AppProviders authValue={authValue}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>{routes}</Routes>
        </MemoryRouter>
      </AppProviders>,
    );
  }

  return render(
    <AppProviders authValue={authValue}>
      <MemoryRouter initialEntries={[route]}>
        {ui}
      </MemoryRouter>
    </AppProviders>,
  );
}

export function renderWithRouter(ui, { route = '/' } = {}) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </ThemeProvider>,
  );
}

export function renderDashboard(dashboardElement, { user, permissions, route, basePath }) {
  const authValue = createAuthValue({ user, permissions });

  return render(
    <AppProviders authValue={authValue}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={`${basePath}/*`} element={dashboardElement} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  );
}
