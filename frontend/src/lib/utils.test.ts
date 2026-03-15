import { describe, it, expect } from 'vitest';
import { cn, formatPrice, generateId } from './utils';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', false && 'hidden', 'end')).toBe('base end');
  });

  it('deduplicates tailwind conflicts', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('handles empty inputs', () => {
    expect(cn()).toBe('');
  });

  it('handles undefined and null', () => {
    expect(cn('a', undefined, null, 'b')).toBe('a b');
  });
});

describe('formatPrice', () => {
  it('formats a number', () => {
    expect(formatPrice(47.8)).toBe('$47.80');
  });

  it('formats a numeric string', () => {
    expect(formatPrice('47.82')).toBe('$47.82');
  });

  it('formats zero', () => {
    expect(formatPrice(0)).toBe('$0.00');
  });

  it('returns original string for NaN input', () => {
    expect(formatPrice('N/A')).toBe('N/A');
  });
});

describe('generateId', () => {
  it('returns a string', () => {
    expect(typeof generateId()).toBe('string');
  });
});
