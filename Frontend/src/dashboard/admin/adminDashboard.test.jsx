import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import AdminDashboard from './Dashboard';
import { renderDashboard } from '../../test/testUtils';
import { mockAdminUser } from '../../test/fixtures';

const mocks = vi.hoisted(() => ({
  emptyList: vi.fn().mockResolvedValue([]),
  emptyPaged: vi.fn().mockResolvedValue({ results: [], count: 0 }),
}));

vi.mock('../../services/dashboardService', () => ({
  getDashboardStats: vi.fn().mockResolvedValue({
    summary: { students: 12, faculty: 4, enrollments: 30 },
    semester: { semester_id: 1, semester_name: 'Fall 2025' },
  }),
}));

vi.mock('../../services/academicsService', () => ({
  listSemesters: vi.fn().mockResolvedValue([]),
  listDepartments: mocks.emptyList,
  listPrograms: mocks.emptyList,
  listCourses: mocks.emptyList,
  listOfferings: mocks.emptyList,
  listProgramCourses: mocks.emptyList,
  getAcademicPolicy: vi.fn().mockResolvedValue({ max_credit_hours: 21 }),
  updateAcademicPolicy: vi.fn(),
  createDepartment: vi.fn(),
  createProgram: vi.fn(),
  createCourse: vi.fn(),
}));

vi.mock('../../services/studentsService', () => ({
  listStudents: mocks.emptyPaged,
  getStudent: vi.fn().mockResolvedValue({}),
  adminUpdateStudentProfile: vi.fn(),
  adminDownloadStudentDocument: vi.fn(),
  listAcademicStanding: mocks.emptyList,
  listGraduationCandidates: mocks.emptyList,
}));

vi.mock('../../services/facultyService', () => ({
  listFaculty: mocks.emptyList,
  listDesignations: mocks.emptyList,
  listCourseAssignments: mocks.emptyList,
  listUnassignedCourses: mocks.emptyList,
  listUnassignedProgramCourses: mocks.emptyList,
  getFacultyWorkload: mocks.emptyList,
  assignCourse: vi.fn(),
  unassignCourse: vi.fn(),
}));

vi.mock('../../services/enrollmentsService', () => ({
  listEnrollments: mocks.emptyList,
  listRepeatRequests: mocks.emptyList,
  reviewRepeatRequest: vi.fn(),
  getAcademicProgress: vi.fn().mockResolvedValue({ batches: [] }),
}));

vi.mock('../../services/examinationsService', () => ({
  listExamTypes: mocks.emptyList,
  listGrades: mocks.emptyList,
  listExaminations: mocks.emptyList,
  getSemesterExamStatus: vi.fn().mockResolvedValue({}),
  listFinalGrades: mocks.emptyList,
  listResults: mocks.emptyList,
  listMarksEditRequests: mocks.emptyList,
  listOfferingEditRequests: mocks.emptyList,
  generateSemesterResults: vi.fn(),
  approveResult: vi.fn(),
  publishResult: vi.fn(),
}));

vi.mock('../../services/attendanceService', () => ({
  listAttendance: mocks.emptyList,
  getAttendanceSummary: mocks.emptyList,
  exportAttendanceSummary: vi.fn(),
}));

vi.mock('../../services/notificationsService', () => ({
  listNotifications: mocks.emptyList,
  listAnnouncements: mocks.emptyList,
  getAnnouncementTargetOptions: vi.fn().mockResolvedValue({}),
  createAnnouncement: vi.fn(),
}));

vi.mock('../../services/complaintsService', () => ({
  listComplaints: mocks.emptyList,
  listCategories: mocks.emptyList,
}));

vi.mock('../../services/admissionService', () => ({
  listAdminApplications: mocks.emptyList,
  getAdminSettings: vi.fn().mockResolvedValue({}),
  updateAdminSettings: vi.fn(),
  reviewApplication: vi.fn(),
}));

vi.mock('../../services/feesService', () => ({
  listFeeStructures: mocks.emptyList,
  createFeeStructure: vi.fn(),
  updateFeeStructure: vi.fn(),
  deleteFeeStructure: vi.fn(),
}));

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders admin home with stats', async () => {
    renderDashboard(<AdminDashboard />, {
      user: mockAdminUser,
      route: '/admin',
      basePath: '/admin',
    });
    await waitFor(() => {
      expect(screen.getByText(/Administrator/i)).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText('Active Students', { selector: '.stat-label' })).toBeInTheDocument();
    });
  });

  it('renders students listing page', async () => {
    renderDashboard(<AdminDashboard />, {
      user: mockAdminUser,
      route: '/admin/students',
      basePath: '/admin',
    });
    await waitFor(() => {
      expect(screen.getByText(/Students Management/i)).toBeInTheDocument();
    });
  });

  it('renders repeat requests page', async () => {
    renderDashboard(<AdminDashboard />, {
      user: mockAdminUser,
      route: '/admin/repeat-requests',
      basePath: '/admin',
    });
    await waitFor(() => {
      expect(screen.getByText(/Repeat Course Requests/i)).toBeInTheDocument();
    });
  });

  it('renders examinations page', async () => {
    renderDashboard(<AdminDashboard />, {
      user: mockAdminUser,
      route: '/admin/examinations',
      basePath: '/admin',
    });
    await waitFor(() => {
      expect(screen.getByText(/Results & Marks/i)).toBeInTheDocument();
    });
  });

  it('renders enrollments page', async () => {
    renderDashboard(<AdminDashboard />, {
      user: mockAdminUser,
      route: '/admin/enrollments',
      basePath: '/admin',
    });
    await waitFor(() => {
      expect(screen.getByText(/Enrollments Management/i)).toBeInTheDocument();
    });
  });
});
