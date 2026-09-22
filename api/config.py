"""
MentorOS API configuration (Phase 9).
Central constants for paths, CORS, upload limits, and evaluation thresholds.
"""

from pathlib import Path

# Project root (parent of api/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Directories
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"
DATA_DIR = BASE_DIR / "data"

# SQLite databases
DB_PATH = DATA_DIR / "mentoros.db"            # sessions / messages / files (new)
MEMORY_DB_PATH = DATA_DIR / "learning_memory.db"  # Phase 6 learning memory (existing)

# Chroma collection (must match embeddings defaults)
CHROMA_COLLECTION = "mentoros_collection"

# Evaluation gate
EVAL_THRESHOLD = 0.60

# Uploads
import os
MAX_UPLOAD_MB = int(os.getenv("MENTOROS_MAX_UPLOAD_MB", "500"))
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}

# CORS — Vite dev server
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Retrieval
DEFAULT_TOP_K = 5

# API metadata
API_VERSION = "1.0"
APP_TITLE = "MentorOS API"
