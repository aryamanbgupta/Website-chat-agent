"""In-memory session store — session_id → conversation history."""


class SessionStore:
    """Simple in-memory session manager.

    Stores conversation history per session_id.
    No persistence needed — Gemini 2.5 Flash has 1M token context window.
    """

    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}

    def get_messages(self, session_id: str) -> list[dict]:
        """Get full conversation history for a session."""
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session history."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})

    def clear_session(self, session_id: str) -> None:
        """Clear a session's history."""
        self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        return len(self._sessions)


# Global singleton
store = SessionStore()
