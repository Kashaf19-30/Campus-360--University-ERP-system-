import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import StudentDashboard from './Dashboard';
import { renderDashboard } from '../../test/testUtils';
import { mockStudentUser, studentPermissions } from '../../test/fixtures';

vi.mock('../../services/studentsService', () => ({
  getMyStudentProfile: vi.fn().mockResolvedValue({
    registration_number: '2024-CS-001',
    status: 'active',
    profile: {
      blood_group: 'A+',
      guardian_phone: '03001234567',
      guardian_occupation: 'Engineer',
      residential_address: '123 Main Street Lahore',
      profile_locked: false,
    },
  }),
  updateMyStudentProfile: vi.fn(),
  myDegreeProgress: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../services/enrollmentsService', () => ({
  myEnrollments: vi.fn().mockResolvedValue([]),
  getMyAcademicStatus: vi.fn().mockResolvedValue({}),
  getMyFailedCourses: vi.fn().mockResolvedValue({ failed_courses: [], pending_requests: [] }),
  submitRepeatRequests: vi.fn(),
}));

vi.mock('../../services/examinationsService', () => ({
  myFinalGrades: vi.fn().mockResolvedValue([]),
  myResults: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../services/attendanceService', () => ({
  myAttendanceSummary: vi.fn().mockResolvedValue([]),
  submitLeave: vi.fn(),
  myLeaves: vi.fn().mockResolvedValue([]),
  deleteLeave: vi.fn(),
}));

vi.mock('../../services/feesService', () => ({
  myChallans: vi.fn().mockResolvedValue([]),
  downloadMyChallan: vi.fn(),
}));

vi.mock('../../services/complaintsService', () => ({
  myComplaints: vi.fn().mockResolvedValue([]),
  submitComplaint: vi.fn(),
  listCategories: vi.fn().mockResolvedValue([]),
  deleteComplaint: vi.fn(),
  getComplaint: vi.fn(),
  submitFeedback: vi.fn(),
  getComplaintThread: vi.fn(),
}));

vi.mock('../../services/notificationsService', () => ({
  listNotifications: vi.fn().mockResolvedValue([]),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  listAnnouncements: vi.fn().mockResolvedValue([]),
}));

describe('StudentDashboard', () => {
  it('renders student home dashboard', async () => {
    renderDashboard(<StudentDashboard />, {
      user: mockStudentUser,
      permissions: studentPermissions,
      route: '/student',
      basePath: '/student',
    });
    await waitFor(() => {
      expect(screen.getByText(/Welcome Back/i)).toBeInTheDocument();
    });
  });

  it('renders enrollments page', async () => {
    renderDashboard(<StudentDashboard />, {
      user: mockStudentUser,
      permissions: studentPermissions,
      route: '/student/enrollments',
      basePath: '/student',
    });
    await waitFor(() => {
      expect(screen.getByText(/My Enrollments/i)).toBeInTheDocument();
    });
  });

  it('renders grades page', async () => {
    renderDashboard(<StudentDashboard />, {
      user: mockStudentUser,
      permissions: studentPermissions,
      route: '/student/grades',
      basePath: '/student',
    });
    await waitFor(() => {
      expect(screen.getByText(/My Grades/i)).toBeInTheDocument();
    });
  });

  it('shows profile completion form when profile is incomplete', async () => {
    const { getMyStudentProfile } = await import('../../services/studentsService');
    getMyStudentProfile.mockResolvedValue({
      registration_number: '2024-CS-001',
      status: 'active',
      profile: {
        blood_group: null,
        guardian_phone: null,
        guardian_occupation: null,
        residential_address: null,
      },
    });

    renderDashboard(<StudentDashboard />, {
      user: mockStudentUser,
      permissions: studentPermissions,
      route: '/student',
      basePath: '/student',
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Complete Your Student Profile/i })).toBeInTheDocument();
    });
  });
});
