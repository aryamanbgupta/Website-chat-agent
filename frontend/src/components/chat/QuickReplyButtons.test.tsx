import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuickReplyButtons } from './QuickReplyButtons';

describe('QuickReplyButtons', () => {
  it('renders all option buttons', () => {
    render(<QuickReplyButtons options={['Yes', 'No', 'Maybe']} onSelect={() => {}} />);
    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
    expect(screen.getByText('Maybe')).toBeInTheDocument();
  });

  it('calls onSelect with the clicked option', async () => {
    const onSelect = vi.fn();
    render(<QuickReplyButtons options={['Yes', 'No']} onSelect={onSelect} />);
    await userEvent.click(screen.getByText('Yes'));
    expect(onSelect).toHaveBeenCalledWith('Yes');
  });

  it('disables buttons when disabled prop is true', () => {
    render(<QuickReplyButtons options={['Yes']} onSelect={() => {}} disabled />);
    expect(screen.getByText('Yes')).toBeDisabled();
  });

  it('returns null for empty options', () => {
    const { container } = render(<QuickReplyButtons options={[]} onSelect={() => {}} />);
    expect(container.firstChild).toBeNull();
  });
});
