import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from './MessageBubble';
import {
  makeMessage,
  makeTextBlock,
  makeProductCardBlock,
  makeCompatibilityBlock,
  makeDiagnosisBlock,
} from '@/test/fixtures';

// Mock react-markdown to avoid ESM/remark issues in jsdom
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}));
vi.mock('remark-gfm', () => ({ default: () => {} }));

describe('MessageBubble', () => {
  it('renders user text as plain paragraph', () => {
    const msg = makeMessage({ role: 'user', content: [makeTextBlock('Hello there')] });
    render(<MessageBubble message={msg} />);
    expect(screen.getByText('Hello there')).toBeInTheDocument();
  });

  it('renders assistant text through markdown', () => {
    const msg = makeMessage({ role: 'assistant', content: [makeTextBlock('**Bold**')] });
    render(<MessageBubble message={msg} />);
    expect(screen.getByTestId('markdown')).toHaveTextContent('**Bold**');
  });

  it('renders text blocks before card blocks', () => {
    const msg = makeMessage({
      role: 'assistant',
      content: [
        makeProductCardBlock(),
        makeTextBlock('After card'),
      ],
    });
    const { container } = render(<MessageBubble message={msg} />);
    const allText = container.textContent || '';
    const textPos = allText.indexOf('After card');
    const cardPos = allText.indexOf('Refrigerator Water Inlet Valve');
    expect(textPos).toBeLessThan(cardPos);
  });

  it('renders product card blocks', () => {
    const msg = makeMessage({ role: 'assistant', content: [makeProductCardBlock()] });
    render(<MessageBubble message={msg} />);
    expect(screen.getByText('Refrigerator Water Inlet Valve')).toBeInTheDocument();
  });

  it('renders compatibility result blocks', () => {
    const msg = makeMessage({ role: 'assistant', content: [makeCompatibilityBlock()] });
    render(<MessageBubble message={msg} />);
    expect(screen.getByText('Compatible')).toBeInTheDocument();
  });

  it('renders diagnosis blocks', () => {
    const msg = makeMessage({ role: 'assistant', content: [makeDiagnosisBlock()] });
    render(<MessageBubble message={msg} />);
    expect(screen.getByText(/Diagnosis: Ice maker not working/)).toBeInTheDocument();
  });

  it('applies user styling', () => {
    const msg = makeMessage({ role: 'user', content: [makeTextBlock('Hi')] });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.querySelector('.justify-end')).toBeInTheDocument();
    expect(container.querySelector('.bg-primary-teal')).toBeInTheDocument();
  });

  it('applies assistant styling', () => {
    const msg = makeMessage({ role: 'assistant', content: [makeTextBlock('Hi')] });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.querySelector('.justify-start')).toBeInTheDocument();
    expect(container.querySelector('.bg-white')).toBeInTheDocument();
  });

  it('shows streaming indicator when streaming with empty content', () => {
    const msg = makeMessage({ role: 'assistant', content: [], isStreaming: true });
    const { container } = render(<MessageBubble message={msg} statusText="Thinking..." />);
    expect(container.querySelector('.bounce-dot-1')).toBeInTheDocument();
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('shows streaming indicator with statusText when streaming with content', () => {
    const msg = makeMessage({
      role: 'assistant',
      content: [makeTextBlock('partial')],
      isStreaming: true,
    });
    const { container } = render(<MessageBubble message={msg} statusText="Searching..." />);
    expect(container.querySelector('.bounce-dot-1')).toBeInTheDocument();
    expect(screen.getByText('Searching...')).toBeInTheDocument();
  });

  it('does not show streaming indicator when not streaming', () => {
    const msg = makeMessage({
      role: 'assistant',
      content: [makeTextBlock('Done')],
      isStreaming: false,
    });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.querySelector('.bounce-dot-1')).toBeNull();
  });
});
