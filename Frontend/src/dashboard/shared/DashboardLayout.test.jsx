import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DashboardLayout from './DashboardLayout';
import { renderWithAuth } from '../../test/testUtils';
import { mockAdminUser } from '../../test/fixtures';

describe('DashboardLayout', () => {
  it('renders role label and navigation items', () => {
    const onNavigate = vi.fn();
    renderWithAuth(
      <DashboardLayout
        roleLabel="Administrator"
        navItems={[
          { id: 'home', label: 'Dashboard', always: true },
          { id: 'students', label: 'Students', always: true },
        ]}
        currentPage="home"
        onNavigate={onNavigate}
        onLogout={vi.fn()}
      >
        <div>Main Content</div>
      </DashboardLayout>,
      { user: mockAdminUser },
    );

    expect(screen.getByText('Administrator')).toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('calls onNavigate when nav item is clicked', () => {
    const onNavigate = vi.fn();
    renderWithAuth(
      <DashboardLayout
        roleLabel="Administrator"
        navItems={[{ id: 'students', label: 'Students', always: true }]}
        currentPage="home"
        onNavigate={onNavigate}
        onLogout={vi.fn()}
      >
        <div>Content</div>
      </DashboardLayout>,
      { user: mockAdminUser },
    );

    fireEvent.click(screen.getByText('Students'));
    expect(onNavigate).toHaveBeenCalledWith('students');
  });
});
