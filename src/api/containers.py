"""Container management endpoints for Docker Reverse Proxy."""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..logger import api_logger


router = APIRouter(prefix="/containers", tags=["containers"])


# Removed parse_labels_string function to avoid conflicts


@router.get("")
async def list_containers(
    request: Request,
    host: Optional[str] = None,
    with_revp_labels: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    List all monitored containers.
    
    Args:
        host: Filter by specific host
        with_revp_labels: Filter containers with/without revp labels
                         None = all containers
                         True = only containers with revp labels
                         False = only containers without revp labels
    
    Returns:
        List of container information with their labels and revp configuration status
    """
    api_logger.info(f"Listing containers (host={host}, with_revp_labels={with_revp_labels})")
    
    if not request.app.state.docker_monitor:
        raise HTTPException(status_code=503, detail="Docker monitor not initialized")
    
    try:
        # Get all containers from the Docker monitor
        containers = []
        
        # Get hosts from the docker monitor's host configuration
        for alias, hostname, port in request.app.state.docker_monitor.hosts_config:
            # Filter by host if specified
            if host and hostname != host:
                continue
                
            # Get containers for this host
            host_containers = request.app.state.docker_monitor.list_containers_sync(hostname)
            
            for container in host_containers:
                # Parse labels properly
                labels_str = container.get("Labels", "")
                if labels_str:
                    labels = {}
                    for label in labels_str.split(','):
                        if '=' in label:
                            key, value = label.split('=', 1)
                            labels[key] = value
                else:
                    labels = {}
                
                # Extract container name for defaults
                container_name = container.get("Names", "").lstrip("/") if container.get("Names") else ""
                
                # Check for revp labels
                revp_labels = {k: v for k, v in labels.items() if k.startswith("snadboy.revp.")}
                has_revp = bool(revp_labels)
                
                # Process revp labels with defaults
                if has_revp:
                    processed_revp = {}
                    for key, value in revp_labels.items():
                        if key == "snadboy.revp.title" and not value:
                            processed_revp[key] = container_name
                        elif key == "snadboy.revp.description" and not value:
                            processed_revp[key] = ""
                        else:
                            processed_revp[key] = value
                    
                    # Add defaults for missing keys
                    if "snadboy.revp.title" not in revp_labels:
                        processed_revp["snadboy.revp.title"] = container_name
                    if "snadboy.revp.description" not in revp_labels:
                        processed_revp["snadboy.revp.description"] = ""
                    
                    # Test label to verify processing works
                    processed_revp["snadboy.revp.test"] = "defaults_applied"
                else:
                    processed_revp = revp_labels
                
                # Get container ID, fallback to generating one from name+host
                container_id = container.get("ID", container.get("Id", ""))
                if not container_id:
                    # Generate a unique ID from container name and host
                    import hashlib
                    container_id = hashlib.sha256(f"{container_name}@{hostname}".encode()).hexdigest()[:12]
                
                # Create container info
                container_info = {
                    "id": container_id,
                    "name": container_name,
                    "host": hostname,
                    "state": container.get("State", "unknown"),
                    "status": container.get("Status", ""),
                    "image": container.get("Image", ""),
                    "has_revp_config": has_revp,
                    "labels": processed_revp
                }
                
                # Apply filter
                if with_revp_labels is not None:
                    if with_revp_labels and not has_revp:
                        continue
                    elif not with_revp_labels and has_revp:
                        continue
                
                containers.append(container_info)
        
        # Sort by host and name
        containers.sort(key=lambda x: (x["host"], x["name"]))
        
        return containers
        
    except Exception as e:
        import traceback
        api_logger.error(f"Error listing containers: {e}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def containers_summary(request: Request) -> Dict[str, Any]:
    """Get summary statistics about monitored containers."""
    api_logger.info("Getting containers summary")
    
    if not request.app.state.docker_monitor:
        raise HTTPException(status_code=503, detail="Docker monitor not initialized")
    
    try:
        docker_status = request.app.state.docker_monitor.get_status()
        
        # Calculate statistics
        total_containers = 0
        containers_with_revp = 0
        containers_by_host = {}
        
        # Get hosts from the docker monitor's host configuration
        for alias, hostname, port in request.app.state.docker_monitor.hosts_config:
            host_containers = request.app.state.docker_monitor.list_containers_sync(hostname)
            host_count = len(host_containers)
            revp_count = 0
            
            for container in host_containers:
                labels_str = container.get("Labels", "")
                if labels_str:
                    labels = {}
                    for label in labels_str.split(','):
                        if '=' in label:
                            key, value = label.split('=', 1)
                            labels[key] = value
                else:
                    labels = {}
                
                if any(k.startswith("snadboy.revp.") for k in labels.keys()):
                    revp_count += 1
            
            total_containers += host_count
            containers_with_revp += revp_count
            containers_by_host[hostname] = {
                "total": host_count,
                "with_revp_config": revp_count,
                "without_revp_config": host_count - revp_count
            }
        
        return {
            "total_containers": total_containers,
            "containers_with_revp_config": containers_with_revp,
            "containers_without_revp_config": total_containers - containers_with_revp,
            "hosts": containers_by_host,
            "monitored_hosts": len(docker_status["hosts"])
        }
        
    except Exception as e:
        api_logger.error(f"Error getting containers summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# get_container function temporarily removed