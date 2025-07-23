"""Dashboard endpoints for Docker Reverse Proxy."""
from typing import Dict, Any, List
from datetime import datetime, timezone
import re
import subprocess
import json

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


@router.get("/api/certificate/status")
async def get_certificate_status(request: Request) -> Dict[str, Any]:
    """Get wildcard certificate status information."""
    api_logger.info("Certificate status requested")
    
    try:
        # Use Caddy API to check certificate info if available
        if request.app.state.caddy_manager:
            # Get TLS certificates info from Caddy
            caddy_url = request.app.state.caddy_manager.api_url
            import httpx
            
            async with httpx.AsyncClient() as client:
                try:
                    # Get certificates info from Caddy admin API
                    response = await client.get(f"{caddy_url}/config/apps/tls/certificates")
                    if response.status_code == 200:
                        certificates = response.json()
                        
                        # Look for our wildcard certificate
                        for cert_key, cert_info in certificates.items():
                            if isinstance(cert_info, dict) and "subjects" in cert_info:
                                subjects = cert_info.get("subjects", [])
                                if "*.snadboy.com" in subjects:
                                    # Found our certificate
                                    not_after = cert_info.get("not_after")
                                    if not_after:
                                        # Convert timestamp to datetime
                                        expiry_dt = datetime.fromtimestamp(not_after, timezone.utc)
                                        expiry_date = expiry_dt.isoformat()
                                        
                                        # Calculate days until expiry
                                        now = datetime.now(timezone.utc)
                                        days_until_expiry = (expiry_dt - now).days
                                        
                                        if days_until_expiry > 30:
                                            status = "valid"
                                        elif days_until_expiry > 7:
                                            status = "expiring"
                                        else:
                                            status = "expired"
                                        
                                        return {
                                            "exists": True,
                                            "domain": "*.snadboy.com",
                                            "issuer": "Let's Encrypt",
                                            "sans": subjects,
                                            "expiry_date": expiry_date,
                                            "days_until_expiry": days_until_expiry,
                                            "status": status,
                                            "challenge_type": "DNS-01",
                                            "provider": "Cloudflare"
                                        }
                                
                except Exception as e:
                    api_logger.warning(f"Could not get certificate info from Caddy API: {e}")
        
        # Fallback to openssl command to check certificate
        try:
            # Use openssl command to get certificate info
            cmd = [
                "sh", "-c", 
                "echo | openssl s_client -connect revp-api.snadboy.com:443 -servername revp-api.snadboy.com 2>/dev/null | openssl x509 -noout -text"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                cert_text = result.stdout
                
                # Parse certificate information
                domain = "*.snadboy.com"
                issuer = "Let's Encrypt"
                expiry_date = None
                
                for line in cert_text.split('\n'):
                    line = line.strip()
                    if line.startswith("Subject: CN ="):
                        domain = line.split("CN =", 1)[1].strip()
                    elif "Issuer:" in line and "Let's Encrypt" in line:
                        issuer = "Let's Encrypt"
                    elif "Not After :" in line:
                        # Parse "Not After : Oct 20 23:28:55 2025 GMT"
                        date_part = line.split("Not After :", 1)[1].strip()
                        expiry_dt = datetime.strptime(date_part, "%b %d %H:%M:%S %Y %Z")
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                        expiry_date = expiry_dt.isoformat()
                        
                        # Calculate days until expiry
                        now = datetime.now(timezone.utc)
                        days_until_expiry = (expiry_dt - now).days
                        
                        if days_until_expiry > 30:
                            status = "valid"
                        elif days_until_expiry > 7:
                            status = "expiring"
                        else:
                            status = "expired"
                        
                        return {
                            "exists": True,
                            "domain": domain,
                            "issuer": issuer,
                            "sans": [domain],
                            "expiry_date": expiry_date,
                            "days_until_expiry": days_until_expiry,
                            "status": status,
                            "challenge_type": "DNS-01",
                            "provider": "Cloudflare"
                        }
                    
        except Exception as e:
            api_logger.warning(f"Could not get certificate via openssl command: {e}")
        
        # If all methods fail, return default response
        return {
            "exists": False,
            "domain": "*.snadboy.com",
            "issuer": "Unknown",
            "sans": [],
            "expiry_date": None,
            "days_until_expiry": None,
            "status": "unknown",
            "challenge_type": "DNS-01",
            "provider": "Cloudflare"
        }
            
    except Exception as e:
        api_logger.error(f"Error getting certificate status: {e}")
        return {
            "exists": False,
            "domain": "*.snadboy.com",
            "issuer": "Unknown",
            "sans": [],
            "expiry_date": None,
            "days_until_expiry": None,
            "status": "error",
            "challenge_type": "DNS-01",
            "provider": "Cloudflare",
            "error": str(e)
        }


@router.get("/api/hosts/status")
async def get_hosts_status(request: Request) -> Dict[str, Any]:
    """Get hosts configuration and connection status."""
    api_logger.info("Hosts status requested")
    
    try:
        hosts_info = {
            "configuration_type": "unknown",
            "hosts": [],
            "total_hosts": 0,
            "enabled_hosts": 0,
            "connection_status": {}
        }
        
        # Check which configuration method is being used
        if settings.has_hosts_config():
            hosts_config = settings.get_hosts_config()
            if hosts_config:
                hosts_info["configuration_type"] = "hosts.yml"
                enabled_hosts = hosts_config.get_enabled_hosts()
                
                # Build hosts information
                for alias, host_config in hosts_config.hosts.items():
                    host_info = {
                        "alias": alias,
                        "hostname": host_config.hostname,
                        "user": host_config.user,
                        "port": host_config.port,
                        "description": host_config.description,
                        "enabled": host_config.enabled,
                        "key_file": host_config.key_file  # May want to mask this in production
                    }
                    hosts_info["hosts"].append(host_info)
                
                hosts_info["total_hosts"] = len(hosts_config.hosts)
                hosts_info["enabled_hosts"] = len(enabled_hosts)
        else:
            hosts_info["configuration_type"] = "DOCKER_HOSTS"
            docker_hosts = settings.parse_docker_hosts()
            
            # Build hosts information from DOCKER_HOSTS
            for alias, hostname, port in docker_hosts:
                host_info = {
                    "alias": alias,
                    "hostname": hostname,
                    "user": settings.ssh_user,
                    "port": port,
                    "description": f"Legacy host from DOCKER_HOSTS",
                    "enabled": True,
                    "key_file": settings.ssh_private_key_path
                }
                hosts_info["hosts"].append(host_info)
            
            hosts_info["total_hosts"] = len(docker_hosts)
            hosts_info["enabled_hosts"] = len(docker_hosts)
        
        # Get connection status if SSH manager is available
        if request.app.state.ssh_manager:
            try:
                connection_results = request.app.state.ssh_manager.test_connections()
                hosts_info["connection_status"] = connection_results
            except Exception as e:
                api_logger.warning(f"Could not test SSH connections: {e}")
                hosts_info["connection_status"] = {}
        
        return hosts_info
        
    except Exception as e:
        api_logger.error(f"Error getting hosts status: {e}")
        return {
            "configuration_type": "error",
            "hosts": [],
            "total_hosts": 0,
            "enabled_hosts": 0,
            "connection_status": {},
            "error": str(e)
        }