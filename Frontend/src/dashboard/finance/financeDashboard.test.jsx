import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import FinanceDashboard from './Dashboard';
import { renderDashboard } from '../../test/testUtils';
import { mockFinanceUser, financePermissions } from '../../test/fixtures';

vi.mock('../../services/financeService', () => ({
  getFinanceDashboard: vi.fn().mockResolvedValue({
    new_admissions: [],
    enrolled_students: [],
    summary: { pending_admissions: 0, enrolled_total: 0, fees_paid: 0, fees_unpaid: 0 },
  }),
  listChallans: vi.fn().mockResolvedValue([]),
  markAdmissionPaid: vi.fn(),
  markChallanPaid: vi.fn(),
}));

vi.mock('../../services/academicsService', () => ({
  listDepartments: vi.fn().mockResolvedValue([]),
  listPrograms: vi.fn().mockResolvedValue([]),
  listSemesters: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../services/feesService', () => ({
  listFeeStructures: vi.fn().mockResolvedValue([]),
  createFeeStructure: vi.fn(),
  updateFeeStructure: vi.fn(),
  deleteFeeStructure: vi.fn(),
}));

describe('FinanceDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redirects to admission fees tab by default', async () => {
    renderDashboard(<FinanceDashboard />, {
      user: mockFinanceUser,
      permissions: financePermissions,
      route: '/finance',
      basePath: '/finance',
    });
    await waitFor(() => {
      expect(screen.getByText(/Finance Officer Dashboard/i)).toBeInTheDocument();
    });
  });

  it('renders semester fees page', async () => {
    renderDashboard(<FinanceDashboard />, {
      user: mockFinanceUser,
      permissions: financePermissions,
      route: '/finance/enrolled',
      basePath: '/finance',
    });
    await waitFor(() => {
      expect(screen.getByText(/Enrolled Students/i)).toBeInTheDocument();
    });
  });

  it('renders challan register page', async () => {
    renderDashboard(<FinanceDashboard />, {
      user: mockFinanceUser,
      permissions: financePermissions,
      route: '/finance/challans',
      basePath: '/finance',
    });
    await waitFor(() => {
      expect(screen.getAllByText(/Challan Register/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/No challans found/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});
