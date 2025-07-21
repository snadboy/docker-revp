"""FastAPI application for health checks and monitoring."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import settings
from ..logger import api_logger
from .health import router as health_router
from .containers import router as containers_router
from .dashboard import router as dashboard_router
from .static_routes import router as static_routes_router


def create_app(docker_monitor=None, caddy_manager=None, ssh_manager=None, static_routes_manager=None):
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
    app.state.static_routes_manager = static_routes_manager
    
    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    app.include_router(dashboard_router)  # Dashboard should be first for "/" route
    app.include_router(health_router)
    app.include_router(containers_router)
    app.include_router(static_routes_router)
    
    @app.on_event("startup")
    async def startup_event():
        api_logger.info(f"API server starting on {settings.api_bind}")
    
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