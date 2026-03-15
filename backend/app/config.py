import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model config
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
EMBEDDING_DIMENSIONS = 768

# Agent config
MAX_AGENT_ITERATIONS = 5

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "backend" / "chroma_db"

# Data files
PARTS_JSON = DATA_DIR / "parts.json"
PARTS_BY_PS_JSON = DATA_DIR / "parts_by_ps.json"
MODELS_INDEX_JSON = DATA_DIR / "models_index.json"
SYMPTOMS_INDEX_JSON = DATA_DIR / "symptoms_index.json"
REPAIRS_JSON = DATA_DIR / "repairs.json"
BLOGS_JSON = DATA_DIR / "blogs.json"

# Search config
DEFAULT_MAX_RESULTS = 5
KEYWORD_FALLBACK_MAX = 10
