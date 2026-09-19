"""
Bob Fab Copilot — FastAPI Backend Entrypoint
Person D: REST API Service connecting real database to cleanroom frontend.
"""

import os
import sys
from pathlib import Path

# Add project root and backend dir to sys.path to enable importing copilot, analytics, and app packages
_backend_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[2])
for _p in (_backend_root, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import lots, defects, rootcause, predict_risk, validate, chat, recommend, patterns

app = FastAPI(
    title="Bob Fab Copilot API",
    description="Semiconductor yield analysis, root cause causality engine, and conversational cleanroom copilot.",
    version="1.0.0",
)

# Enable CORS for frontend Vite client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(lots.router)
app.include_router(defects.router)
app.include_router(rootcause.router)
app.include_router(predict_risk.router)
app.include_router(validate.router)
app.include_router(chat.router)
app.include_router(recommend.router)
app.include_router(patterns.router)


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "online",
        "service": "Bob Fab Copilot API",
        "version": "1.0.0",
        "database": "bob_fab.db connected",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8005"))
    print(f"\n>>> Starting Bob Fab Copilot API on http://localhost:{port} <<<\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

