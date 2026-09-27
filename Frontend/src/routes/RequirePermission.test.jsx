import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RequirePermission from './RequirePermission';
import AuthContext from '../context/AuthContext';
import { createAuthValue } from '../test/testUtils';

function renderGate({ permissions, required = 'students.view_student' }) {
  const authValue = createAuthValue({ permissions });
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={['/students']}>
        <Routes>
          <Route
            path="/students"
            element={
              <RequirePermission permission={required}>
                <div>Students Page</div>
              </RequirePermission>
            }
          />
          <Route path="/" element={<div>Dashboard Home</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('RequirePermission', () => {
  it('renders page when permission is granted', () => {
    renderGate({ permissions: ['students.view_student'] });
    expect(screen.getByText('Students Page')).toBeInTheDocument();
  });

  it('redirects when permission is missing', () => {
    renderGate({ permissions: [] });
    expect(screen.getByText('Dashboard Home')).toBeInTheDocument();
  });
});
