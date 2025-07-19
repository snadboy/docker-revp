"""Caddy reverse proxy management via Admin API."""
import asyncio
import json
from typing import Dict, Optional

import httpx

from .config import settings
from .logger import caddy_logger
from .docker_monitor import ContainerInfo


class CaddyManager:
    """Manage Caddy configuration via the Admin API."""
    
    def __init__(self):
        self.api_url = settings.caddy_api_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self._routes: Dict[str, str] = {}  # domain -> container_id mapping
    
    async def start(self) -> None:
        """Initialize Caddy manager."""
        caddy_logger.info(f"Initializing Caddy manager with API URL: {self.api_url}")
        
        # Test connection
        try:
            await self.test_connection()
            caddy_logger.info("Successfully connected to Caddy Admin API")
        except Exception as e:
            caddy_logger.error(f"Failed to connect to Caddy Admin API: {e}")
            raise
        
        # Note: Cleanup will be called later by DockerMonitor after initialization
    
    async def stop(self) -> None:
        """Stop Caddy manager."""
        await self.client.aclose()
    
    async def test_connection(self) -> bool:
        """Test connection to Caddy Admin API."""
        try:
            response = await self.client.get(f"{self.api_url}/config/")
            return response.status_code == 200
        except Exception as e:
            caddy_logger.error(f"Caddy connection test failed: {e}")
            return False
    
    async def add_route(self, container: ContainerInfo) -> None:
        """Add or update a route in Caddy."""
        if not container.is_valid:
            caddy_logger.warning(f"Invalid container configuration for {container.name}")
            return
        
        caddy_logger.info(
            f"Adding route: {container.domain} -> {container.backend_url} "
            f"(force_ssl: {container.force_ssl})"
        )
        
        try:
            # Check if another container is using this domain
            existing_container_id = self._routes.get(container.domain)
            if existing_container_id and existing_container_id != container.container_id:
                caddy_logger.warning(
                    f"Domain {container.domain} already in use by container "
                    f"{existing_container_id[:12]}, replacing with {container.container_id[:12]}"
                )
            
            # Create the route configuration
            route_config = self._create_route_config(container)
            
            # Apply configuration to Caddy
            await self._apply_route(container.domain, route_config)
            
            # Track the route
            self._routes[container.domain] = container.container_id
            
            caddy_logger.info(f"Successfully added route for {container.domain}")
            
        except Exception as e:
            caddy_logger.error(f"Failed to add route for {container.domain}: {e}")
            raise
    
    async def remove_route(self, container: ContainerInfo) -> None:
        """Remove a route from Caddy."""
        if not container.domain:
            return
        
        caddy_logger.info(f"Removing route for {container.domain}")
        
        try:
            # Check if this container owns the route
            if self._routes.get(container.domain) != container.container_id:
                caddy_logger.warning(
                    f"Container {container.container_id[:12]} does not own domain "
                    f"{container.domain}, skipping removal"
                )
                return
            
            # Remove from Caddy
            await self._remove_route(container.domain)
            
            # Remove from tracking
            self._routes.pop(container.domain, None)
            
            caddy_logger.info(f"Successfully removed route for {container.domain}")
            
        except Exception as e:
            caddy_logger.error(f"Failed to remove route for {container.domain}: {e}")
    
    def _create_route_config(self, container: ContainerInfo) -> dict:
        """Create Caddy route configuration for a container."""
        # Basic reverse proxy configuration
        # Use resolved_host_port if available, otherwise fall back to container_port
        backend_port = container.resolved_host_port if container.resolved_host_port else container.container_port
        
        config = {
            "@id": f"revp_route_{container.container_id}",
            "match": [{"host": [container.domain]}],
            "handle": [{
                "handler": "reverse_proxy",
                "upstreams": [{
                    "dial": f"{container.host_ip}:{backend_port}"
                }],
                "transport": {
                    "protocol": "http",
                    "tls": {} if container.backend_proto == "https" else None
                }
            }]
        }
        
        # Remove None values
        if config["handle"][0]["transport"]["tls"] is None:
            del config["handle"][0]["transport"]["tls"]
        
        # Handle backend path if not root
        if container.backend_path != "/":
            config["handle"][0]["rewrite"] = {
                "strip_path_prefix": container.backend_path.rstrip('/')
            }
        
        return config
    
    async def _apply_route(self, domain: str, route_config: dict) -> None:
        """Apply a route configuration to Caddy."""
        route_id = route_config.get("@id")
        if not route_id:
            raise Exception("Route configuration missing @id")
        
        # Check if route already exists
        if await self._route_exists(route_id):
            caddy_logger.info(f"Route {route_id} already exists for {domain}, skipping")
            return
        
        # Add the new route to the routes array
        response = await self.client.post(
            f"{self.api_url}/config/apps/http/servers/srv0/routes",
            json=route_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(
                f"Failed to apply route: {response.status_code} - {response.text}"
            )
    
    async def _remove_route(self, domain: str) -> None:
        """Remove a route configuration from Caddy."""
        # Get the container ID for this domain
        container_id = self._routes.get(domain, "")
        if not container_id:
            return  # No route to remove
        
        route_id = f"revp_route_{container_id}"
        
        # Get existing routes to find the index
        try:
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                return  # No routes to remove
            
            routes = routes_response.json()
            
            # Find the route index
            route_index = None
            for i, route in enumerate(routes):
                if route.get("@id") == route_id:
                    route_index = i
                    break
            
            if route_index is not None:
                # Remove the route by index
                response = await self.client.delete(
                    f"{self.api_url}/config/apps/http/servers/srv0/routes/{route_index}"
                )
                
                if response.status_code not in [200, 204]:
                    raise Exception(
                        f"Failed to remove route: {response.status_code} - {response.text}"
                    )
                    
        except Exception as e:
            # If remove fails, just log it - don't prevent other operations
            caddy_logger.warning(f"Failed to remove route for {domain}: {e}")
    
    async def _route_exists(self, route_id: str) -> bool:
        """Check if a route with the given ID already exists."""
        try:
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                return False
            
            routes = routes_response.json()
            
            # Check if any route has this ID
            for route in routes:
                if route.get("@id") == route_id:
                    return True
            return False
            
        except Exception as e:
            caddy_logger.error(f"Error checking if route exists: {e}")
            return False
    
    async def _remove_route_by_id(self, route_id: str) -> None:
        """Remove a route configuration from Caddy by route ID."""
        try:
            # Only remove routes with revp_route_ prefix
            if not route_id.startswith("revp_route_"):
                caddy_logger.info(f"Skipping removal of non-Revp route: {route_id}")
                return
                
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                return  # No routes to remove
            
            routes = routes_response.json()
            
            # Find the route index
            route_index = None
            for i, route in enumerate(routes):
                if route.get("@id") == route_id:
                    route_index = i
                    break
            
            if route_index is not None:
                # Remove the route by index
                response = await self.client.delete(
                    f"{self.api_url}/config/apps/http/servers/srv0/routes/{route_index}"
                )
                
                if response.status_code not in [200, 204]:
                    caddy_logger.warning(
                        f"Failed to remove route {route_id}: {response.status_code} - {response.text}"
                    )
                    
        except Exception as e:
            # If remove fails, just log it - don't prevent other operations
            caddy_logger.warning(f"Failed to remove route {route_id}: {e}")
    
    async def cleanup_revp_routes(self, docker_monitor=None) -> None:
        """Remove only stale Revp routes from Caddy on startup.
        
        This method only removes routes for containers that either:
        1. No longer exist, OR
        2. Exist but don't have Revp labels
        
        This prevents removing routes from other container management systems.
        """
        try:
            caddy_logger.info("Cleaning up stale Revp routes on startup")
            
            # Get current routes
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                caddy_logger.warning("Could not get current routes for cleanup")
                return
            
            routes = routes_response.json()
            
            # If no docker_monitor provided, skip cleanup to be safe
            if not docker_monitor:
                caddy_logger.info("No Docker monitor provided, skipping route cleanup for safety")
                return
            
            revp_routes_found = 0
            routes_to_remove = []
            
            # Find routes with revp_route_ prefix and verify they should be managed by us
            for i, route in enumerate(routes):
                route_id = route.get("@id", "")
                if route_id.startswith("revp_route_"):
                    # Extract container ID from revp_route_ prefix
                    container_part = route_id[11:]  # Remove "revp_route_" prefix
                    
                    # Check if this container should be managed by Revp
                    should_remove = await self._should_remove_route(container_part, docker_monitor)
                    if should_remove:
                        routes_to_remove.append(i)
                        revp_routes_found += 1
                        caddy_logger.debug(f"Found stale Revp route to remove: {route_id}")
                    else:
                        caddy_logger.debug(f"Keeping route for active Revp container: {route_id}")
                else:
                    # Skip all other routes - only process revp_route_ prefixed routes
                    caddy_logger.debug(f"Skipping non-Revp route: {route_id}")
            
            # Remove routes in reverse order to maintain indices
            for route_index in reversed(routes_to_remove):
                try:
                    response = await self.client.delete(
                        f"{self.api_url}/config/apps/http/servers/srv0/routes/{route_index}"
                    )
                    if response.status_code not in [200, 204]:
                        caddy_logger.warning(f"Failed to remove route at index {route_index}: {response.status_code}")
                except Exception as e:
                    caddy_logger.warning(f"Error removing route at index {route_index}: {e}")
            
            if revp_routes_found > 0:
                caddy_logger.info(f"Successfully cleaned up {revp_routes_found} stale Revp routes")
            else:
                caddy_logger.info("No stale Revp routes found to clean up")
                
        except Exception as e:
            caddy_logger.error(f"Error during Revp route cleanup: {e}")
            # Don't raise - startup should continue even if cleanup fails
    
    async def _should_remove_route(self, container_id: str, docker_monitor) -> bool:
        """Check if a route should be removed based on container state.
        
        Returns True ONLY if:
        1. Container exists on a monitored host AND has Revp labels
        
        This conservative approach ensures we only remove routes for containers
        that we can confirm should be managed by this Revp instance.
        """
        try:
            # Check all monitored hosts for this container
            for _, hostname, _ in docker_monitor.hosts_config:
                # Try to inspect the container
                container_info = docker_monitor.inspect_container_sync(hostname, container_id)
                
                if container_info:
                    # Container exists, check if it has Revp labels
                    config = container_info.get("Config", {})
                    labels = config.get("Labels", {})
                    
                    # If container has Revp domain label, it should be managed by us
                    if "snadboy.revp.domain" in labels:
                        caddy_logger.debug(f"Container {container_id} has Revp labels, route will be recreated")
                        return True  # Remove old route, it will be recreated with current config
                    else:
                        caddy_logger.debug(f"Container {container_id} exists but has no Revp labels, keeping route")
                        return False  # Keep the route, it's not ours to manage
            
            # Container doesn't exist on any monitored host - DON'T remove
            # It might be managed by a different system or on a different host
            caddy_logger.debug(f"Container {container_id} not found on monitored hosts, keeping route (might be external)")
            return False  # Conservative: keep routes for containers we can't verify
            
        except Exception as e:
            caddy_logger.warning(f"Error checking container {container_id}: {e}")
            return False  # When in doubt, don't remove
    
    async def get_current_config(self) -> dict:
        """Get current Caddy configuration."""
        try:
            response = await self.client.get(f"{self.api_url}/config/")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            caddy_logger.error(f"Failed to get Caddy config: {e}")
            return {}
    
    def get_status(self) -> dict:
        """Get Caddy manager status."""
        return {
            "api_url": self.api_url,
            "connected": True,  # Will be updated by health check
            "route_count": len(self._routes),
            "routes": {
                domain: container_id[:12]
                for domain, container_id in self._routes.items()
            }
        }