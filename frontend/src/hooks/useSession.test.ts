import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSession } from './useSession';

beforeEach(() => {
  localStorage.clear();
});

describe('useSession', () => {
  it('creates and stores a new session id when none exists', () => {
    const { result } = renderHook(() => useSession());
    expect(result.current.sessionId).toBeTruthy();
    expect(localStorage.setItem).toHaveBeenCalled();
  });

  it('reads existing session id from localStorage', () => {
    localStorage.setItem('partselect_session_id', 'existing-id');
    const { result } = renderHook(() => useSession());
    expect(result.current.sessionId).toBe('existing-id');
  });

  it('resetSession generates a new id', () => {
    const { result } = renderHook(() => useSession());
    const firstId = result.current.sessionId;

    act(() => {
      result.current.resetSession();
    });

    expect(result.current.sessionId).not.toBe(firstId);
    expect(result.current.sessionId).toBeTruthy();
  });
});
