"""Pydantic request/response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message text content")


class ChatRequest(BaseModel):
    message: str = Field(description="The user's latest message")
    session_id: str = Field(description="Session UUID for conversation continuity")


class HealthResponse(BaseModel):
    status: str = "ok"
    parts_loaded: int = 0
    models_loaded: int = 0
    repairs_loaded: int = 0
    blogs_loaded: int = 0
