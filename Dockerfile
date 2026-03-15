FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only what the backend needs
COPY data/ ./data/
COPY backend/ ./backend/

# Install backend dependencies with uv (much faster than pip)
WORKDIR /app/backend
RUN uv pip install --system --no-cache \
    'fastapi>=0.115.0' \
    'uvicorn[standard]>=0.34.0' \
    'sse-starlette>=2.2.0' \
    'google-genai>=1.0.0' \
    'chromadb>=0.6.0' \
    'pydantic>=2.10.0' \
    'python-dotenv>=1.2.2'

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
