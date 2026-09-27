import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React, { useState } from 'react';
import {
  formatDate,
  getStatusBadgeClass,
  PageHeader,
  TableSearchBar,
  LoadingSpinner,
} from './helpers';

describe('shared helpers', () => {
  it('formats dates for en-PK locale', () => {
    expect(formatDate('2025-01-15')).toMatch(/\d{2}\/\d{2}\/\d{4}/);
    expect(formatDate(null)).toBe('—');
  });

  it('maps status values to badge classes', () => {
    expect(getStatusBadgeClass('approved')).toContain('approved');
    expect(getStatusBadgeClass('pending')).toContain('under-review');
    expect(getStatusBadgeClass('rejected')).toContain('rejected');
  });

  it('renders page header with title', () => {
    render(<PageHeader breadcrumb="ADMIN > STUDENTS" title="Students" />);
    expect(screen.getByText('Students')).toBeInTheDocument();
    expect(screen.getByText(/ADMIN/)).toBeInTheDocument();
  });

  it('renders loading spinner message', () => {
    render(<LoadingSpinner message="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('filters table rows via search bar', () => {
    function TableDemo() {
      const items = [
        { id: 1, name: 'Ali Khan' },
        { id: 2, name: 'Sara Ahmed' },
      ];
      const [search, setSearch] = useState('');
      const filtered = items.filter(i => i.name.toLowerCase().includes(search.toLowerCase()));
      return (
        <>
          <TableSearchBar search={search} onSearchChange={setSearch} placeholder="Search name" />
          <ul>{filtered.map(i => <li key={i.id}>{i.name}</li>)}</ul>
        </>
      );
    }
    render(<TableDemo />);
    fireEvent.change(screen.getByPlaceholderText('Search name'), { target: { value: 'Sara' } });
    expect(screen.getByText('Sara Ahmed')).toBeInTheDocument();
    expect(screen.queryByText('Ali Khan')).not.toBeInTheDocument();
  });
});
