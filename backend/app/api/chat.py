"""POST /api/chat SSE endpoint."""

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agent.loop import run_agent
from app.api.models import ChatRequest
from app.session.memory import store

router = APIRouter()


@router.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle chat requests. Returns an SSE stream.

    The frontend sends the latest user message + session_id.
    The backend manages full conversation history including tool calls.
    """
    session_id = request.session_id
    user_message = request.message.strip()

    if not user_message:
        return EventSourceResponse(_error_stream("Please enter a message."))

    # Add user message to session history
    store.add_message(session_id, "user", user_message)

    # Get full conversation history
    messages = store.get_messages(session_id)

    async def event_generator():
        assistant_text = ""
        async for event in run_agent(messages, session_id):
            event_type = event.get("event", "text_delta")
            data = event.get("data", "")

            # Collect assistant text for session history
            if event_type == "text_delta":
                assistant_text += data

            yield {
                "event": event_type,
                "data": data if isinstance(data, str) else json.dumps(data),
            }

        # Save assistant response to session history
        if assistant_text:
            store.add_message(session_id, "assistant", assistant_text)

    return EventSourceResponse(event_generator())


async def _error_stream(message: str):
    yield {"event": "error", "data": message}
    yield {"event": "done", "data": ""}
