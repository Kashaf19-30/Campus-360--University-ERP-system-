import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import AiRecommendationPage from './Pages/AiRecommendationPage';
import { renderWithAuth } from '../../test/testUtils';
import { mockApplicantUser } from '../../test/fixtures';

vi.mock('../../services/recommendationService', () => ({
  submitRecommendationProfile: vi.fn().mockResolvedValue({}),
  fetchRecommendations: vi.fn().mockResolvedValue([]),
}));

describe('AiRecommendationPage', () => {
  it('renders wizard step 1 with background choices', () => {
    renderWithAuth(<AiRecommendationPage />, {
      user: mockApplicantUser,
      route: '/applicant/ai-recommendation',
    });
    expect(screen.getByText(/Find your perfect degree/i)).toBeInTheDocument();
    expect(screen.getByText(/What did you study in intermediate/i)).toBeInTheDocument();
  });

  it('shows error when continuing without background', () => {
    renderWithAuth(<AiRecommendationPage />, {
      user: mockApplicantUser,
      route: '/applicant/ai-recommendation',
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByText(/select your intermediate background/i)).toBeInTheDocument();
  });
});
