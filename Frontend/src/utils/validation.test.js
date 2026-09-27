import { describe, it, expect } from 'vitest';
import {
  isValidEmail,
  isValidCNIC,
  isValidPhone,
  isValidName,
  isValidPassword,
  hasMatricAndInter,
  isPersonalDetailsComplete,
  isProfileComplete,
  getEmailError,
  getCNICError,
} from './validation';

describe('validation', () => {
  it('validates email format', () => {
    expect(isValidEmail('user@test.edu')).toBe(true);
    expect(isValidEmail('bad-email')).toBe(false);
    expect(getEmailError('')).toBe('Email is required');
  });

  it('validates CNIC as 13 digits', () => {
    expect(isValidCNIC('3520212345678')).toBe(true);
    expect(isValidCNIC('123')).toBe(false);
    expect(getCNICError('123')).toMatch(/13 digits/);
  });

  it('validates phone as 11 digits', () => {
    expect(isValidPhone('03001234567')).toBe(true);
    expect(isValidPhone('0300')).toBe(false);
  });

  it('validates names as letters only', () => {
    expect(isValidName('Ali Khan')).toBe(true);
    expect(isValidName('Ali123')).toBe(false);
  });

  it('validates password complexity', () => {
    expect(isValidPassword('Secure1!')).toBe(true);
    expect(isValidPassword('weak')).toBe(false);
  });

  it('requires matric and inter academic records', () => {
    expect(hasMatricAndInter([])).toBe(false);
    expect(hasMatricAndInter([{ qualification_level: 'matric' }])).toBe(false);
    expect(hasMatricAndInter([
      { qualification_level: 'matric' },
      { qualification_level: 'inter' },
    ])).toBe(true);
  });

  it('checks personal details completion', () => {
    const complete = {
      firstName: 'Ali',
      lastName: 'Khan',
      fatherName: 'Ahmed',
      cnic: '3520212345678',
      gender: 'male',
      cellPhone: '03001234567',
    };
    expect(isPersonalDetailsComplete(complete)).toBe(true);
    expect(isPersonalDetailsComplete({ ...complete, cnic: '123' })).toBe(false);
  });

  it('checks full profile completion', () => {
    const profile = {
      firstName: 'Ali',
      lastName: 'Khan',
      fatherName: 'Ahmed',
      cnic: '3520212345678',
      gender: 'male',
      cellPhone: '03001234567',
      residence: {
        perm_country: 'Pakistan',
        perm_state: 'Punjab',
        perm_city: 'Lahore',
        perm_address: '123 Main Street',
      },
      emergency: { name: 'Sara', relation: 'Sister', phone: '03009876543' },
      guardian: { name: 'Ahmed', cnic: '3520212345679', relation: 'Father' },
    };
    expect(isProfileComplete(profile)).toBe(true);
  });
});
