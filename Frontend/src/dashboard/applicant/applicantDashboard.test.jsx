import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import ApplicantDashboard from './Dashboard';
import { renderDashboard } from '../../test/testUtils';
import { mockApplicantUser, emptyApplicantProfile } from '../../test/fixtures';

vi.mock('../../services/admissionService', () => ({
  getApplicantProfile: vi.fn().mockResolvedValue({
    firstName: 'Ali',
    lastName: 'Khan',
    fatherName: 'Ahmed',
    username: 'applicant_user',
    cnic: '3520212345678',
    gender: 'male',
    cellPhone: '03001234567',
    residence: { perm_country: 'Pakistan', perm_state: 'Punjab', perm_city: 'Lahore', perm_address: '123 Street' },
    emergency: { name: 'Sara', relation: 'Sister', phone: '03009876543' },
    guardian: { name: 'Ahmed', cnic: '3520212345679', relation: 'Father' },
  }),
  getMyDocuments: vi.fn().mockResolvedValue([]),
  getAcademicRecords: vi.fn().mockResolvedValue([]),
  getMyApplications: vi.fn().mockResolvedValue([]),
  isApplicationLocked: vi.fn().mockReturnValue(false),
  hasRejectedApplication: vi.fn().mockReturnValue(false),
  getApplicationChallanPending: vi.fn().mockReturnValue(null),
}));

describe('ApplicantDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders applicant dashboard home', async () => {
    renderDashboard(<ApplicantDashboard />, {
      user: mockApplicantUser,
      route: '/applicant',
      basePath: '/applicant',
    });
    await waitFor(() => {
      expect(screen.getAllByText(/Campus 360/i).length).toBeGreaterThan(0);
    });
    await waitFor(() => {
      expect(screen.getAllByText(/Dashboard/i).length).toBeGreaterThan(0);
    });
  });

  it('renders profile completion page', async () => {
    renderDashboard(<ApplicantDashboard />, {
      user: mockApplicantUser,
      route: '/applicant/profile',
      basePath: '/applicant',
    });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Complete Profile/i })).toBeInTheDocument();
    });
  });

  it('shows rejected application view when application is rejected', async () => {
    const admission = await import('../../services/admissionService');
    admission.getMyApplications.mockResolvedValueOnce([{ status: 'rejected', rejection_message: 'Incomplete docs' }]);
    admission.hasRejectedApplication.mockReturnValueOnce(true);

    renderDashboard(<ApplicantDashboard />, {
      user: mockApplicantUser,
      route: '/applicant',
      basePath: '/applicant',
    });

    await waitFor(() => {
      expect(screen.getByText(/Application Rejected/i)).toBeInTheDocument();
    });
  });
});
