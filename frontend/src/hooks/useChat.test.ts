import { describe, it, expect } from 'vitest';
import { chatReducer, initialState } from './useChat';
import type { ChatState, Message, ContentBlock } from '@/lib/types';
import { makeMessage, makeTextBlock, makeProductCard } from '@/test/fixtures';

function assistantState(content: ContentBlock[] = [], extra: Partial<Message> = {}): ChatState {
  return {
    ...initialState,
    messages: [
      makeMessage({ role: 'assistant', content, isStreaming: true, ...extra }),
    ],
    isStreaming: true,
  };
}

describe('chatReducer', () => {
  describe('ADD_USER_MESSAGE', () => {
    it('appends user message and starts streaming', () => {
      const msg = makeMessage({ role: 'user' });
      const next = chatReducer(initialState, { type: 'ADD_USER_MESSAGE', message: msg });
      expect(next.messages).toHaveLength(1);
      expect(next.messages[0].role).toBe('user');
      expect(next.isStreaming).toBe(true);
    });

    it('clears previous error', () => {
      const state: ChatState = { ...initialState, error: 'old error' };
      const msg = makeMessage({ role: 'user' });
      const next = chatReducer(state, { type: 'ADD_USER_MESSAGE', message: msg });
      expect(next.error).toBeNull();
    });

    it('clears statusText', () => {
      const state: ChatState = { ...initialState, statusText: 'Searching...' };
      const msg = makeMessage({ role: 'user' });
      const next = chatReducer(state, { type: 'ADD_USER_MESSAGE', message: msg });
      expect(next.statusText).toBeNull();
    });
  });

  describe('ADD_ASSISTANT_MESSAGE', () => {
    it('appends assistant message', () => {
      const msg = makeMessage({ role: 'assistant', content: [] });
      const next = chatReducer(initialState, { type: 'ADD_ASSISTANT_MESSAGE', message: msg });
      expect(next.messages).toHaveLength(1);
      expect(next.messages[0].role).toBe('assistant');
    });
  });

  describe('APPEND_TEXT_DELTA', () => {
    it('appends to existing text block', () => {
      const state = assistantState([makeTextBlock('Hello')]);
      const next = chatReducer(state, { type: 'APPEND_TEXT_DELTA', text: ' world' });
      const last = next.messages[0].content[0];
      expect(last.type).toBe('text');
      if (last.type === 'text') expect(last.text).toBe('Hello world');
    });

    it('creates new text block when last block is not text', () => {
      const cardBlock: ContentBlock = { type: 'product_card', data: makeProductCard() };
      const state = assistantState([cardBlock]);
      const next = chatReducer(state, { type: 'APPEND_TEXT_DELTA', text: 'New text' });
      expect(next.messages[0].content).toHaveLength(2);
      const last = next.messages[0].content[1];
      expect(last.type).toBe('text');
      if (last.type === 'text') expect(last.text).toBe('New text');
    });

    it('creates new text block on empty content', () => {
      const state = assistantState([]);
      const next = chatReducer(state, { type: 'APPEND_TEXT_DELTA', text: 'First' });
      expect(next.messages[0].content).toHaveLength(1);
    });

    it('returns unchanged state if last message is not assistant', () => {
      const state: ChatState = {
        ...initialState,
        messages: [makeMessage({ role: 'user' })],
      };
      const next = chatReducer(state, { type: 'APPEND_TEXT_DELTA', text: 'test' });
      expect(next).toBe(state);
    });

    it('clears statusText', () => {
      const state: ChatState = { ...assistantState([makeTextBlock('Hi')]), statusText: 'Thinking...' };
      const next = chatReducer(state, { type: 'APPEND_TEXT_DELTA', text: '!' });
      expect(next.statusText).toBeNull();
    });
  });

  describe('ADD_CONTENT_BLOCK', () => {
    it('appends a content block to last assistant message', () => {
      const state = assistantState([]);
      const block: ContentBlock = { type: 'product_card', data: makeProductCard() };
      const next = chatReducer(state, { type: 'ADD_CONTENT_BLOCK', block });
      expect(next.messages[0].content).toHaveLength(1);
      expect(next.messages[0].content[0].type).toBe('product_card');
    });

    it('returns unchanged state if no assistant message', () => {
      const next = chatReducer(initialState, {
        type: 'ADD_CONTENT_BLOCK',
        block: makeTextBlock('test'),
      });
      expect(next).toBe(initialState);
    });
  });

  describe('SET_STATUS', () => {
    it('sets statusText', () => {
      const next = chatReducer(initialState, { type: 'SET_STATUS', text: 'Searching...' });
      expect(next.statusText).toBe('Searching...');
    });
  });

  describe('SET_SUGGESTIONS', () => {
    it('sets suggestions on last assistant message', () => {
      const state = assistantState([makeTextBlock('Hello')]);
      const next = chatReducer(state, { type: 'SET_SUGGESTIONS', options: ['Yes', 'No'] });
      expect(next.messages[0].suggestions).toEqual(['Yes', 'No']);
    });

    it('returns unchanged state when no assistant message', () => {
      const next = chatReducer(initialState, { type: 'SET_SUGGESTIONS', options: ['Yes'] });
      expect(next).toBe(initialState);
    });
  });

  describe('SET_ERROR', () => {
    it('sets error and stops streaming', () => {
      const state: ChatState = { ...initialState, isStreaming: true };
      const next = chatReducer(state, { type: 'SET_ERROR', error: 'Connection failed' });
      expect(next.error).toBe('Connection failed');
      expect(next.isStreaming).toBe(false);
      expect(next.statusText).toBeNull();
    });
  });

  describe('FINALIZE_STREAM', () => {
    it('sets isStreaming false on state and last assistant message', () => {
      const state = assistantState([makeTextBlock('Done')]);
      const next = chatReducer(state, { type: 'FINALIZE_STREAM' });
      expect(next.isStreaming).toBe(false);
      expect(next.messages[0].isStreaming).toBe(false);
    });

    it('handles empty messages array', () => {
      const state: ChatState = { ...initialState, isStreaming: true };
      const next = chatReducer(state, { type: 'FINALIZE_STREAM' });
      expect(next.isStreaming).toBe(false);
    });

    it('clears statusText', () => {
      const state: ChatState = { ...assistantState(), statusText: 'Working...' };
      const next = chatReducer(state, { type: 'FINALIZE_STREAM' });
      expect(next.statusText).toBeNull();
    });
  });

  describe('CLEAR_MESSAGES', () => {
    it('resets to initial state', () => {
      const state: ChatState = {
        messages: [makeMessage()],
        isStreaming: true,
        error: 'err',
        statusText: 'status',
      };
      const next = chatReducer(state, { type: 'CLEAR_MESSAGES' });
      expect(next).toEqual(initialState);
    });
  });

  describe('unknown action', () => {
    it('returns current state', () => {
      // @ts-expect-error testing unknown action
      const next = chatReducer(initialState, { type: 'UNKNOWN' });
      expect(next).toBe(initialState);
    });
  });
});
