import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from './LoginPage';
import { renderWithAuth } from '../test/testUtils';

vi.mock('../services/authService', () => ({
  loginUser: vi.fn(),
}));

import { loginUser } from '../services/authService';

describe('LoginPage', () => {
  it('renders login form after intro animation', async () => {
    renderWithAuth(<LoginPage />, { user: null });
    expect(await screen.findByRole('button', { name: /sign in/i }, { timeout: 2000 })).toBeInTheDocument();
  });

  it('shows validation errors for empty submit', async () => {
    renderWithAuth(<LoginPage />, { user: null });
    fireEvent.click(await screen.findByRole('button', { name: /sign in/i }, { timeout: 2000 }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });

  it('calls login API with valid credentials', async () => {
    loginUser.mockResolvedValue({
      token: 'jwt',
      user: { user_id: 1, user_type: 'admin', username: 'admin' },
    });

    renderWithAuth(<LoginPage />, { user: null });
    await screen.findByRole('button', { name: /sign in/i }, { timeout: 2000 });

    fireEvent.change(screen.getByPlaceholderText('yourname@campus.edu'), { target: { value: 'admin@test.edu' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'Secure1!' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(loginUser).toHaveBeenCalledWith('admin@test.edu', 'Secure1!');
    });
  });
});
