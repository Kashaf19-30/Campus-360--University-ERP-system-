import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRecommendationWizard } from './useRecommendationWizard';

vi.mock('../services/recommendationService', () => ({
  submitRecommendationProfile: vi.fn().mockResolvedValue({}),
  fetchRecommendations: vi.fn().mockResolvedValue([
    { program_name: 'BS Computer Science', match_score: 92 },
  ]),
}));

describe('useRecommendationWizard', () => {
  it('starts on step 1 and blocks advance without background', () => {
    const { result } = renderHook(() => useRecommendationWizard('token'));
    expect(result.current.currentStep).toBe(1);
    act(() => result.current.goToNextStep());
    expect(result.current.error).toMatch(/background/i);
    expect(result.current.currentStep).toBe(1);
  });

  it('advances to step 2 after selecting background', () => {
    const { result } = renderHook(() => useRecommendationWizard('token'));
    act(() => result.current.updateField('background', 'FSc Pre-Engineering'));
    act(() => result.current.goToNextStep());
    expect(result.current.currentStep).toBe(2);
    expect(result.current.error).toBe('');
  });

  it('clears wizard state', () => {
    const { result } = renderHook(() => useRecommendationWizard('token'));
    act(() => result.current.updateField('background', 'FSc Pre-Engineering'));
    act(() => result.current.clearAllData());
    expect(result.current.background).toBe('');
    expect(result.current.currentStep).toBe(1);
  });
});
