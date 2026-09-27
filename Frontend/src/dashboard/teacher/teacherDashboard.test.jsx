import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import TeacherDashboard from './Dashboard';
import { renderDashboard } from '../../test/testUtils';
import { mockTeacherUser, teacherPermissions, completeTeacherProfile } from '../../test/fixtures';

vi.mock('../../services/facultyService', () => ({
  getMyFacultyProfile: vi.fn().mockResolvedValue({
    profile_completed: true,
    employee_code: 'FAC-001',
    username: 'teacher_user',
    email: 'teacher@test.edu',
  }),
  updateMyFacultyProfile: vi.fn(),
}));

vi.mock('../../services/offeringsService', () => ({
  getMyOfferings: vi.fn().mockResolvedValue([]),
  getMyOfferingsForMarks: vi.fn().mockResolvedValue([]),
  getOfferingStudents: vi.fn().mockResolvedValue([]),
  submitFinalMarks: vi.fn(),
}));

vi.mock('../../services/examinationsService', () => ({
  listExaminations: vi.fn().mockResolvedValue([]),
  enterMarks: vi.fn(),
  listMarks: vi.fn().mockResolvedValue([]),
  requestMarksEdit: vi.fn(),
  getMarksLockStatus: vi.fn().mockResolvedValue({}),
  createContinuousAssessment: vi.fn(),
  requestOfferingMarksEdit: vi.fn(),
  updateExamination: vi.fn(),
}));

vi.mock('../../services/attendanceService', () => ({
  listAttendance: vi.fn().mockResolvedValue([]),
  markAttendance: vi.fn(),
  nextLectureNumber: vi.fn().mockResolvedValue({ next: 1 }),
  teacherLeaves: vi.fn().mockResolvedValue([]),
  reviewLeave: vi.fn(),
}));

vi.mock('../../services/notificationsService', () => ({
  listNotifications: vi.fn().mockResolvedValue([]),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  listAnnouncements: vi.fn().mockResolvedValue([]),
  createAnnouncement: vi.fn(),
  getAnnouncementTargetOptions: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../services/academicsService', () => ({
  listDepartments: vi.fn().mockResolvedValue([]),
  listPrograms: vi.fn().mockResolvedValue([]),
}));

describe('TeacherDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders teacher home', async () => {
    renderDashboard(<TeacherDashboard />, {
      user: mockTeacherUser,
      permissions: teacherPermissions,
      route: '/teacher',
      basePath: '/teacher',
    });
    await waitFor(() => {
      expect(screen.getByText(/Welcome Back/i)).toBeInTheDocument();
    });
  });

  it('renders my courses page', async () => {
    renderDashboard(<TeacherDashboard />, {
      user: mockTeacherUser,
      permissions: teacherPermissions,
      route: '/teacher/courses',
      basePath: '/teacher',
    });
    await waitFor(() => {
      expect(screen.getByText(/My Courses/i)).toBeInTheDocument();
    });
  });

  it('renders examinations page', async () => {
    renderDashboard(<TeacherDashboard />, {
      user: mockTeacherUser,
      permissions: teacherPermissions,
      route: '/teacher/examinations',
      basePath: '/teacher',
    });
    await waitFor(() => {
      expect(screen.getByText(/Examinations & Marks/i)).toBeInTheDocument();
    });
  });

  it('shows onboarding when profile is incomplete', async () => {
    const { getMyFacultyProfile } = await import('../../services/facultyService');
    getMyFacultyProfile.mockResolvedValueOnce({ profile_completed: false });

    renderDashboard(<TeacherDashboard />, {
      user: mockTeacherUser,
      permissions: teacherPermissions,
      route: '/teacher',
      basePath: '/teacher',
    });

    await waitFor(() => {
      expect(screen.getByText(/Complete Your Faculty Profile/i)).toBeInTheDocument();
    });
  });
});
