import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StockBadge } from './StockBadge';

describe('StockBadge', () => {
  it('shows "In Stock" when inStock is true', () => {
    render(<StockBadge inStock={true} />);
    expect(screen.getByText('In Stock')).toBeInTheDocument();
  });

  it('shows "Out of Stock" when inStock is false', () => {
    render(<StockBadge inStock={false} />);
    expect(screen.getByText('Out of Stock')).toBeInTheDocument();
  });

  it('uses success color class when in stock', () => {
    const { container } = render(<StockBadge inStock={true} />);
    expect(container.firstChild).toHaveClass('text-success-green');
  });

  it('uses error color class when out of stock', () => {
    const { container } = render(<StockBadge inStock={false} />);
    expect(container.firstChild).toHaveClass('text-error-red');
  });
});
