import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import AuthContext from '../context/AuthContext';
import { createAuthValue } from '../test/testUtils';

function renderProtected({ authValue, path = '/admin', allowedRoles = ['admin'] }) {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={allowedRoles}>
                <div>Admin Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/student" element={<div>Student Home</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to login', () => {
    renderProtected({ authValue: createAuthValue({ user: null, token: null }) });
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('shows loading while session is refreshing', () => {
    renderProtected({
      authValue: createAuthValue({
        user: { user_type: 'admin' },
        authReady: false,
      }),
    });
    expect(screen.getByText(/loading your session/i)).toBeInTheDocument();
  });

  it('renders children for allowed role', () => {
    renderProtected({
      authValue: createAuthValue({
        user: { user_type: 'admin', username: 'admin' },
      }),
    });
    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('redirects wrong role to their dashboard', () => {
    renderProtected({
      authValue: createAuthValue({
        user: { user_type: 'student', username: 'stu' },
      }),
    });
    expect(screen.getByText('Student Home')).toBeInTheDocument();
  });
});
