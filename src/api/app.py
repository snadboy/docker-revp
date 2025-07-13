"""FastAPI application for health checks and monitoring."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..config import settings
from ..logger import api_logger
from .health import router as health_router
from .containers import router as containers_router


def create_app(docker_monitor=None, caddy_manager=None, ssh_manager=None):
    """Create FastAPI application."""
    app = FastAPI(
        title="Docker Monitor API",
        description="Health checks and monitoring for Docker container monitor",
        version="1.0.0"
    )
    
    # Store references to managers
    app.state.docker_monitor = docker_monitor
    app.state.caddy_manager = caddy_manager
    app.state.ssh_manager = ssh_manager
    
    # Include routers
    app.include_router(health_router)
    app.include_router(containers_router)
    
    @app.on_event("startup")
    async def startup_event():
        api_logger.info(f"API server starting on {settings.api_host}:{settings.api_port}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        api_logger.info("API server shutting down")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        api_logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app