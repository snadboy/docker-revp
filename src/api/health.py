"""Health check endpoints for Docker Reverse Proxy."""
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..config import settings
from ..logger import api_logger


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/version")
async def version_info():
    """Get version information."""
    return {
        "version": settings.app_version,
        "build_date": settings.build_date,
        "git_commit": settings.git_commit,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/detailed")
async def detailed_health_check(request: Request) -> Dict[str, Any]:
    """Detailed health check with component status."""
    api_logger.info("Detailed health check requested")
    
    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check Docker monitor status
    if request.app.state.docker_monitor:
        try:
            docker_status = request.app.state.docker_monitor.get_status()
            response["components"]["docker_monitor"] = {
                "status": "healthy",
                "total_containers": docker_status["total_containers"],
                "monitored_hosts": len(docker_status["monitored_hosts"]),
                "hosts": docker_status["hosts"]
            }
        except Exception as e:
            api_logger.error(f"Error getting Docker monitor status: {e}")
            response["components"]["docker_monitor"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            response["status"] = "degraded"
    
    # Check Caddy manager status
    if request.app.state.caddy_manager:
        try:
            caddy_status = request.app.state.caddy_manager.get_status()
            # Test actual connection
            connected = await request.app.state.caddy_manager.test_connection()
            caddy_status["connected"] = connected
            
            response["components"]["caddy_manager"] = {
                "status": "healthy" if connected else "unhealthy",
                **caddy_status
            }
            
            if not connected:
                response["status"] = "degraded"
                
        except Exception as e:
            api_logger.error(f"Error getting Caddy manager status: {e}")
            response["components"]["caddy_manager"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            response["status"] = "degraded"
    
    # Check SSH connections
    if request.app.state.ssh_manager:
        try:
            ssh_connections = request.app.state.ssh_manager.test_connections()
            healthy_count = sum(1 for conn in ssh_connections.values() if conn["connected"])
            total_count = len(ssh_connections)
            
            response["components"]["ssh_connections"] = {
                "status": "healthy" if healthy_count == total_count else "degraded",
                "healthy_count": healthy_count,
                "total_count": total_count,
                "connections": ssh_connections
            }
            
            if healthy_count < total_count:
                response["status"] = "degraded"
                
        except Exception as e:
            api_logger.error(f"Error testing SSH connections: {e}")
            response["components"]["ssh_connections"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            response["status"] = "degraded"
    
    return response


@router.get("/metrics")
async def metrics(request: Request):
    """Prometheus-compatible metrics endpoint."""
    metrics_lines = [
        "# HELP docker_monitor_up Docker monitor service status",
        "# TYPE docker_monitor_up gauge",
        "docker_monitor_up 1",
        "",
        "# HELP docker_monitor_containers_total Total number of monitored containers",
        "# TYPE docker_monitor_containers_total gauge",
    ]
    
    # Get container count
    container_count = 0
    if request.app.state.docker_monitor:
        try:
            status = request.app.state.docker_monitor.get_status()
            container_count = status["total_containers"]
        except:
            pass
    
    metrics_lines.append(f"docker_monitor_containers_total {container_count}")
    metrics_lines.append("")
    
    # Get host metrics
    if request.app.state.docker_monitor:
        try:
            status = request.app.state.docker_monitor.get_status()
            metrics_lines.extend([
                "# HELP docker_monitor_hosts_total Total number of monitored hosts",
                "# TYPE docker_monitor_hosts_total gauge",
                f"docker_monitor_hosts_total {len(status['monitored_hosts'])}",
                ""
            ])
            
            # Per-host container count
            metrics_lines.extend([
                "# HELP docker_monitor_host_containers Number of containers per host",
                "# TYPE docker_monitor_host_containers gauge"
            ])
            
            for host, host_info in status["hosts"].items():
                metrics_lines.append(
                    f'docker_monitor_host_containers{{host="{host}"}} {host_info["container_count"]}'
                )
            
            metrics_lines.append("")
            
        except:
            pass
    
    # Get route count
    if request.app.state.caddy_manager:
        try:
            caddy_status = request.app.state.caddy_manager.get_status()
            metrics_lines.extend([
                "# HELP docker_monitor_caddy_routes_total Total number of Caddy routes",
                "# TYPE docker_monitor_caddy_routes_total gauge",
                f"docker_monitor_caddy_routes_total {caddy_status['route_count']}",
                ""
            ])
        except:
            pass
    
    # Get SSH connection metrics
    if request.app.state.ssh_manager:
        try:
            ssh_connections = request.app.state.ssh_manager.test_connections()
            
            metrics_lines.extend([
                "# HELP docker_monitor_ssh_connection_status SSH connection status per host",
                "# TYPE docker_monitor_ssh_connection_status gauge"
            ])
            
            for host, conn in ssh_connections.items():
                status_value = 1 if conn["connected"] else 0
                metrics_lines.append(
                    f'docker_monitor_ssh_connection_status{{host="{host}",port="{conn["port"]}"}} {status_value}'
                )
            
        except:
            pass
    
    return JSONResponse(
        content="\n".join(metrics_lines),
        media_type="text/plain"
    )