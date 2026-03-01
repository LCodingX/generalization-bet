import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import jobs, callbacks, datasets, admin

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ============================================================
# App
# ============================================================

app = FastAPI(
    title="LLM Influence Orchestrator",
    description=(
        "Backend API for the fine-tuning influence dashboard. "
        "Orchestrates PEFT fine-tuning jobs on Modal and serves "
        "TracIn + DataInf influence scores to the frontend."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# CORS — Allow the Next.js frontend
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Local dev
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel previews
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Routes
# ============================================================

app.include_router(jobs.router)
app.include_router(callbacks.router)
app.include_router(datasets.router)
app.include_router(admin.router)


# ============================================================
# Root
# ============================================================


@app.get("/")
async def root():
    return {
        "service": "llm-influence-orchestrator",
        "version": "0.1.0",
        "docs": "/docs",
    }
