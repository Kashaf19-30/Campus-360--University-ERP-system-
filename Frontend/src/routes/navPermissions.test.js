import { describe, it, expect } from 'vitest';
import { filterNavItems, canSeeNavItem, canAccessRoute } from './navPermissions';

const hasAll = () => true;
const hasNone = () => false;
const hasStudentsOnly = (p) => p === 'students.view_student';

describe('navPermissions', () => {
  const navItems = [
    { id: 'home', label: 'Home', always: true },
    { id: 'students', label: 'Students', permission: 'students.view_student' },
    {
      id: 'academics-menu',
      label: 'Academics',
      permissions: ['academics.view_department'],
      children: [
        { id: 'academics', label: 'Programs', permission: 'academics.view_program' },
        { id: 'policy', label: 'Policy', permission: 'academics.view_program' },
      ],
    },
  ];

  it('shows always-visible items', () => {
    expect(canSeeNavItem({ always: true }, hasNone)).toBe(true);
  });

  it('filters items by permission', () => {
    const filtered = filterNavItems(navItems, hasStudentsOnly);
    expect(filtered.map(i => i.id)).toEqual(['home', 'students']);
  });

  it('keeps parent menu when any child is visible', () => {
    const hasProgram = (p) => p === 'academics.view_program';
    const filtered = filterNavItems(navItems, hasProgram);
    expect(filtered.some(i => i.id === 'academics-menu')).toBe(true);
  });

  it('allows route when any listed permission matches', () => {
    expect(canAccessRoute({ permissions: ['a', 'b'] }, (p) => p === 'b')).toBe(true);
    expect(canAccessRoute({ permission: 'x' }, hasNone)).toBe(false);
    expect(canAccessRoute({ always: true }, hasNone)).toBe(true);
  });
});
