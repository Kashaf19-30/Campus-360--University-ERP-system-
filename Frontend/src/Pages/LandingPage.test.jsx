import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import LandingPage from './LandingPage';
import { renderWithAuth } from '../test/testUtils';

describe('LandingPage', () => {
  it('renders marketing sections and navigation', () => {
    renderWithAuth(<LandingPage />, { user: null });
    expect(screen.getByRole('heading', { name: /Empowering Minds/i })).toBeInTheDocument();
    expect(screen.getAllByText(/Apply Online/i).length).toBeGreaterThan(0);
  });
});
