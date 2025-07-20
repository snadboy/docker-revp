"""Docker container monitoring and event handling."""
import asyncio
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .logger import docker_logger


class ServiceInfo:
    """Individual service configuration for containers or static routes."""
    
    def __init__(self, port: str = None, labels_dict: dict = None, static_route=None):
        if static_route:
            # Initialize from static route
            self.port = "static"
            self.domain = static_route.domain
            self.backend_proto = "http" if static_route.backend_url.startswith("http://") else "https"
            self.backend_path = static_route.backend_path
            self.force_ssl = static_route.force_ssl
            self.support_websocket = static_route.support_websocket
            self.resolved_host_port = None
            self._static_backend_url = static_route.backend_url
            self.is_static = True
        else:
            # Initialize from container labels
            self.port = port
            self.domain = labels_dict.get("domain", "")
            self.backend_proto = labels_dict.get("backend-proto", "http")
            self.backend_path = labels_dict.get("backend-path", "/")
            self.force_ssl = labels_dict.get("force-ssl", "true").lower() == "true"
            self.support_websocket = labels_dict.get("support-websocket", "false").lower() == "true"
            self.resolved_host_port = None
            self._static_backend_url = None
            self.is_static = False
    
    @property
    def is_valid(self) -> bool:
        """Check if service has valid configuration."""
        if self.is_static:
            return bool(self.domain and self._static_backend_url)
        return bool(self.domain and self.port)
    
    def backend_url(self, host_ip: str = None) -> str:
        """Get the backend URL for this service."""
        if self.is_static:
            # For static routes, return the configured backend URL directly
            path = self.backend_path if self.backend_path.startswith('/') else f"/{self.backend_path}"
            if self._static_backend_url.endswith('/') and path.startswith('/'):
                path = path[1:]  # Remove duplicate slash
            return f"{self._static_backend_url.rstrip('/')}{path}"
        else:
            # For container services, construct URL from host and port
            path = self.backend_path if self.backend_path.startswith('/') else f"/{self.backend_path}"
            # Use resolved host port if available, otherwise fall back to container port
            port = self.resolved_host_port if self.resolved_host_port else self.port
            return f"{self.backend_proto}://{host_ip}:{port}{path}"
    
    def to_dict(self) -> dict:
        """Convert service to dictionary representation."""
        return {
            "port": self.port,
            "domain": self.domain,
            "backend_proto": self.backend_proto,
            "backend_path": self.backend_path,
            "force_ssl": self.force_ssl,
            "support_websocket": self.support_websocket,
            "resolved_host_port": self.resolved_host_port,
            "is_static": self.is_static,
            "static_backend_url": self._static_backend_url if self.is_static else None
        }


class ContainerInfo:
    """Container information and metadata with multiple services."""
    
    def __init__(self, container_id: str, host: str, host_ip: str, labels: dict, name: str):
        self.container_id = container_id
        self.host = host
        self.host_ip = host_ip
        self.name = name
        self.labels = labels
        self.last_seen = datetime.utcnow()
        
        # Parse port-based services from labels
        self.services = self._parse_services(labels)
    
    def _parse_services(self, labels: dict) -> dict:
        """Parse port-based service configurations from labels."""
        services = {}
        
        for label_key, value in labels.items():
            if not label_key.startswith("snadboy.revp."):
                continue
            
            # Split label: snadboy.revp.{port}.{property}
            parts = label_key.split(".")
            if len(parts) != 4:
                continue
            
            prefix, revp, port, property_name = parts
            
            # Validate port is numeric
            if not port.isdigit():
                continue
            
            # Initialize service if not exists
            if port not in services:
                services[port] = {}
            
            # Store property for this port
            services[port][property_name] = value
        
        # Convert to ServiceInfo objects
        service_objects = {}
        for port, service_labels in services.items():
            service_objects[port] = ServiceInfo(port, service_labels)
        
        return service_objects
    
    @property
    def is_valid(self) -> bool:
        """Check if container has any valid service configurations."""
        return any(service.is_valid for service in self.services.values())
    
    @property
    def valid_services(self) -> dict:
        """Get only the valid services."""
        return {port: service for port, service in self.services.items() if service.is_valid}
    
    def resolve_port_mapping(self, port_bindings: dict) -> None:
        """Resolve container ports to host ports from Docker port bindings.
        
        Args:
            port_bindings: Docker NetworkSettings.Ports dict
        """
        if not port_bindings:
            return
        
        # Resolve port mappings for each service
        for service in self.services.values():
            if not service.port:
                continue
            
            # Look for the container port in the bindings
            # Docker uses format like "80/tcp", "443/tcp"
            tcp_key = f"{service.port}/tcp"
            udp_key = f"{service.port}/udp"
            
            # Check TCP first (most common)
            if tcp_key in port_bindings and port_bindings[tcp_key]:
                # port_bindings[tcp_key] is a list of dicts like [{"HostIp": "0.0.0.0", "HostPort": "8080"}]
                # Take the first binding
                binding = port_bindings[tcp_key][0]
                service.resolved_host_port = binding.get("HostPort")
            elif udp_key in port_bindings and port_bindings[udp_key]:
                # Check UDP as fallback
                binding = port_bindings[udp_key][0]
                service.resolved_host_port = binding.get("HostPort")
            else:
                # Port not published or not found
                docker_logger.warning(
                    f"Container {self.name}: port {service.port} is not published to host"
                )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "container_id": self.container_id,
            "host": self.host,
            "host_ip": self.host_ip,
            "name": self.name,
            "services": {port: service.to_dict() for port, service in self.services.items()},
            "labels": self.labels,
            "last_seen": self.last_seen.isoformat()
        }


class DockerMonitor:
    """Monitor Docker containers across multiple hosts."""
    
    def __init__(self, caddy_manager=None):
        self.caddy_manager = caddy_manager
        self.containers: Dict[str, ContainerInfo] = {}
        self.hosts_config = settings.parse_docker_hosts()
        self.executor = ThreadPoolExecutor(max_workers=len(self.hosts_config) or 1)
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start monitoring all configured Docker hosts."""
        self._running = True
        docker_logger.info("Starting Docker monitor")
        
        # Clean up stale Revp routes on startup
        if self.caddy_manager:
            await self.caddy_manager.cleanup_revp_routes(self)
        
        # Start monitoring each host
        for alias, host, port in self.hosts_config:
            task = asyncio.create_task(self._monitor_host(alias, host, port))
            self._tasks.append(task)
        
        # Start reconciliation task
        reconcile_task = asyncio.create_task(self._reconciliation_loop())
        self._tasks.append(reconcile_task)
        
        docker_logger.info(f"Started monitoring {len(self.hosts_config)} Docker hosts")
    
    async def stop(self) -> None:
        """Stop monitoring."""
        docker_logger.info("Stopping Docker monitor")
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        docker_logger.info("Docker monitor stopped")
    
    async def _monitor_host(self, alias: str, host: str, port: int) -> None:
        """Monitor Docker events from a specific host."""
        docker_logger.info(f"Starting event monitor for {host}:{port}")
        
        while self._running:
            try:
                # Get host IP address
                host_ip = await self._get_host_ip(alias, host)
                
                # Start docker events command
                cmd = [
                    "docker", "-H", f"ssh://{alias}",
                    "events",
                    "--filter", "type=container",
                    "--format", "{{json .}}"
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                docker_logger.info(f"Connected to Docker events on {host}:{port}")
                
                # Read events
                async for line in process.stdout:
                    if not self._running:
                        break
                    
                    try:
                        event = json.loads(line.decode().strip())
                        await self._handle_event(alias, host, host_ip, event)
                    except json.JSONDecodeError as e:
                        docker_logger.error(f"Failed to parse event from {host}: {e}")
                    except Exception as e:
                        docker_logger.error(f"Error handling event from {host}: {e}")
                
                # Check if process ended unexpectedly
                if self._running:
                    docker_logger.warning(f"Docker events stream ended for {host}, reconnecting...")
                    await asyncio.sleep(5)
                
            except Exception as e:
                docker_logger.error(f"Error monitoring {host}: {e}")
                if self._running:
                    await asyncio.sleep(30)  # Wait before retry
    
    async def _get_host_ip(self, alias: str, host: str) -> str:
        """Get the IP address of a Docker host."""
        # For localhost, return the host IP that containers can reach
        if host in ["localhost", "127.0.0.1"]:
            # Get the default gateway from inside a container's perspective
            return "host.docker.internal"
        
        # For remote hosts, try to resolve the IP
        try:
            import socket
            return socket.gethostbyname(host)
        except:
            return host  # Return original if resolution fails
    
    async def _handle_event(self, alias: str, host: str, host_ip: str, event: dict) -> None:
        """Handle a Docker container event."""
        action = event.get("Action", "")
        container_id = event.get("id", "")
        
        if not container_id:
            return
        
        docker_logger.debug(f"Event from {host}: {action} for container {container_id[:12]}")
        
        if action in ["start", "unpause"]:
            await self._handle_container_start(alias, host, host_ip, container_id)
        elif action in ["stop", "pause", "die", "kill"]:
            await self._handle_container_stop(container_id)
        elif action == "restart":
            # Handle restart as stop followed by start
            await self._handle_container_stop(container_id)
            await self._handle_container_start(alias, host, host_ip, container_id)
    
    async def _handle_container_start(self, alias: str, host: str, host_ip: str, container_id: str) -> None:
        """Handle container start event."""
        docker_logger.info(f"Processing container start for {container_id} on {host}")
        try:
            docker_logger.info(f"Getting container info for {container_id} using alias {alias}")
            # Get container details
            try:
                container_info = await self._get_container_info(alias, container_id)
                docker_logger.info(f"Container info result: {type(container_info)} - {bool(container_info)}")
            except Exception as inspect_error:
                docker_logger.error(f"Exception getting container info for {container_id}: {inspect_error}")
                return
            
            if not container_info:
                docker_logger.warning(f"Could not get container info for {container_id}")
                return
            
            # Check if container has our labels
            # Docker inspect returns labels under Config.Labels
            config = container_info.get("Config", {})
            labels = config.get("Labels", {})
            docker_logger.info(f"Container {container_id} labels: {labels}")
            # Check if container has any revp port-based labels
            has_revp_labels = any(key.startswith("snadboy.revp.") and len(key.split(".")) == 4 
                                 and key.split(".")[2].isdigit() 
                                 for key in labels.keys())
            
            if not has_revp_labels:
                docker_logger.info(f"Container {container_id} does not have any snadboy.revp port-based labels")
                return
            
            # Create ContainerInfo object
            container = ContainerInfo(
                container_id=container_id,
                host=host,
                host_ip=host_ip,
                labels=labels,
                name=container_info.get("Name", "").lstrip("/")
            )
            
            if not container.is_valid:
                docker_logger.warning(
                    f"Container {container.name} has revp labels but no valid service configurations"
                )
                return
            
            # Resolve container port to host port
            network_settings = container_info.get("NetworkSettings", {})
            port_bindings = network_settings.get("Ports", {})
            container.resolve_port_mapping(port_bindings)
            
            # Store container
            self.containers[container_id] = container
            
            # Log detected services
            valid_services = container.valid_services
            service_info = ", ".join([f"{service.domain} (port {port})" for port, service in valid_services.items()])
            docker_logger.info(
                f"Detected container {container.name} on {host} with services: {service_info}"
            )
            
            # Update Caddy for each valid service
            if self.caddy_manager:
                for port, service in valid_services.items():
                    docker_logger.info(f"Adding Caddy route for {service.domain}")
                    await self.caddy_manager.add_route(container, service)
                    docker_logger.info(f"Successfully added Caddy route for {service.domain}")
            else:
                docker_logger.error("CaddyManager is not available!")
            
        except Exception as e:
            docker_logger.error(f"Error handling container start: {e}")
    
    async def _handle_container_stop(self, container_id: str) -> None:
        """Handle container stop event."""
        # Try to find container by both full and short ID
        container = self.containers.get(container_id)
        
        if not container:
            # Try with short ID (first 12 chars)
            short_id = container_id[:12]
            for cid, cont in self.containers.items():
                if cid.startswith(short_id) or cid == short_id:
                    container = cont
                    container_id = cid  # Use the stored ID for removal
                    break
        
        if not container:
            return
        
        docker_logger.info(
            f"Container {container.name} stopped, removing routes"
        )
        
        # Remove from Caddy
        if self.caddy_manager:
            await self.caddy_manager.remove_route(container)
        
        # Remove from tracking (use the actual key found)
        if container_id in self.containers:
            del self.containers[container_id]
    
    async def _get_container_info(self, alias: str, container_id: str) -> Optional[dict]:
        """Get detailed container information."""
        try:
            cmd = [
                "docker", "-H", f"ssh://{alias}",
                "inspect", container_id
            ]
            
            docker_logger.debug(f"Running docker inspect for {container_id} with alias {alias}")
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                docker_logger.error(f"Failed to inspect container {container_id}: {stderr.decode()}")
                return None
            
            containers = json.loads(stdout.decode())
            container_info = containers[0] if containers else None
            if container_info:
                docker_logger.debug(f"Successfully got container info for {container_id}")
            else:
                docker_logger.warning(f"No container info returned for {container_id}")
            return container_info
            
        except Exception as e:
            docker_logger.error(f"Error getting container info for {container_id}: {e}")
            return None
    
    async def _reconciliation_loop(self) -> None:
        """Periodically reconcile container state."""
        await asyncio.sleep(10)  # Initial delay
        
        while self._running:
            try:
                docker_logger.info("Starting reconciliation")
                
                # Check if Caddy still has our routes
                if self.caddy_manager:
                    await self._check_and_restore_routes()
                
                await self._reconcile_all_hosts()
                docker_logger.info("Reconciliation completed")
            except Exception as e:
                docker_logger.error(f"Reconciliation error: {e}")
            
            await asyncio.sleep(settings.reconcile_interval)
    
    async def _check_and_restore_routes(self) -> None:
        """Check if our tracked routes still exist in Caddy and restore missing ones."""
        # Skip route restoration if we have no containers tracked yet
        # This happens after startup cleanup - containers will be discovered in reconciliation
        if not self.containers:
            docker_logger.debug("No containers tracked yet, skipping route restoration check")
            return
            
        try:
            # Get current Caddy routes
            caddy_config = await self.caddy_manager.get_current_config()
            current_routes = []
            
            # Extract route IDs from Caddy config
            servers = caddy_config.get("apps", {}).get("http", {}).get("servers", {})
            for server_name, server_config in servers.items():
                routes = server_config.get("routes", [])
                for route in routes:
                    route_id = route.get("@id", "")
                    # Only track routes with revp_route_ prefix (new format)
                    if route_id.startswith("revp_route_"):
                        current_routes.append(route_id)
                    # Skip legacy route_ format - only manage revp_route_ prefixed routes
                    elif route_id.startswith("route_"):
                        docker_logger.debug(f"Ignoring legacy route_ format: {route_id}")
            
            # Check each tracked container and its services
            missing_routes = []
            for container_id, container in self.containers.items():
                # Check each service in the container
                for port, service in container.valid_services.items():
                    expected_route_id = f"revp_route_{container_id}_{port}"
                    
                    if expected_route_id not in current_routes:
                        missing_routes.append((container, service))
            
            # Restore missing routes
            if missing_routes:
                docker_logger.warning(f"Found {len(missing_routes)} missing routes in Caddy, restoring...")
                for container, service in missing_routes:
                    try:
                        docker_logger.info(f"Restoring route for {service.domain}")
                        await self.caddy_manager.add_route(container, service)
                    except Exception as e:
                        docker_logger.error(f"Failed to restore route for {service.domain}: {e}")
                        
        except Exception as e:
            docker_logger.error(f"Error checking routes: {e}")
    
    async def _reconcile_all_hosts(self) -> None:
        """Reconcile containers from all hosts."""
        docker_logger.info(f"Reconciling {len(self.hosts_config)} hosts")
        seen_containers: Set[str] = set()
        
        # Check all hosts
        tasks = []
        for alias, host, port in self.hosts_config:
            docker_logger.info(f"Adding reconciliation task for {host} (alias: {alias})")
            task = self._reconcile_host(alias, host, port, seen_containers)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                host_info = self.hosts_config[i]
                docker_logger.error(f"Reconciliation failed for {host_info[1]}: {result}")
        
        # FORCE ROUTE CREATION: If we have no tracked containers, manually process all RevP containers
        if not self.containers:
            docker_logger.info("No tracked containers found, forcing route creation for all RevP containers")
            await self._force_route_creation()
        
        # Remove containers that are no longer running
        to_remove = []
        for container_id, container in self.containers.items():
            if container_id not in seen_containers:
                docker_logger.info(
                    f"Container {container.name} no longer exists, removing"
                )
                to_remove.append(container_id)
        
        for container_id in to_remove:
            await self._handle_container_stop(container_id)
    
    async def _force_route_creation(self) -> None:
        """Force route creation for all containers with RevP labels."""
        try:
            # Get all containers from API
            for alias, host, port in self.hosts_config:
                docker_logger.info(f"Force processing containers on {host}")
                docker_logger.debug(f"Getting host IP for {host}")
                host_ip = await self._get_host_ip(alias, host)
                docker_logger.debug(f"Host IP for {host}: {host_ip}")
                
                # Get all containers
                docker_logger.debug(f"About to call list_containers_sync for {host}")
                containers = self.list_containers_sync(host)
                docker_logger.info(f"Found {len(containers)} total containers from force route creation")
                
                for container_data in containers:
                    # Parse labels properly (same logic as API)
                    labels_str = container_data.get("Labels", "")
                    if labels_str:
                        labels = {}
                        for label in labels_str.split(','):
                            if '=' in label:
                                key, value = label.split('=', 1)
                                labels[key] = value
                    else:
                        labels = {}
                    
                    # Check for revp labels
                    revp_labels = {k: v for k, v in labels.items() if k.startswith("snadboy.revp.")}
                    has_revp = bool(revp_labels)
                    
                    if has_revp:
                        container_id = container_data['ID']
                        container_name = container_data.get('Names', '').lstrip('/') if container_data.get('Names') else ''
                        docker_logger.info(f"Force creating route for {container_name} ({container_id})")
                        
                        # Process this container
                        try:
                            await self._handle_container_start(alias, host, host_ip, container_id)
                        except Exception as container_error:
                            docker_logger.error(f"Error processing container {container_id}: {container_error}")
                    else:
                        container_name = container_data.get('Names', '').lstrip('/') if container_data.get('Names') else 'unknown'
                        docker_logger.debug(f"Skipping container {container_name} - no RevP config")
                        
        except Exception as e:
            import traceback
            docker_logger.error(f"Error in force route creation: {e}")
            docker_logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _reconcile_host(self, alias: str, host: str, port: int, seen_containers: Set[str]) -> None:
        """Reconcile containers from a specific host."""
        try:
            docker_logger.info(f"Reconciling host {host} with alias {alias}")
            host_ip = await self._get_host_ip(alias, host)
            
            # List running containers
            cmd = [
                "docker", "-H", f"ssh://{alias}",
                "ps", "--format", "{{json .}}"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                docker_logger.error(f"Failed to list containers on {host}: {stderr.decode()}")
                return
            
            # Process each container
            containers_found = stdout.decode().strip().split('\n')
            docker_logger.info(f"Found {len([l for l in containers_found if l])} containers on {host}")
            
            for line in containers_found:
                if not line:
                    continue
                
                try:
                    container_summary = json.loads(line)
                    container_id = container_summary.get("ID", "")
                    
                    if not container_id:
                        continue
                    
                    seen_containers.add(container_id)
                    
                    # Check if we're already tracking this container
                    if container_id not in self.containers:
                        # Get full container info and check labels
                        docker_logger.info(f"Found new container {container_id} on {host}, processing...")
                        await self._handle_container_start(alias, host, host_ip, container_id)
                    else:
                        # Update last seen time
                        self.containers[container_id].last_seen = datetime.utcnow()
                        
                except Exception as e:
                    docker_logger.error(f"Error processing container: {e}")
                    
        except Exception as e:
            docker_logger.error(f"Error reconciling host {host}: {e}")
    
    def get_status(self) -> dict:
        """Get current monitoring status."""
        host_status = {}
        
        # Count containers per host
        for container in self.containers.values():
            if container.host not in host_status:
                host_status[container.host] = {
                    "container_count": 0,
                    "domains": []
                }
            
            host_status[container.host]["container_count"] += 1
            # Add all service domains for this container
            for service in container.valid_services.values():
                host_status[container.host]["domains"].append(service.domain)
        
        return {
            "total_containers": len(self.containers),
            "hosts": host_status,
            "monitored_hosts": [
                {"alias": alias, "host": host, "port": port}
                for alias, host, port in self.hosts_config
            ]
        }
    
    def list_containers_sync(self, hostname: str) -> List[dict]:
        """List containers on a specific host (synchronous)."""
        try:
            docker_logger.info(f"Looking for containers on {hostname}")
            # Find the host config
            alias = None
            for a, h, p in self.hosts_config:
                if h == hostname:
                    alias = a
                    break
            
            if not alias:
                docker_logger.warning(f"No alias found for hostname {hostname}")
                return []
            
            # Run docker ps command synchronously
            import subprocess
            result = subprocess.run([
                "docker", "-H", f"ssh://{alias}",
                "ps", "--format", "{{json .}}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                docker_logger.error(f"Failed to list containers on {hostname}: {result.stderr}")
                return []
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        docker_logger.error(f"Error parsing container JSON: {e} - Line: {line[:100]}")
            
            docker_logger.info(f"Successfully parsed {len(containers)} containers from {hostname}")
            return containers
            
        except Exception as e:
            docker_logger.error(f"Error listing containers on {hostname}: {e}")
            return []
    
    def inspect_container_sync(self, hostname: str, container_id: str) -> dict:
        """Inspect a specific container (synchronous)."""
        try:
            # Find the host config
            alias = None
            for a, h, p in self.hosts_config:
                if h == hostname:
                    alias = a
                    break
            
            if not alias:
                return {}
            
            # Run docker inspect command synchronously
            import subprocess
            result = subprocess.run([
                "docker", "-H", f"ssh://{alias}",
                "inspect", container_id
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                docker_logger.error(f"Failed to inspect container {container_id} on {hostname}: {result.stderr}")
                return {}
            
            data = json.loads(result.stdout)
            return data[0] if data else {}
            
        except Exception as e:
            docker_logger.error(f"Error inspecting container {container_id} on {hostname}: {e}")
            return {}