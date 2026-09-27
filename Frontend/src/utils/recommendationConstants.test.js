import { describe, it, expect } from 'vitest';
import {
  BACKGROUND_CHOICES,
  SUBJECT_MAP,
  INTERESTS_LIST,
  GOALS_LIST,
  WIZARD_STEPS,
} from './recommendationConstants';

describe('recommendationConstants', () => {
  it('has backgrounds with subject maps', () => {
    BACKGROUND_CHOICES.forEach((bg) => {
      expect(SUBJECT_MAP[bg]?.length).toBeGreaterThan(0);
    });
  });

  it('wizard has five steps ending with Results', () => {
    expect(WIZARD_STEPS).toHaveLength(5);
    expect(WIZARD_STEPS[4].label).toBe('Results');
  });

  it('interests and goals are non-empty lists', () => {
    expect(INTERESTS_LIST.length).toBeGreaterThan(5);
    expect(GOALS_LIST.length).toBeGreaterThan(3);
  });
});
