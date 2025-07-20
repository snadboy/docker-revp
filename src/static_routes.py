"""Static routes configuration management for Docker Reverse Proxy."""
import asyncio
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, field_validator
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
    
    def __del__(self):
        """Cleanup file watcher on destruction."""
        self.stop_watching()