"""
FastAPI Main Application Entry Point.
Initializes database, mounts routers, CORS, and serves static frontend dashboard.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from app.config import settings
from app.database import init_db
from app.routes.video import router as video_router
from app.routes.translation import router as translation_router
from app.routes.jobs import router as jobs_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Convert spoken video language while preserving original background music, SFX, and video frames.",
    version="1.0.0"
)

# Enable CORS for local dev and embedded preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(video_router)
app.include_router(translation_router)
app.include_router(jobs_router)

# Mount frontend directory for static assets and dashboard
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_dir / "index.html"))

@app.on_event("startup")
async def on_startup():
    init_db()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "max_duration_default": settings.DEFAULT_MAX_DURATION,
        "storage": {
            "uploads": str(settings.UPLOAD_DIR),
            "final_videos": str(settings.FINAL_VIDEOS_DIR)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
