import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CompatibilityBadge } from './CompatibilityBadge';
import { makeCompatibilityResult } from '@/test/fixtures';

describe('CompatibilityBadge', () => {
  it('shows "Compatible" for verified compatible result', () => {
    render(<CompatibilityBadge data={makeCompatibilityResult()} />);
    expect(screen.getByText('Compatible')).toBeInTheDocument();
  });

  it('shows "Not Compatible" when compatible is false', () => {
    const data = makeCompatibilityResult({ compatible: false, confidence: 'verified' });
    render(<CompatibilityBadge data={data} />);
    expect(screen.getByText('Not Compatible')).toBeInTheDocument();
  });

  it('shows "Unable to Verify" for part_not_found', () => {
    const data = makeCompatibilityResult({ compatible: null, confidence: 'part_not_found' });
    render(<CompatibilityBadge data={data} />);
    expect(screen.getByText('Unable to Verify')).toBeInTheDocument();
  });

  it('shows "Unverified" for not_in_data with compatible null', () => {
    const data = makeCompatibilityResult({ compatible: null, confidence: 'not_in_data' });
    render(<CompatibilityBadge data={data} />);
    expect(screen.getByText('Unable to Verify')).toBeInTheDocument();
  });

  it('displays part and model numbers', () => {
    render(<CompatibilityBadge data={makeCompatibilityResult()} />);
    expect(screen.getByText(/Part: PS11752778/)).toBeInTheDocument();
    expect(screen.getByText(/Model: WDT780SAEM1/)).toBeInTheDocument();
  });

  it('displays message text', () => {
    render(<CompatibilityBadge data={makeCompatibilityResult()} />);
    expect(screen.getByText('This part is compatible with your model.')).toBeInTheDocument();
  });

  it('renders source link when source_url provided', () => {
    const data = makeCompatibilityResult({ source_url: 'https://example.com' });
    render(<CompatibilityBadge data={data} />);
    const link = screen.getByText('View Details');
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
  });
});
