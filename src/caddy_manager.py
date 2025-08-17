"""Caddy reverse proxy management via Admin API."""
import asyncio
import json
from typing import Dict, Optional

import httpx

from .config import settings
from .logger import caddy_logger
from .docker_monitor import ContainerInfo, ServiceInfo


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
        
        # Ensure Caddy is listening on both HTTP and HTTPS ports
        await self.ensure_http_https_listeners()
        
        # Note: Catch-all routes can be added manually if needed via ensure_catchall_route()
        
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
    
    async def ensure_http_https_listeners(self) -> None:
        """Ensure Caddy is listening on both HTTP (80) and HTTPS (443) ports."""
        try:
            caddy_logger.info("Ensuring Caddy listens on both HTTP and HTTPS ports")
            
            # Get current server configuration
            response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0")
            if response.status_code != 200:
                # Server doesn't exist, create it with both listeners
                server_config = {
                    "listen": [":80", ":443"],
                    "routes": []
                }
                create_response = await self.client.put(
                    f"{self.api_url}/config/apps/http/servers/srv0",
                    json=server_config,
                    headers={"Content-Type": "application/json"}
                )
                if create_response.status_code in [200, 201]:
                    caddy_logger.info("Created server with HTTP and HTTPS listeners")
                else:
                    caddy_logger.warning(f"Failed to create server: {create_response.status_code}")
            else:
                # Server exists, check if it has both listeners
                server_config = response.json()
                current_listen = server_config.get("listen", [])
                
                # Check if both ports are configured
                has_http = any(":80" in l for l in current_listen)
                has_https = any(":443" in l for l in current_listen)
                
                if not has_http or not has_https:
                    # Update to include both ports
                    server_config["listen"] = [":80", ":443"]
                    update_response = await self.client.patch(
                        f"{self.api_url}/config/apps/http/servers/srv0",
                        json={"listen": [":80", ":443"]},
                        headers={"Content-Type": "application/json"}
                    )
                    if update_response.status_code in [200, 201]:
                        caddy_logger.info(f"Updated server to listen on both HTTP and HTTPS (was: {current_listen})")
                    else:
                        caddy_logger.warning(f"Failed to update server listeners: {update_response.status_code}")
                else:
                    caddy_logger.info("Server already configured to listen on both HTTP and HTTPS")
                    
        except Exception as e:
            caddy_logger.error(f"Error ensuring HTTP/HTTPS listeners: {e}")
    
    async def add_route(self, container: ContainerInfo, service: 'ServiceInfo') -> None:
        """Add or update a route in Caddy."""
        if not service.is_valid:
            caddy_logger.warning(f"Invalid service configuration for {container.name}:{service.port}")
            return
        
        backend_url = service.backend_url(container.host_ip)
        caddy_logger.info(
            f"Adding route: {service.domain} -> {backend_url} "
            f"(force_ssl: {service.force_ssl}, websocket: {service.support_websocket})"
        )
        
        try:
            # Check if another container is using this domain
            existing_container_id = self._routes.get(service.domain)
            expected_route_id = f"{container.container_id}_{service.port}"
            
            if existing_container_id and existing_container_id != expected_route_id:
                caddy_logger.warning(
                    f"Domain {service.domain} already in use by {existing_container_id}, replacing with {container.container_id[:12]}:{service.port}"
                )
            
            # Create the route configuration
            route_config = self._create_route_config(container, service)
            
            # Apply configuration to Caddy (HTTPS route to srv0)
            await self._apply_route(service.domain, route_config, server="srv0")
            
            # If force_ssl is enabled AND not using cloudflare_tunnel, add HTTP redirect route to srv1
            # Skip redirect for cloudflare_tunnel as Cloudflare handles SSL termination
            if service.force_ssl and not getattr(service, 'cloudflare_tunnel', False):
                redirect_config = self._create_http_redirect_config(service.domain, container.container_id, service.port)
                await self._apply_route(service.domain, redirect_config, server="srv1")
                caddy_logger.info(f"Added HTTP to HTTPS redirect for {service.domain} on srv1")
            elif getattr(service, 'cloudflare_tunnel', False):
                # For cloudflare_tunnel routes, add HTTP route directly to srv1 without redirect
                await self._apply_route(service.domain, route_config, server="srv1")
                caddy_logger.info(f"Added HTTP route for cloudflare_tunnel {service.domain} on srv1")
            
            # Track the route (use container_id:port as unique identifier)
            self._routes[service.domain] = f"{container.container_id}_{service.port}"
            
            caddy_logger.info(f"Successfully added route for {service.domain}")
            
        except Exception as e:
            caddy_logger.error(f"Failed to add route for {service.domain}: {e}")
            raise
    
    async def remove_route(self, container: ContainerInfo) -> None:
        """Remove all routes for a container."""
        if not container.valid_services:
            return
        
        caddy_logger.info(f"Removing routes for container {container.name}")
        
        # Remove each service route
        for port, service in container.valid_services.items():
            try:
                # Check if this container owns the route
                expected_route_owner = f"{container.container_id}_{service.port}"
                    
                if self._routes.get(service.domain) != expected_route_owner:
                    caddy_logger.warning(
                        f"Container {container.container_id[:12]}:{service.port} does not own domain "
                        f"{service.domain}, skipping removal"
                    )
                    continue
                
                # Remove the HTTPS route from srv0
                await self._remove_route(service.domain, container.container_id, service.port, server="srv0")
                
                # Also remove HTTP redirect if it exists (srv1)
                if service.force_ssl:
                    await self._remove_route(service.domain, container.container_id, service.port, server="srv1", is_redirect=True)
                
                # Remove from tracking
                self._routes.pop(service.domain, None)
                
                caddy_logger.info(f"Successfully removed route for {service.domain}")
                
            except Exception as e:
                caddy_logger.error(f"Failed to remove route for {service.domain}: {e}")
    
    async def add_static_route(self, service: ServiceInfo) -> None:
        """Add or update a static route in Caddy."""
        if not service.is_valid or not service.is_static:
            caddy_logger.warning(f"Invalid static service configuration for {service.domain}")
            return
        
        backend_url = service.backend_url()
        caddy_logger.info(
            f"Adding static route: {service.domain} -> {backend_url} "
            f"(force_ssl: {service.force_ssl}, websocket: {service.support_websocket})"
        )
        
        try:
            # Check if another service is using this domain
            existing_route_id = self._routes.get(service.domain)
            if existing_route_id and not existing_route_id.startswith("static_"):
                caddy_logger.warning(
                    f"Domain {service.domain} already in use by container {existing_route_id}, replacing with static route"
                )
            
            # Create the route configuration
            route_config = self._create_static_route_config(service)
            
            # Apply configuration to Caddy (HTTPS route to srv0)
            await self._apply_route(service.domain, route_config, server="srv0")
            
            # If force_ssl is enabled AND not using cloudflare_tunnel, add HTTP redirect route to srv1
            # Skip redirect for cloudflare_tunnel as Cloudflare handles SSL termination
            if service.force_ssl and not getattr(service, 'cloudflare_tunnel', False):
                redirect_config = {
                    "@id": f"revp_static_http_redirect_{service.domain.replace('.', '_')}",
                    "match": [{"host": [service.domain]}],
                    "handle": [{
                        "handler": "static_response",
                        "headers": {
                            "Location": ["https://{http.request.host}{http.request.uri}"]
                        },
                        "status_code": 308
                    }],
                    "terminal": True
                }
                await self._apply_route(service.domain, redirect_config, server="srv1")
                caddy_logger.info(f"Added HTTP to HTTPS redirect for static route {service.domain} on srv1")
            elif getattr(service, 'cloudflare_tunnel', False):
                # For cloudflare_tunnel routes, add HTTP route directly to srv1 without redirect
                route_config = self._create_static_route_config(service)
                await self._apply_route(service.domain, route_config, server="srv1")
                caddy_logger.info(f"Added HTTP route for cloudflare_tunnel static route {service.domain} on srv1")
            
            # Track the route with static prefix
            self._routes[service.domain] = f"static_{service.domain}"
            
            caddy_logger.info(f"Successfully added static route for {service.domain}")
            
        except Exception as e:
            caddy_logger.error(f"Failed to add static route for {service.domain}: {e}")
            raise
    
    async def remove_static_route(self, domain: str) -> None:
        """Remove a static route."""
        try:
            # Check if this is a static route
            route_id = self._routes.get(domain)
            if not route_id or not route_id.startswith("static_"):
                caddy_logger.warning(f"No static route found for domain {domain}")
                return
            
            # Create the static route ID for removal
            static_route_id = f"revp_static_route_{domain.replace('.', '_')}"
            
            # Remove from Caddy using the correct route ID
            await self._remove_route_by_id(static_route_id)
            
            # Remove from tracking
            self._routes.pop(domain, None)
            
            caddy_logger.info(f"Successfully removed static route for {domain}")
            
        except Exception as e:
            caddy_logger.error(f"Failed to remove static route for {domain}: {e}")
    
    async def cleanup_static_routes(self) -> None:
        """Clean up all static routes from Caddy (removes duplicates and stale entries)."""
        try:
            caddy_logger.info("Cleaning up all static routes from Caddy")
            
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                caddy_logger.warning("Could not get current routes for static route cleanup")
                return
            
            routes = routes_response.json()
            if routes is None:
                caddy_logger.info("No routes to clean up")
                return
            
            # Find all static routes (both current and stale)
            static_route_indices = []
            for i, route in enumerate(routes):
                route_id = route.get("@id", "")
                if route_id.startswith("revp_static_route_"):
                    static_route_indices.append(i)
            
            # Remove all static routes in reverse order to maintain indices
            removed_count = 0
            for route_index in reversed(static_route_indices):
                try:
                    response = await self.client.delete(
                        f"{self.api_url}/config/apps/http/servers/srv0/routes/{route_index}"
                    )
                    if response.status_code in [200, 204]:
                        removed_count += 1
                    else:
                        caddy_logger.warning(f"Failed to remove static route at index {route_index}: {response.status_code}")
                except Exception as e:
                    caddy_logger.warning(f"Error removing static route at index {route_index}: {e}")
            
            # Clear static route tracking
            static_domains_to_remove = [
                domain for domain, route_id in self._routes.items() 
                if route_id.startswith("static_")
            ]
            for domain in static_domains_to_remove:
                self._routes.pop(domain, None)
            
            caddy_logger.info(f"Successfully cleaned up {removed_count} static routes from Caddy")
                
        except Exception as e:
            caddy_logger.error(f"Error during static route cleanup: {e}")
    
    async def ensure_catchall_route(self) -> None:
        """Ensure a catch-all route exists for undefined domains."""
        try:
            caddy_logger.info("Ensuring catch-all route exists for undefined domains")
            
            # Create catch-all route configuration
            catchall_config = {
                "@id": "revp_catchall_route",
                "match": [{
                    "host": ["*.snadboy.com"]
                }],
                "handle": [{
                    "handler": "file_server",
                    "root": "/var/www/error_pages",
                    "index_names": ["404.html"]
                }],
                "terminal": False  # Lower priority than specific routes
            }
            
            # Check if catch-all route already exists
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                caddy_logger.warning("Could not get current routes for catch-all setup")
                return
            
            routes = routes_response.json()
            if routes is None:
                routes = []
            
            # Look for existing catch-all route
            catchall_index = None
            for i, route in enumerate(routes):
                if route.get("@id") == "revp_catchall_route":
                    catchall_index = i
                    break
            
            if catchall_index is not None:
                # Update existing catch-all route
                response = await self.client.put(
                    f"{self.api_url}/config/apps/http/servers/srv0/routes/{catchall_index}",
                    json=catchall_config,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code in [200, 201]:
                    caddy_logger.info("Successfully updated catch-all route")
                else:
                    caddy_logger.warning(f"Failed to update catch-all route: {response.status_code}")
            else:
                # Add new catch-all route at the end (lowest priority)
                response = await self.client.post(
                    f"{self.api_url}/config/apps/http/servers/srv0/routes",
                    json=catchall_config,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code in [200, 201]:
                    caddy_logger.info("Successfully added catch-all route")
                else:
                    caddy_logger.warning(f"Failed to add catch-all route: {response.status_code}")
                    
        except Exception as e:
            caddy_logger.error(f"Error ensuring catch-all route: {e}")

    async def update_static_routes(self, static_routes: list) -> None:
        """Update all static routes based on configuration."""
        caddy_logger.info(f"Updating static routes: {len(static_routes)} routes")
        
        # First, clean up all existing static routes to prevent duplicates
        await self.cleanup_static_routes()
        
        # Add all static routes fresh, skipping those with DNS failures
        skipped = 0
        for static_route in static_routes:
            # Check if DNS validation failed
            if hasattr(static_route, 'dns_resolved') and static_route.dns_resolved == False:
                skipped += 1
                caddy_logger.warning(f"Skipping static route {static_route.domain} due to DNS failure: {static_route.dns_error}")
                continue
                
            service = ServiceInfo(static_route=static_route)
            await self.add_static_route(service)
        
        if skipped > 0:
            caddy_logger.warning(f"Skipped {skipped} static routes due to DNS resolution failures")
    
    def _create_static_route_config(self, service: ServiceInfo) -> dict:
        """Create Caddy route configuration for a static service (HTTPS only now)."""
        # Reverse proxy handler
        # For static routes, extract host:port from backend_url, ignore path
        backend_dial = service._static_backend_url.replace("http://", "").replace("https://", "")
        # Remove any path component
        if "/" in backend_dial:
            backend_dial = backend_dial.split("/")[0]
        
        reverse_proxy_handler = {
            "handler": "reverse_proxy",
            "upstreams": [{"dial": backend_dial}]
        }
        
        # Add transport configuration for HTTPS backends
        if service._static_backend_url.startswith("https://"):
            transport_config = {
                "protocol": "http",
                "tls": {}
            }
            
            # Add TLS insecure skip verify if enabled (for self-signed certs)
            if hasattr(service, 'tls_insecure_skip_verify') and service.tls_insecure_skip_verify:
                transport_config["tls"]["insecure_skip_verify"] = True
                caddy_logger.info(f"TLS skip verify enabled for {service.domain} (use only for self-signed certs)")
            
            reverse_proxy_handler["transport"] = transport_config
        
        # Add path rewriting if backend_path is not "/"
        if service.backend_path != "/":
            backend_path = service.backend_path.rstrip("/")
            reverse_proxy_handler["rewrite"] = {
                "uri": backend_path + "{http.request.uri}"
            }
        
        # Configure headers for proper forwarding
        headers_config = {
            "request": {
                "set": {}
            }
        }
        
        # Check if Cloudflare tunnel is being used
        if hasattr(service, 'cloudflare_tunnel') and service.cloudflare_tunnel:
            # Use Cloudflare-specific headers for accurate client IP and protocol
            headers_config["request"]["set"]["X-Forwarded-Proto"] = ["https"]
            headers_config["request"]["set"]["X-Real-IP"] = ["{http.request.header.CF-Connecting-IP}"]
            headers_config["request"]["set"]["X-Forwarded-For"] = ["{http.request.header.CF-Connecting-IP}"]
            headers_config["request"]["set"]["X-Forwarded-Host"] = ["{http.request.host}"]
            caddy_logger.info(f"Cloudflare tunnel headers enabled for {service.domain}")
        else:
            # Standard X-Forwarded headers for direct connections
            headers_config["request"]["set"]["X-Forwarded-For"] = ["{http.request.header.X-Forwarded-For}, {http.request.remote.host}"]
            headers_config["request"]["set"]["X-Forwarded-Proto"] = ["{http.request.scheme}"]
            headers_config["request"]["set"]["X-Forwarded-Host"] = ["{http.request.host}"]
            headers_config["request"]["set"]["X-Real-IP"] = ["{http.request.remote.host}"]
        
        # WebSocket support - add Connection and Upgrade headers
        if service.support_websocket:
            headers_config["request"]["set"]["Connection"] = ["{http.request.header.Connection}"]
            headers_config["request"]["set"]["Upgrade"] = ["{http.request.header.Upgrade}"]
        
        # Special handling for Home Assistant
        if service.domain == "ha.snadboy.com":
            # Home Assistant requires specific header handling
            headers_config["request"]["set"]["Host"] = ["{http.request.host}"]
        
        reverse_proxy_handler["headers"] = headers_config
        
        # Create route configuration with unique ID (HTTPS only)
        route_id = f"revp_static_route_{service.domain.replace('.', '_')}"
        
        # Build the route configuration
        config = {
            "@id": route_id,
            "match": [{"host": [service.domain]}],
            "handle": [reverse_proxy_handler],
            "terminal": True
        }
        
        return config
    
    def _create_http_redirect_config(self, domain: str, container_id: str, port: str) -> dict:
        """Create HTTP to HTTPS redirect configuration."""
        return {
            "@id": f"revp_http_redirect_{container_id}_{port}",
            "match": [{"host": [domain]}],
            "handle": [{
                "handler": "static_response",
                "headers": {
                    "Location": ["https://{http.request.host}{http.request.uri}"]
                },
                "status_code": 308
            }],
            "terminal": True
        }
    
    def _create_route_config(self, container: ContainerInfo, service: 'ServiceInfo') -> dict:
        """Create Caddy route configuration for a service (HTTPS only now)."""
        # Basic reverse proxy configuration
        # Use resolved_host_port if available, otherwise fall back to service port
        backend_port = service.resolved_host_port if service.resolved_host_port else service.port
        
        # Create the reverse proxy handler directly
        reverse_proxy_handler = {
            "handler": "reverse_proxy",
            "upstreams": [{
                "dial": f"{container.host_ip}:{backend_port}"
            }],
            "transport": {
                "protocol": "http",
                "tls": {} if service.backend_proto == "https" else None
            }
        }
        
        # Configure headers for proper forwarding
        headers_config = {
            "request": {
                "set": {}
            }
        }
        
        # Check if Cloudflare tunnel is being used
        if hasattr(service, 'cloudflare_tunnel') and service.cloudflare_tunnel:
            # Use Cloudflare-specific headers for accurate client IP and protocol
            headers_config["request"]["set"]["X-Forwarded-Proto"] = ["https"]
            headers_config["request"]["set"]["X-Real-IP"] = ["{http.request.header.CF-Connecting-IP}"]
            headers_config["request"]["set"]["X-Forwarded-For"] = ["{http.request.header.CF-Connecting-IP}"]
            headers_config["request"]["set"]["X-Forwarded-Host"] = ["{http.request.host}"]
            caddy_logger.info(f"Cloudflare tunnel headers enabled for {service.domain}")
        else:
            # Standard X-Forwarded headers for direct connections
            headers_config["request"]["set"]["X-Forwarded-For"] = ["{http.request.header.X-Forwarded-For}, {http.request.remote.host}"]
            headers_config["request"]["set"]["X-Forwarded-Proto"] = ["{http.request.scheme}"]
            headers_config["request"]["set"]["X-Forwarded-Host"] = ["{http.request.host}"]
            headers_config["request"]["set"]["X-Real-IP"] = ["{http.request.remote.host}"]
        
        # Add websocket support if enabled
        if service.support_websocket:
            headers_config["request"]["set"]["Connection"] = ["{http.request.header.Connection}"]
            headers_config["request"]["set"]["Upgrade"] = ["{http.request.header.Upgrade}"]
        
        reverse_proxy_handler["headers"] = headers_config
        
        # Remove None values
        if reverse_proxy_handler["transport"]["tls"] is None:
            del reverse_proxy_handler["transport"]["tls"]
        
        # Handle backend path if not root
        if service.backend_path != "/":
            reverse_proxy_handler["rewrite"] = {
                "strip_path_prefix": service.backend_path.rstrip('/')
            }
        
        # Build the route configuration (HTTPS only)
        config = {
            "@id": f"revp_route_{container.container_id}_{service.port}",
            "match": [{"host": [service.domain]}],
            "handle": [reverse_proxy_handler],
            "terminal": True
        }
        
        return config
    
    async def _apply_route(self, domain: str, route_config: dict, server: str = "srv0") -> None:
        """Apply a route configuration to Caddy."""
        route_id = route_config.get("@id")
        if not route_id:
            raise Exception("Route configuration missing @id")
        
        # First, remove any existing routes with the same ID to prevent duplicates
        await self._remove_route_by_id(route_id)
        
        # Check if routes array exists, if not initialize it
        routes_response = await self.client.get(
            f"{self.api_url}/config/apps/http/servers/{server}/routes"
        )
        
        if routes_response.status_code == 200 and routes_response.json() is None:
            # Initialize empty routes array if it doesn't exist
            init_response = await self.client.put(
                f"{self.api_url}/config/apps/http/servers/{server}/routes",
                json=[],
                headers={"Content-Type": "application/json"}
            )
            if init_response.status_code not in [200, 201]:
                raise Exception(
                    f"Failed to initialize routes array: {init_response.status_code} - {init_response.text}"
                )
        
        # Add the new route to the routes array
        response = await self.client.post(
            f"{self.api_url}/config/apps/http/servers/{server}/routes",
            json=route_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(
                f"Failed to apply route: {response.status_code} - {response.text}"
            )
    
    async def _remove_route(self, domain: str, container_id: str, port: str, server: str = "srv0", is_redirect: bool = False) -> None:
        """Remove a route configuration from Caddy."""
        # Construct the route ID based on whether it's a redirect or main route
        if is_redirect:
            route_id = f"revp_http_redirect_{container_id}_{port}"
        else:
            route_id = f"revp_route_{container_id}_{port}"
        
        # Get existing routes to find the index
        try:
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/{server}/routes")
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
                    f"{self.api_url}/config/apps/http/servers/{server}/routes/{route_index}"
                )
                
                if response.status_code not in [200, 204]:
                    raise Exception(
                        f"Failed to remove route: {response.status_code} - {response.text}"
                    )
                    
        except Exception as e:
            # If remove fails, just log it - don't prevent other operations
            caddy_logger.warning(f"Failed to remove route for {domain} on {server}: {e}")
    
    async def _route_exists(self, route_id: str) -> bool:
        """Check if a route with the given ID already exists."""
        try:
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                return False
            
            routes = routes_response.json()
            if routes is None:
                return False
            
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
            # Only remove routes with revp_ prefix (both revp_route_ and revp_static_route_)
            if not (route_id.startswith("revp_route_") or route_id.startswith("revp_static_route_")):
                caddy_logger.debug(f"Skipping removal of non-Revp route: {route_id}")
                return
                
            routes_response = await self.client.get(f"{self.api_url}/config/apps/http/servers/srv0/routes")
            if routes_response.status_code != 200:
                return  # No routes to remove
            
            routes = routes_response.json()
            if routes is None:
                return  # No routes to remove
            
            # Find and remove all routes with this ID (in case of duplicates)
            removed_count = 0
            for i in reversed(range(len(routes))):
                route = routes[i]
                if route.get("@id") == route_id:
                    try:
                        response = await self.client.delete(
                            f"{self.api_url}/config/apps/http/servers/srv0/routes/{i}"
                        )
                        
                        if response.status_code in [200, 204]:
                            removed_count += 1
                            caddy_logger.debug(f"Removed route {route_id} at index {i}")
                        else:
                            caddy_logger.warning(
                                f"Failed to remove route {route_id} at index {i}: {response.status_code} - {response.text}"
                            )
                    except Exception as e:
                        caddy_logger.warning(f"Error removing route {route_id} at index {i}: {e}")
            
            if removed_count > 0:
                caddy_logger.info(f"Removed {removed_count} instance(s) of route {route_id}")
                    
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
            if routes is None:
                caddy_logger.info("No routes to clean up on startup")
                return
            
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
                    # New format: revp_route_{container_id}_{port}
                    container_part = route_id[11:]  # Remove "revp_route_" prefix
                    
                    # Extract just the container ID (before the first underscore in the new format)
                    if "_" in container_part:
                        container_id = container_part.split("_")[0]
                    else:
                        # Legacy format without port
                        container_id = container_part
                    
                    # Check if this container should be managed by Revp
                    should_remove = await self._should_remove_route(container_id, docker_monitor)
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
                    
                    # Check for port-based Revp labels (new format)
                    has_revp_labels = any(key.startswith("snadboy.revp.") and len(key.split(".")) == 4 
                                         and key.split(".")[2].isdigit() 
                                         for key in labels.keys())
                    
                    if has_revp_labels:
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
    
    async def get_config(self) -> dict:
        """Get current Caddy configuration (alias for get_current_config)."""
        return await self.get_current_config()
    
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