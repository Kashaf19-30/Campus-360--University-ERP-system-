import { describe, it, expect, beforeEach } from 'vitest';
import { saveFormDraft, loadFormDraft, clearFormDraft } from './formDraft';

describe('formDraft', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('saves and loads draft by user and form name', () => {
    saveFormDraft(42, 'profile', { firstName: 'Ali' });
    expect(loadFormDraft(42, 'profile')).toEqual({ firstName: 'Ali' });
  });

  it('returns null when no draft exists', () => {
    expect(loadFormDraft(1, 'profile')).toBeNull();
  });

  it('clears draft from storage', () => {
    saveFormDraft(1, 'profile', { x: 1 });
    clearFormDraft(1, 'profile');
    expect(loadFormDraft(1, 'profile')).toBeNull();
  });
});
