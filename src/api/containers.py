"""Container management endpoints for Docker Reverse Proxy."""
from typing import List, Dict, Any, Optional
import hashlib

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..logger import api_logger
from ..docker_monitor import ContainerInfo


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
                
                # Check for port-based revp labels (new format)
                revp_labels = {k: v for k, v in labels.items() if k.startswith("snadboy.revp.")}
                has_revp = any(key.startswith("snadboy.revp.") and len(key.split(".")) == 4 
                              and key.split(".")[2].isdigit() 
                              for key in labels.keys())
                
                # Use the raw revp labels for ContainerInfo (no processing needed)
                processed_revp = revp_labels
                
                # Get container ID, fallback to generating one from name+host
                container_id = container.get("ID", container.get("Id", ""))
                if not container_id:
                    # Generate a unique ID from container name and host
                    container_id = hashlib.sha256(f"{container_name}@{hostname}".encode()).hexdigest()[:12]
                
                # Create ContainerInfo object to get service information
                services_info = []
                
                if has_revp:
                    # Get host IP - use simple resolution for API endpoint
                    if hostname in ["localhost", "127.0.0.1"]:
                        host_ip = "host.docker.internal"
                    else:
                        try:
                            import socket
                            host_ip = socket.gethostbyname(hostname)
                        except:
                            host_ip = hostname  # Fallback to hostname
                    
                    # Create ContainerInfo object
                    container_info_obj = ContainerInfo(
                        container_id=container_id,
                        host=hostname,
                        host_ip=host_ip,
                        labels=processed_revp,
                        name=container_name
                    )
                    
                    # Try to resolve port mapping from container ports
                    ports = container.get("Ports", "")
                    if ports:
                        # Parse port bindings from Docker output
                        port_bindings = {}
                        for port_info in ports.split(','):
                            port_info = port_info.strip()
                            if '->' in port_info:
                                # Format: "0.0.0.0:8080->80/tcp"
                                host_part, container_part = port_info.split('->', 1)
                                if ':' in host_part:
                                    host_port = host_part.split(':')[-1]
                                    container_port_proto = container_part.strip()
                                    if container_port_proto not in port_bindings:
                                        port_bindings[container_port_proto] = []
                                    port_bindings[container_port_proto].append({
                                        "HostPort": host_port,
                                        "HostIp": "0.0.0.0"
                                    })
                        
                        # Resolve port mapping
                        container_info_obj.resolve_port_mapping(port_bindings)
                    
                    # Get services information
                    for port, service in container_info_obj.valid_services.items():
                        services_info.append({
                            "port": port,
                            "domain": service.domain,
                            "backend_url": service.backend_url(host_ip),
                            "resolved_host_port": service.resolved_host_port,
                            "backend_proto": service.backend_proto,
                            "backend_path": service.backend_path,
                            "force_ssl": service.force_ssl,
                            "support_websocket": service.support_websocket
                        })
                
                # Create container info dictionary
                container_info = {
                    "id": container_id,
                    "name": container_name,
                    "host": hostname,
                    "state": container.get("State", "unknown"),
                    "status": container.get("Status", ""),
                    "image": container.get("Image", ""),
                    "has_revp_config": has_revp,
                    "labels": processed_revp,
                    "services": services_info
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