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




@router.get("/api/hosts/status")
async def get_hosts_status(request: Request) -> Dict[str, Any]:
    """Get hosts configuration and connection status."""
    api_logger.info("Hosts status requested")
    
    try:
        from ..hosts_config import verify_hostname_resolution
        
        hosts_info = {
            "configuration_type": "unknown",
            "hosts": [],
            "total_hosts": 0,
            "enabled_hosts": 0,
            "connection_status": {},
            "dns_verification": {},
            "validation_errors": []
        }
        
        # Load hosts configuration from hosts.yml
        hosts_config = settings.load_hosts_config()
        hosts_info["configuration_type"] = "hosts.yml"
        enabled_hosts = hosts_config.get_enabled_hosts()
        
        # Perform DNS verification
        dns_results = verify_hostname_resolution(hosts_config, check_dns=True)
        hosts_info["dns_verification"] = dns_results
        
        # Build hosts information with DNS status
        for alias, host_config in hosts_config.hosts.items():
            dns_info = dns_results.get(alias, {})
            host_info = {
                "alias": alias,
                "hostname": host_config.hostname,
                "user": host_config.user,
                "port": host_config.port,
                "description": host_config.description,
                "enabled": host_config.enabled,
                "key_file": host_config.key_file,  # May want to mask this in production
                "dns_resolved": dns_info.get("dns_resolved", False),
                "ip_address": dns_info.get("ip_address"),
                "dns_errors": dns_info.get("errors", []),
                "dns_warnings": dns_info.get("warnings", [])
            }
            hosts_info["hosts"].append(host_info)
            
            # Collect validation errors
            if dns_info.get("errors"):
                for error in dns_info["errors"]:
                    hosts_info["validation_errors"].append(f"{alias}: {error}")
        
        hosts_info["total_hosts"] = len(hosts_config.hosts)
        hosts_info["enabled_hosts"] = len(enabled_hosts)
        
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


@router.get("/api/verify-caddy")
async def verify_caddy_configuration(request: Request) -> Dict[str, Any]:
    """Verify that Caddy configuration matches discovered containers and static routes."""
    api_logger.info("Caddy configuration verification requested")
    
    try:
        verification = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "container_routes": {
                "matched": 0,
                "missing": 0,
                "orphaned": 0,
                "details": []
            },
            "static_routes": {
                "matched": 0,
                "missing": 0,
                "details": []
            }
        }
        
        # Get current Caddy configuration
        caddy_config = {}
        caddy_routes = {}
        
        if request.app.state.caddy_manager:
            try:
                caddy_config = await request.app.state.caddy_manager.get_current_config()
                # Extract route information from Caddy config
                servers = caddy_config.get("apps", {}).get("http", {}).get("servers", {})
                for server_name, server_config in servers.items():
                    routes = server_config.get("routes", [])
                    for route in routes:
                        route_id = route.get("@id", "")
                        if route_id.startswith("revp_route_") or route_id.startswith("revp_static_route_"):
                            # Extract domain from match
                            match_conditions = route.get("match", [])
                            for match in match_conditions:
                                hosts = match.get("host", [])
                                if hosts:
                                    caddy_routes[route_id] = {
                                        "domain": hosts[0],
                                        "route_id": route_id
                                    }
            except Exception as e:
                api_logger.error(f"Error getting Caddy configuration: {e}")
        
        # Check container routes
        if request.app.state.docker_monitor:
            try:
                # Get all containers with RevP labels from all hosts
                expected_routes = {}
                
                for alias, hostname, port in request.app.state.docker_monitor.hosts_config:
                    host_containers = request.app.state.docker_monitor.list_containers_sync(hostname)
                    
                    for container in host_containers:
                        container_id = container.get("ID", "")
                        labels_str = container.get("Labels", "")
                        
                        if labels_str and container_id:
                            labels = {}
                            for label in labels_str.split(','):
                                if '=' in label:
                                    key, value = label.split('=', 1)
                                    labels[key] = value
                            
                            # Check for RevP labels
                            revp_labels = {k: v for k, v in labels.items() if k.startswith("snadboy.revp.")}
                            if revp_labels:
                                # Parse port-based services
                                services = {}
                                for label_key, value in revp_labels.items():
                                    parts = label_key.split(".")
                                    if len(parts) == 4:  # snadboy.revp.{port}.{property}
                                        port_num = parts[2]
                                        property_name = parts[3]
                                        
                                        if port_num not in services:
                                            services[port_num] = {}
                                        services[port_num][property_name] = value
                                
                                # Create expected routes for each service
                                for port_num, service_labels in services.items():
                                    domain = service_labels.get("domain")
                                    if domain:
                                        expected_route_id = f"revp_route_{container_id}_{port_num}"
                                        expected_routes[expected_route_id] = {
                                            "domain": domain,
                                            "container_id": container_id,
                                            "port": port_num,
                                            "hostname": hostname
                                        }
                
                # Compare expected routes with Caddy routes
                for expected_id, expected_info in expected_routes.items():
                    if expected_id in caddy_routes:
                        verification["container_routes"]["matched"] += 1
                        verification["container_routes"]["details"].append({
                            "status": "matched",
                            "route_id": expected_id,
                            "domain": expected_info["domain"],
                            "container_id": expected_info["container_id"]
                        })
                    else:
                        verification["container_routes"]["missing"] += 1
                        verification["container_routes"]["details"].append({
                            "status": "missing",
                            "route_id": expected_id,
                            "domain": expected_info["domain"],
                            "container_id": expected_info["container_id"],
                            "message": "Container has RevP labels but no Caddy route found"
                        })
                
                # Check for orphaned routes (routes without corresponding containers)
                for caddy_id, caddy_info in caddy_routes.items():
                    if caddy_id.startswith("revp_route_") and caddy_id not in expected_routes:
                        verification["container_routes"]["orphaned"] += 1
                        verification["container_routes"]["details"].append({
                            "status": "orphaned",
                            "route_id": caddy_id,
                            "domain": caddy_info["domain"],
                            "message": "Caddy route exists but no corresponding container found"
                        })
                        
            except Exception as e:
                api_logger.error(f"Error verifying container routes: {e}")
        
        # Check static routes
        if request.app.state.static_routes_manager:
            try:
                static_routes = request.app.state.static_routes_manager.get_routes()
                
                for route in static_routes:
                    domain = route.domain
                    expected_route_id = f"revp_static_route_{domain.replace('.', '_')}"
                    
                    # Check if static route exists in Caddy
                    found_in_caddy = False
                    for caddy_id, caddy_info in caddy_routes.items():
                        if caddy_id.startswith("revp_static_route_") and caddy_info["domain"] == domain:
                            found_in_caddy = True
                            break
                    
                    if found_in_caddy:
                        verification["static_routes"]["matched"] += 1
                        verification["static_routes"]["details"].append({
                            "status": "matched",
                            "domain": domain,
                            "backend_url": route.backend_url
                        })
                    else:
                        verification["static_routes"]["missing"] += 1
                        verification["static_routes"]["details"].append({
                            "status": "missing",
                            "domain": domain,
                            "backend_url": route.backend_url,
                            "message": "Static route defined but no Caddy configuration found"
                        })
                        
            except Exception as e:
                api_logger.error(f"Error verifying static routes: {e}")
        
        api_logger.info(f"Caddy verification completed: {verification['container_routes']['matched']} container routes matched, "
                       f"{verification['container_routes']['missing']} missing, {verification['container_routes']['orphaned']} orphaned, "
                       f"{verification['static_routes']['matched']} static routes matched, {verification['static_routes']['missing']} static missing")
        
        return verification
        
    except Exception as e:
        api_logger.error(f"Error during Caddy verification: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "container_routes": {"matched": 0, "missing": 0, "orphaned": 0, "details": []},
            "static_routes": {"matched": 0, "missing": 0, "details": []}
        }

@router.get("/api/caddy-config", response_model=Dict[str, Any], tags=["about"])
async def get_caddy_config(request: Request) -> Dict[str, Any]:
    """Get the current Caddy configuration."""
    api_logger.info("Caddy configuration requested")
    
    try:
        # Get Caddy config from the API
        caddy_config = await request.app.state.caddy_manager.get_config()
        
        # Pretty format the JSON
        formatted_config = json.dumps(caddy_config, indent=2, sort_keys=True)
        
        return {
            "success": True,
            "config": formatted_config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        api_logger.error(f"Error retrieving Caddy configuration: {e}")
        return {
            "success": False,
            "error": str(e),
            "config": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/api/hosts/recheck-dns", response_model=Dict[str, Any])
async def recheck_hosts_dns(request: Request) -> Dict[str, Any]:
    """
    Recheck DNS resolution for all hosts.
    
    Returns:
        Summary of hosts DNS recheck results
    """
    api_logger.info("API: Rechecking DNS for all hosts")
    
    try:
        from ..hosts_config import validate_and_report_hosts
        from pathlib import Path
        
        # Validate hosts configuration with DNS check
        hosts_config_file = Path("/app/config/hosts.yml")
        
        if not hosts_config_file.exists():
            return {
                "status": "error",
                "message": "Hosts configuration file not found",
                "total_hosts": 0,
                "working_hosts": 0,
                "dns_issues": 0
            }
        
        success, report = validate_and_report_hosts(hosts_config_file, check_dns=True)
        
        # Calculate results
        total_hosts = report.get('enabled_hosts', 0)
        dns_results = report.get('dns_verification', {})
        
        working_hosts = 0
        dns_issues = 0
        
        for alias, result in dns_results.items():
            if result.get('dns_resolved', False):
                working_hosts += 1
            else:
                dns_issues += 1
        
        api_logger.info(f"Hosts DNS recheck completed: {working_hosts} working, {dns_issues} issues")
        
        # Also trigger SSH connection tests if SSH manager is available
        connection_status = {}
        if request.app.state.ssh_manager:
            try:
                api_logger.info("Testing SSH connections after DNS recheck")
                connection_status = request.app.state.ssh_manager.test_connections()
                api_logger.info(f"SSH connection tests completed: {len(connection_status)} hosts tested")
            except Exception as e:
                api_logger.warning(f"Could not test SSH connections during recheck: {e}")
        
        return {
            "status": "completed",
            "total_hosts": total_hosts,
            "working_hosts": working_hosts,
            "dns_issues": dns_issues,
            "success": success,
            "errors": report.get('errors', []),
            "warnings": report.get('warnings', []),
            "connection_status": connection_status,
            "message": f"DNS recheck completed for {total_hosts} hosts"
        }
        
    except Exception as e:
        api_logger.error(f"API: Error rechecking hosts DNS: {str(e)}")
        return {
            "status": "error", 
            "message": f"Error rechecking hosts DNS: {str(e)}",
            "total_hosts": 0,
            "working_hosts": 0,
            "dns_issues": 0
        }


@router.get("/api/missing-subdomains")
async def get_missing_subdomains() -> Dict[str, Any]:
    """Get statistics about missing subdomain requests."""
    api_logger.info("Missing subdomains statistics requested")
    
    try:
        import re
        from pathlib import Path
        from collections import defaultdict, Counter
        
        log_file = Path("/var/log/caddy/missing_subdomains.log")
        if not log_file.exists():
            return {
                "success": True,
                "message": "No missing subdomain requests logged yet",
                "requests": [],
                "summary": {
                    "total_requests": 0,
                    "unique_subdomains": 0,
                    "top_subdomains": [],
                    "recent_requests": []
                }
            }
        
        # Parse the last 1000 lines of the log file
        missing_requests = []
        subdomain_counts = Counter()
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last 1000 lines
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                for line in recent_lines:
                    try:
                        log_entry = json.loads(line.strip())
                        host = log_entry.get('request', {}).get('host', '')
                        timestamp = log_entry.get('ts', '')
                        method = log_entry.get('request', {}).get('method', '')
                        uri = log_entry.get('request', {}).get('uri', '')
                        status = log_entry.get('status', 0)
                        
                        if host and host.endswith('.snadboy.com'):
                            subdomain = host.split('.')[0]
                            subdomain_counts[subdomain] += 1
                            
                            missing_requests.append({
                                "subdomain": subdomain,
                                "full_host": host,
                                "timestamp": timestamp,
                                "method": method,
                                "uri": uri,
                                "status": status
                            })
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            api_logger.warning(f"Error parsing missing subdomains log: {e}")
        
        # Sort by timestamp (most recent first)
        missing_requests.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            "success": True,
            "requests": missing_requests[:100],  # Return last 100 requests
            "summary": {
                "total_requests": len(missing_requests),
                "unique_subdomains": len(subdomain_counts),
                "top_subdomains": subdomain_counts.most_common(10),
                "recent_requests": missing_requests[:10]
            }
        }
        
    except Exception as e:
        api_logger.error(f"Error retrieving missing subdomains statistics: {e}")
        return {
            "success": False,
            "error": str(e),
            "requests": [],
            "summary": {
                "total_requests": 0,
                "unique_subdomains": 0,
                "top_subdomains": [],
                "recent_requests": []
            }
        }