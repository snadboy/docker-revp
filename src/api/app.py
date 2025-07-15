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

# Import FastAPI-MCP for Model Context Protocol support
try:
    from fastapi_mcp import FastApiMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    api_logger.warning("fastapi-mcp not available, MCP endpoint will not be mounted")


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
    
    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    app.include_router(dashboard_router)  # Dashboard should be first for "/" route
    app.include_router(health_router)
    app.include_router(containers_router)
    
    # Mount MCP server for AI agent integration
    if MCP_AVAILABLE:
        try:
            mcp = FastApiMCP(app)
            mcp.mount()  # Mounts at /mcp endpoint
            api_logger.info("MCP server mounted at /mcp - AI agents can now access this API")
        except Exception as e:
            api_logger.error(f"Failed to mount MCP server: {e}")
    
    @app.on_event("startup")
    async def startup_event():
        api_logger.info(f"API server starting on {settings.api_host}:{settings.api_port}")
        if MCP_AVAILABLE:
            api_logger.info("MCP endpoint available for AI agent integration")
    
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