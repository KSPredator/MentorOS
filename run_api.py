"""
MentorOS API launcher.

Run this script from the project root to start the FastAPI server:
  python run_api.py

Options (edit below or use env vars):
  HOST     — default "0.0.0.0"
  PORT     — default 8000
  RELOAD   — default True (auto-restart on code changes)
"""

import os
import sys
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402

HOST = os.getenv("MENTOROS_HOST", "0.0.0.0")
PORT = int(os.getenv("MENTOROS_PORT", "8000"))
RELOAD = os.getenv("MENTOROS_RELOAD", "true").lower() == "true"

if __name__ == "__main__":
    print(f"\n🎓 MentorOS API starting on http://{HOST}:{PORT}")
    print(f"   Swagger UI → http://localhost:{PORT}/docs")
    print(f"   ReDoc      → http://localhost:{PORT}/redoc\n")

    uvicorn.run(
        "api.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info",
    )
