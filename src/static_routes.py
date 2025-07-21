"""Static routes configuration management for Docker Reverse Proxy."""
import asyncio
import tempfile
import shutil
import time
import yaml
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, field_validator, ValidationError
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

from .logger import api_logger


class StaticRoute(BaseModel):
    """Static route configuration."""
    domain: str
    backend_url: str
    backend_path: str = "/"
    force_ssl: bool = True
    support_websocket: bool = False
    
    @field_validator('domain')
    def validate_domain(cls, v):
        """Validate domain format."""
        if not v or not isinstance(v, str):
            raise ValueError("Domain must be a non-empty string")
        return v.strip()
    
    @field_validator('backend_url')
    def validate_backend_url(cls, v):
        """Validate backend URL format."""
        if not v or not isinstance(v, str):
            raise ValueError("Backend URL must be a non-empty string")
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Backend URL must start with http:// or https://")
        return v.strip()


class StaticRoutesConfig(BaseModel):
    """Static routes configuration container."""
    static_routes: List[StaticRoute] = []


class StaticRoutesFileHandler(FileSystemEventHandler):
    """File system event handler for static routes configuration."""
    
    def __init__(self, manager: 'StaticRoutesManager'):
        self.manager = manager
        
    def on_modified(self, event):
        """Handle file modification events."""
        api_logger.debug(f"File event: {event.event_type} on {event.src_path}")
        if not event.is_directory and event.src_path == str(self.manager.config_file_path):
            api_logger.info(f"Static routes file modified: {event.src_path}")
            # Use asyncio to run the async callback
            if self.manager._on_change_callback:
                # Get the running event loop and schedule the coroutine
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.manager._trigger_reload())
                except RuntimeError:
                    # No running loop, create a new task
                    asyncio.run(self.manager._trigger_reload())
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path == str(self.manager.config_file_path):
            api_logger.info(f"Static routes file created: {event.src_path}")
            if self.manager._on_change_callback:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.manager._trigger_reload())
                except RuntimeError:
                    asyncio.run(self.manager._trigger_reload())


class StaticRoutesManager:
    """Manages static routes configuration from YAML file with file watching."""
    
    def __init__(self, config_file_path: str):
        self.config_file_path = Path(config_file_path)
        self._routes: List[StaticRoute] = []
        self._file_mtime: Optional[float] = None
        self._observer: Optional[Observer] = None
        self._on_change_callback: Optional[Callable] = None
        
    def load_routes(self) -> List[StaticRoute]:
        """Load static routes from YAML file."""
        if not self.config_file_path.exists():
            api_logger.info(f"Static routes file not found at {self.config_file_path}, no static routes loaded")
            self._routes = []
            return self._routes
        
        try:
            # Check if file has been modified
            current_mtime = self.config_file_path.stat().st_mtime
            if self._file_mtime == current_mtime and self._routes:
                return self._routes
            
            api_logger.info(f"Loading static routes from {self.config_file_path}")
            
            with open(self.config_file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                api_logger.warning("Static routes file is empty")
                self._routes = []
                return self._routes
            
            # Parse and validate configuration
            config = StaticRoutesConfig(**data)
            self._routes = config.static_routes
            self._file_mtime = current_mtime
            
            api_logger.info(f"Loaded {len(self._routes)} static routes")
            for route in self._routes:
                api_logger.debug(f"Static route: {route.domain} -> {route.backend_url}")
            
            return self._routes
            
        except yaml.YAMLError as e:
            api_logger.error(f"Error parsing static routes YAML: {e}")
            return []
        except Exception as e:
            api_logger.error(f"Error loading static routes: {e}")
            return []
    
    def get_routes(self) -> List[StaticRoute]:
        """Get current static routes, reloading if file changed."""
        return self.load_routes()
    
    def get_routes_by_domain(self) -> Dict[str, StaticRoute]:
        """Get static routes indexed by domain."""
        return {route.domain: route for route in self.get_routes()}
    
    def start_watching(self, on_change_callback: Callable = None) -> None:
        """Start watching the static routes file for changes."""
        self._on_change_callback = on_change_callback
        
        # Only watch if the file exists or its parent directory exists
        watch_path = self.config_file_path.parent if self.config_file_path.parent.exists() else None
        
        if watch_path:
            api_logger.info(f"Starting file watcher for static routes: {self.config_file_path}")
            api_logger.info(f"Watching directory: {watch_path}")
            
            # Use PollingObserver for better compatibility with Docker volumes
            self._observer = PollingObserver()
            event_handler = StaticRoutesFileHandler(self)
            self._observer.schedule(event_handler, str(watch_path), recursive=False)
            self._observer.start()
            
            # Log observer status
            api_logger.debug(f"File watcher started, is_alive: {self._observer.is_alive()}")
        else:
            api_logger.warning(f"Cannot watch static routes file: parent directory does not exist: {self.config_file_path.parent}")
    
    def stop_watching(self) -> None:
        """Stop watching the static routes file."""
        if self._observer:
            api_logger.info("Stopping static routes file watcher")
            self._observer.stop()
            self._observer.join()
            self._observer = None
    
    async def _trigger_reload(self) -> None:
        """Trigger reload of static routes and call the callback."""
        try:
            # Small delay to ensure file write is complete
            await asyncio.sleep(0.5)
            
            # Reload routes
            old_routes = len(self._routes)
            new_routes = self.load_routes()
            
            api_logger.info(f"Static routes reloaded: {old_routes} -> {len(new_routes)} routes")
            
            # Call the callback if provided
            if self._on_change_callback:
                await self._on_change_callback(new_routes)
                
        except Exception as e:
            api_logger.error(f"Error during static routes reload: {e}")
    
    def save_routes(self, routes: List[StaticRoute]) -> bool:
        """
        Save static routes to YAML file atomically.
        
        Args:
            routes: List of StaticRoute objects to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create configuration object
            config = StaticRoutesConfig(static_routes=routes)
            
            # Convert to dict for YAML serialization
            config_dict = {
                "static_routes": [route.model_dump() for route in routes]
            }
            
            # Create YAML content with header comment
            yaml_content = self._generate_yaml_content(config_dict)
            
            # Write atomically using temp file
            success = self._write_file_atomic(yaml_content)
            
            if success:
                # Update internal state
                self._routes = routes
                self._file_mtime = self.config_file_path.stat().st_mtime if self.config_file_path.exists() else None
                api_logger.info(f"Successfully saved {len(routes)} static routes to {self.config_file_path}")
                return True
            else:
                api_logger.error(f"Failed to save static routes to {self.config_file_path}")
                return False
                
        except Exception as e:
            api_logger.error(f"Error saving static routes: {e}")
            return False
    
    def add_route(self, route: StaticRoute) -> bool:
        """
        Add a new static route.
        
        Args:
            route: StaticRoute object to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load current routes
            current_routes = self.get_routes()
            
            # Check for domain conflicts
            if any(existing.domain == route.domain for existing in current_routes):
                api_logger.warning(f"Route with domain {route.domain} already exists")
                return False
            
            # Add new route
            updated_routes = current_routes + [route]
            
            # Save updated routes
            return self.save_routes(updated_routes)
            
        except Exception as e:
            api_logger.error(f"Error adding static route: {e}")
            return False
    
    def update_route(self, domain: str, updated_route: StaticRoute) -> bool:
        """
        Update an existing static route.
        
        Args:
            domain: Domain of the route to update
            updated_route: New StaticRoute object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load current routes
            current_routes = self.get_routes()
            
            # Find and update the route
            updated_routes = []
            route_found = False
            
            for route in current_routes:
                if route.domain == domain:
                    updated_routes.append(updated_route)
                    route_found = True
                else:
                    updated_routes.append(route)
            
            if not route_found:
                api_logger.warning(f"Route with domain {domain} not found for update")
                return False
            
            # Check for domain conflicts if domain changed
            if updated_route.domain != domain:
                if any(existing.domain == updated_route.domain for existing in updated_routes if existing.domain != updated_route.domain):
                    api_logger.warning(f"Cannot update route: domain {updated_route.domain} already exists")
                    return False
            
            # Save updated routes
            return self.save_routes(updated_routes)
            
        except Exception as e:
            api_logger.error(f"Error updating static route: {e}")
            return False
    
    def delete_route(self, domain: str) -> bool:
        """
        Delete a static route by domain.
        
        Args:
            domain: Domain of the route to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load current routes
            current_routes = self.get_routes()
            
            # Filter out the route to delete
            updated_routes = [route for route in current_routes if route.domain != domain]
            
            if len(updated_routes) == len(current_routes):
                api_logger.warning(f"Route with domain {domain} not found for deletion")
                return False
            
            # Save updated routes
            return self.save_routes(updated_routes)
            
        except Exception as e:
            api_logger.error(f"Error deleting static route: {e}")
            return False
    
    def get_route_by_domain(self, domain: str) -> Optional[StaticRoute]:
        """
        Get a specific route by domain.
        
        Args:
            domain: Domain to search for
            
        Returns:
            StaticRoute if found, None otherwise
        """
        routes = self.get_routes()
        for route in routes:
            if route.domain == domain:
                return route
        return None
    
    def validate_route(self, route_data: Dict[str, Any]) -> StaticRoute:
        """
        Validate route data and return StaticRoute object.
        
        Args:
            route_data: Dictionary with route configuration
            
        Returns:
            StaticRoute: Validated route object
            
        Raises:
            ValidationError: If validation fails
        """
        return StaticRoute(**route_data)
    
    def _generate_yaml_content(self, config_dict: Dict[str, Any]) -> str:
        """Generate YAML content with header comments."""
        header = """# Static routes configuration for RevP
# This file is automatically monitored for changes
# 
# WARNING: While you can edit this file manually, it's recommended to use
# the dashboard interface to prevent configuration conflicts and ensure
# proper validation.
#
# Format:
# static_routes:
#   - domain: example.com
#     backend_url: http://backend-server:8080
#     backend_path: /
#     force_ssl: true
#     support_websocket: false

"""
        
        yaml_content = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
        return header + yaml_content
    
    def _write_file_atomic(self, content: str) -> bool:
        """
        Write content to file atomically using temp file and rename.
        
        Args:
            content: Content to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary file in same directory
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    dir=self.config_file_path.parent,
                    prefix=f".{self.config_file_path.name}.tmp",
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    temp_file = f.name
                    
                    # Try to acquire lock on original file if it exists (Unix only)
                    lock_acquired = False
                    if self.config_file_path.exists() and HAS_FCNTL:
                        try:
                            with open(self.config_file_path, 'r') as lock_file:
                                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                                lock_acquired = True
                        except (IOError, OSError):
                            # File is locked by another process, wait briefly
                            time.sleep(0.1)
                    
                    # Write content to temp file
                    f.write(content)
                    f.flush()
                
                # Atomically replace original file with temp file
                shutil.move(temp_file, self.config_file_path)
                
                # Set appropriate permissions
                self.config_file_path.chmod(0o644)
                
                return True
                
            except Exception as e:
                # Clean up temp file if it exists
                if temp_file and Path(temp_file).exists():
                    try:
                        Path(temp_file).unlink()
                    except:
                        pass
                raise e
                
        except Exception as e:
            api_logger.error(f"Error writing file atomically: {e}")
            return False
    
    def get_file_info(self) -> Dict[str, Any]:
        """
        Get information about the static routes file.
        
        Returns:
            Dict with file information
        """
        try:
            if not self.config_file_path.exists():
                return {
                    "exists": False,
                    "path": str(self.config_file_path),
                    "size": 0,
                    "mtime": None,
                    "routes_count": 0
                }
            
            stat = self.config_file_path.stat()
            routes = self.get_routes()
            
            return {
                "exists": True,
                "path": str(self.config_file_path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "routes_count": len(routes),
                "last_modified": time.ctime(stat.st_mtime)
            }
            
        except Exception as e:
            api_logger.error(f"Error getting file info: {e}")
            return {"error": str(e)}

    def __del__(self):
        """Cleanup file watcher on destruction."""
        self.stop_watching()