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
        config = {
            "@id": f"route_{container.container_id}",
            "match": [{"host": [container.domain]}],
            "handle": [{
                "handler": "reverse_proxy",
                "upstreams": [{
                    "dial": f"{container.host_ip}:{container.backend_port}"
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
        # Caddy expects routes to be part of a server configuration
        server_config = {
            "listen": [":443", ":80"],
            "routes": [route_config]
        }
        
        # If force_ssl is enabled, add automatic HTTPS
        if route_config.get("force_ssl", True):
            server_config["automatic_https"] = {
                "disable_redirects": False
            }
        
        # Create the full configuration path for this domain
        config_path = f"/config/apps/http/servers/{domain.replace('.', '_')}"
        
        # Apply the configuration
        response = await self.client.put(
            f"{self.api_url}{config_path}",
            json=server_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(
                f"Failed to apply route: {response.status_code} - {response.text}"
            )
    
    async def _remove_route(self, domain: str) -> None:
        """Remove a route configuration from Caddy."""
        config_path = f"/config/apps/http/servers/{domain.replace('.', '_')}"
        
        response = await self.client.delete(f"{self.api_url}{config_path}")
        
        if response.status_code not in [200, 204, 404]:
            raise Exception(
                f"Failed to remove route: {response.status_code} - {response.text}"
            )
    
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