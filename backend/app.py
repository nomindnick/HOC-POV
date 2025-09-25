from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from backend.config import settings
from backend.db.base import db
from backend.api import ingest

# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Local, offline-first web application for CPRA document classification"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.project_name,
        "version": "1.0.0",
        "status": "running"
    }


@app.get(f"{settings.api_v1_str}/health")
async def health_check():
    """Health check endpoint for monitoring application status"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "cpra-filter-backend",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print(f"🚀 {settings.project_name} starting up...")
    print(f"📁 Data directory: {settings.data_dir}")
    print(f"🔗 API available at: http://{settings.backend_host}:{settings.backend_port}")
    print(f"🎨 Frontend expected at: {settings.frontend_url}")

    # Initialize database
    print(f"🗄️ Initializing database...")
    db.init_db()
    print(f"✅ Database initialized successfully")

# Include routers
app.include_router(ingest.router)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    print(f"👋 {settings.project_name} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )