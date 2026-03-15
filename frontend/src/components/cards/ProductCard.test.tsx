import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProductCard } from './ProductCard';
import { makeProductCard } from '@/test/fixtures';

describe('ProductCard', () => {
  it('renders product name', () => {
    render(<ProductCard data={makeProductCard()} />);
    expect(screen.getByText('Refrigerator Water Inlet Valve')).toBeInTheDocument();
  });

  it('renders formatted price', () => {
    render(<ProductCard data={makeProductCard()} />);
    expect(screen.getByText('$47.82')).toBeInTheDocument();
  });

  it('renders brand and ps_number', () => {
    render(<ProductCard data={makeProductCard()} />);
    expect(screen.getByText('Whirlpool | PS11752778')).toBeInTheDocument();
  });

  it('renders image when image_url is provided', () => {
    render(<ProductCard data={makeProductCard()} />);
    const img = screen.getByAltText('Refrigerator Water Inlet Valve');
    expect(img).toHaveAttribute('src', 'https://example.com/part.jpg');
  });

  it('does not render image when image_url is empty', () => {
    render(<ProductCard data={makeProductCard({ image_url: '' })} />);
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('renders star rating', () => {
    const { container } = render(<ProductCard data={makeProductCard()} />);
    expect(container.querySelectorAll('svg').length).toBeGreaterThanOrEqual(5);
  });

  it('renders review count', () => {
    render(<ProductCard data={makeProductCard()} />);
    expect(screen.getByText('(123 reviews)')).toBeInTheDocument();
  });

  it('renders stock badge', () => {
    render(<ProductCard data={makeProductCard()} />);
    expect(screen.getByText('In Stock')).toBeInTheDocument();
  });

  it('renders installation difficulty when provided', () => {
    render(<ProductCard data={makeProductCard({ installation_difficulty: 'Easy' })} />);
    expect(screen.getByText('Easy')).toBeInTheDocument();
  });

  it('renders symptoms (max 4)', () => {
    const symptoms = ['Leaking', 'No water', 'Noisy', 'Slow fill', 'Extra symptom'];
    render(<ProductCard data={makeProductCard({ symptoms_fixed: symptoms })} />);
    expect(screen.getByText('Fixes: Leaking')).toBeInTheDocument();
    expect(screen.getByText('Fixes: Slow fill')).toBeInTheDocument();
    expect(screen.queryByText('Fixes: Extra symptom')).toBeNull();
  });

  it('renders source link', () => {
    render(<ProductCard data={makeProductCard()} />);
    const link = screen.getByText('View on PartSelect');
    expect(link).toHaveAttribute('href', 'https://partselect.com/PS11752778');
    expect(link).toHaveAttribute('target', '_blank');
  });
});
