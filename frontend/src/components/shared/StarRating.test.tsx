import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StarRating } from './StarRating';

describe('StarRating', () => {
  it('renders 5 star SVGs', () => {
    const { container } = render(<StarRating rating={4} />);
    const stars = container.querySelectorAll('svg');
    expect(stars).toHaveLength(5);
  });

  it('returns null for NaN rating', () => {
    const { container } = render(<StarRating rating="not-a-number" />);
    expect(container.firstChild).toBeNull();
  });

  it('displays numeric rating text', () => {
    render(<StarRating rating="3.7" />);
    expect(screen.getByText('3.7')).toBeInTheDocument();
  });

  it('applies filled class to stars at or below rounded rating', () => {
    const { container } = render(<StarRating rating={3} />);
    const stars = container.querySelectorAll('svg');
    // First 3 should be filled, last 2 empty
    expect(stars[0]).toHaveClass('fill-star-filled');
    expect(stars[3]).toHaveClass('fill-star-empty');
  });

  it('parses string ratings', () => {
    render(<StarRating rating="4.5" />);
    expect(screen.getByText('4.5')).toBeInTheDocument();
  });
});
