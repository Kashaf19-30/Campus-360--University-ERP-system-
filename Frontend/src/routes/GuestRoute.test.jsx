import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GuestRoute from './GuestRoute';
import AuthContext from '../context/AuthContext';
import { createAuthValue } from '../test/testUtils';

function renderGuest(authValue, initialPath = '/login') {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/login"
            element={
              <GuestRoute>
                <div>Login Form</div>
              </GuestRoute>
            }
          />
          <Route path="/admin" element={<div>Admin Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('GuestRoute', () => {
  it('shows login page for guests', () => {
    renderGuest(createAuthValue({ user: null }));
    expect(screen.getByText('Login Form')).toBeInTheDocument();
  });

  it('redirects authenticated users to dashboard', () => {
    renderGuest(createAuthValue({
      user: { user_type: 'admin', username: 'admin' },
    }));
    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
  });
});
