import { describe, it, expect } from 'vitest';
import { dashboardPathForRole, pageIdFromPath } from './paths';

describe('paths', () => {
  it('maps roles to dashboard bases', () => {
    expect(dashboardPathForRole('admin')).toBe('/admin');
    expect(dashboardPathForRole('applicant')).toBe('/applicant');
    expect(dashboardPathForRole('finance_officer')).toBe('/finance');
  });

  it('extracts page id from applicant ai route', () => {
    expect(pageIdFromPath('/applicant/ai-recommendation', '/applicant')).toBe('ai-recommendation');
  });

  it('extracts teacher courses page id', () => {
    expect(pageIdFromPath('/teacher/courses', '/teacher')).toBe('courses');
  });
});
