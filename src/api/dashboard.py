"""Dashboard endpoints for Docker Reverse Proxy."""
from typing import Dict, Any, List
from datetime import datetime, timezone
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..config import settings
from ..logger import api_logger


router = APIRouter(tags=["dashboard"])

# Get the absolute path to the static directory
STATIC_DIR = Path(__file__).parent.parent / "static"
templates = Jinja2Templates(directory=str(STATIC_DIR))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard page."""
    api_logger.info("Dashboard page requested")
    
    # Pass version info to template
    context = {
        "request": request,
        "version": settings.app_version,
        "build_date": settings.build_date,
        "git_commit": settings.git_commit[:8] if settings.git_commit else "unknown"
    }
    
    return templates.TemplateResponse("index.html", context)


@router.get("/api/changelog")
async def get_changelog() -> List[Dict[str, Any]]:
    """Get changelog entries for the last 5 versions."""
    api_logger.info("Changelog requested")
    
    try:
        # Read CHANGELOG.md
        changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
        if not changelog_path.exists():
            return []
        
        content = changelog_path.read_text()
        
        # Parse changelog entries
        entries = []
        
        # Split by version headers (both # and ##)
        sections = re.split(r"^(##?\s+.*?)$", content, flags=re.MULTILINE)
        
        for i in range(1, len(sections), 2):  # Headers are at odd indices
            if i + 1 >= len(sections):
                break
                
            header = sections[i].strip()
            body = sections[i + 1] if i + 1 < len(sections) else ""
            
            # Extract version and date from header
            # Formats: "## [1.1.1](...) (2025-07-13)" or "# 1.0.0 (2025-07-13)"
            version_match = re.search(r"\[?(\d+\.\d+\.\d+)\]?", header)
            date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", header)
            
            if not version_match:
                continue
                
            version = version_match.group(1)
            date = date_match.group(1) if date_match else "Unknown"
            
            # Extract changes
            changes = {
                "features": [],
                "fixes": [],
                "breaking": [],
                "other": []
            }
            
            lines = body.split('\n')
            current_type = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("### Features"):
                    current_type = "features"
                elif line.startswith("### Bug Fixes"):
                    current_type = "fixes"
                elif line.startswith("### BREAKING CHANGES"):
                    current_type = "breaking"
                elif line.startswith("### "):
                    current_type = "other"
                elif line.startswith("* ") and current_type:
                    # Extract change description and remove commit hash links
                    change = re.sub(r"\s*\([a-f0-9]+\)$", "", line[2:])
                    change = re.sub(r"\s*\(\[[a-f0-9]+\].*?\)$", "", change)
                    changes[current_type].append(change)
            
            entries.append({
                "version": version,
                "date": date,
                "changes": changes,
                "is_current": version == settings.app_version
            })
        
        return entries[:5]  # Return only last 5 versions
        
    except Exception as e:
        api_logger.error(f"Error reading changelog: {e}")
        return []


@router.get("/api/dashboard/summary")
async def dashboard_summary(request: Request) -> Dict[str, Any]:
    """Get summary data for dashboard."""
    api_logger.info("Dashboard summary requested")
    
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": {
            "current": settings.app_version,
            "build_date": settings.build_date,
            "git_commit": settings.git_commit
        },
        "containers": {
            "total": 0,
            "with_revp": 0,
            "without_revp": 0
        },
        "health": {
            "status": "healthy",
            "components": {}
        },
        "hosts": []
    }
    
    # Get container statistics
    if request.app.state.docker_monitor:
        try:
            # Get container counts
            all_containers = []
            for alias, hostname, port in request.app.state.docker_monitor.hosts_config:
                host_containers = request.app.state.docker_monitor.list_containers_sync(hostname)
                
                host_summary = {
                    "hostname": hostname,
                    "port": port,
                    "container_count": len(host_containers),
                    "revp_count": 0
                }
                
                for container in host_containers:
                    labels_str = container.get("Labels", "")
                    if labels_str:
                        labels = {}
                        for label in labels_str.split(','):
                            if '=' in label:
                                key, value = label.split('=', 1)
                                labels[key] = value
                        
                        if any(k.startswith("snadboy.revp.") for k in labels.keys()):
                            host_summary["revp_count"] += 1
                    
                    all_containers.append(container)
                
                summary["hosts"].append(host_summary)
            
            # Calculate totals
            summary["containers"]["total"] = len(all_containers)
            summary["containers"]["with_revp"] = sum(h["revp_count"] for h in summary["hosts"])
            summary["containers"]["without_revp"] = summary["containers"]["total"] - summary["containers"]["with_revp"]
            
        except Exception as e:
            api_logger.error(f"Error getting container statistics: {e}")
    
    # Get health status
    try:
        # Check Docker monitor
        if request.app.state.docker_monitor:
            summary["health"]["components"]["docker_monitor"] = {"status": "healthy"}
        else:
            summary["health"]["components"]["docker_monitor"] = {"status": "unhealthy"}
            summary["health"]["status"] = "degraded"
        
        # Check Caddy manager
        if request.app.state.caddy_manager:
            connected = await request.app.state.caddy_manager.test_connection()
            summary["health"]["components"]["caddy_manager"] = {
                "status": "healthy" if connected else "unhealthy"
            }
            if not connected:
                summary["health"]["status"] = "degraded"
        
        # Check SSH connections
        if request.app.state.ssh_manager:
            ssh_connections = request.app.state.ssh_manager.test_connections()
            healthy_count = sum(1 for conn in ssh_connections.values() if conn["connected"])
            total_count = len(ssh_connections)
            
            summary["health"]["components"]["ssh_connections"] = {
                "status": "healthy" if healthy_count == total_count else "degraded",
                "healthy_count": healthy_count,
                "total_count": total_count
            }
            
            if healthy_count < total_count:
                summary["health"]["status"] = "degraded"
                
    except Exception as e:
        api_logger.error(f"Error checking health status: {e}")
        summary["health"]["status"] = "unknown"
    
    return summary