"""
FastAPI Backend - Distributed Execution Control Plane
======================================================

Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import os

from app.config import settings
from app.database import init_db, close_db
from app.api import auth, subscriptions, wallets, protection, masters, signals, security, analytics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Execution Control Plane API",
    description="Backend API for distributed Forex trade replication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Parse CORS origins
cors_origins = [origin.strip() for origin in settings.allowed_origins.split(',')]
logger.info(f"CORS origins configured: {cors_origins}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Execution Control Plane API...")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize database
    await init_db()
    
    logger.info("✅ API ready to accept requests")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")
    await close_db()
    logger.info("Shutdown complete")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Execution Control Plane API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Mount API routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(security.router, prefix="/api/v1", tags=["Security"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
app.include_router(wallets.router, prefix="/api/v1", tags=["Wallets"])
app.include_router(protection.router, prefix="/api/v1", tags=["Protection"])
app.include_router(masters.router, prefix="/api/v1/masters", tags=["Masters"])
app.include_router(signals.router, prefix="/api/v1", tags=["Signals"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])


# Mount static files for EA downloads
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"✅ Static files mounted from {static_dir}")
else:
    logger.warning(f"⚠️ Static directory {static_dir} not found. EA downloads will be unavailable.")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
