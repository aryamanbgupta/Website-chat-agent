"""FastAPI app — CORS, lifespan, routes."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.models import HealthResponse
from app.data import loader


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all data into memory on startup."""
    print("Loading data...")
    loader.load_all()
    print("Ready!")
    yield
    print("Shutting down.")


app = FastAPI(
    title="PartSelect AI Agent",
    description="AI chat agent for refrigerator and dishwasher parts",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — safety net (primary flow goes through Next.js proxy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        parts_loaded=len(loader.parts_by_ps),
        models_loaded=len(loader.models_index),
        repairs_loaded=len(loader.repairs),
        blogs_loaded=len(loader.blogs),
    )
