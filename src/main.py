"""Main entry point for Docker Monitor."""
import asyncio
import signal
import sys
from typing import Optional

import uvicorn

from .config import settings
from .logger import main_logger
from .ssh_config import SSHConfigManager
from .docker_monitor import DockerMonitor
from .caddy_manager import CaddyManager
from .static_routes import StaticRoutesManager
from .api.app import create_app


class DockerMonitorService:
    """Main service orchestrator."""
    
    def __init__(self):
        self.ssh_manager: Optional[SSHConfigManager] = None
        self.docker_monitor: Optional[DockerMonitor] = None
        self.caddy_manager: Optional[CaddyManager] = None
        self.static_routes_manager: Optional[StaticRoutesManager] = None
        self.app = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start all components."""
        main_logger.info("Starting Docker Monitor service")
        
        try:
            # Validate configuration
            settings.validate()
            main_logger.info("Configuration validated successfully")
            
            # Set up SSH configuration
            main_logger.info("Setting up SSH configuration")
            self.ssh_manager = SSHConfigManager()
            self.ssh_manager.setup()
            
            # Initialize Caddy manager
            main_logger.info("Initializing Caddy manager")
            self.caddy_manager = CaddyManager()
            await self.caddy_manager.start()
            
            # Initialize static routes manager
            main_logger.info("Initializing static routes manager")
            self.static_routes_manager = StaticRoutesManager(settings.static_routes_file)
            static_routes = self.static_routes_manager.get_routes()
            if static_routes:
                main_logger.info(f"Loading {len(static_routes)} static routes into Caddy")
                await self.caddy_manager.update_static_routes(static_routes)
            
            # Start file watching for static routes
            self.static_routes_manager.start_watching(self._on_static_routes_changed)
            
            # Initialize Docker monitor
            main_logger.info("Initializing Docker monitor")
            self.docker_monitor = DockerMonitor(caddy_manager=self.caddy_manager)
            await self.docker_monitor.start()
            
            # Create FastAPI app
            self.app = create_app(
                docker_monitor=self.docker_monitor,
                caddy_manager=self.caddy_manager,
                ssh_manager=self.ssh_manager,
                static_routes_manager=self.static_routes_manager
            )
            
            main_logger.info("All components started successfully")
            
        except Exception as e:
            main_logger.error(f"Failed to start service: {e}")
            await self.stop()
            raise
    
    async def _on_static_routes_changed(self, new_routes: list) -> None:
        """Handle static routes file changes."""
        try:
            main_logger.info(f"Static routes changed, updating Caddy configuration ({len(new_routes)} routes)")
            await self.caddy_manager.update_static_routes(new_routes)
            main_logger.info("Static routes successfully updated in Caddy")
        except Exception as e:
            main_logger.error(f"Error updating static routes in Caddy: {e}")
    
    async def stop(self) -> None:
        """Stop all components."""
        main_logger.info("Stopping Docker Monitor service")
        
        # Stop Docker monitor
        if self.docker_monitor:
            await self.docker_monitor.stop()
        
        # Stop Caddy manager
        if self.caddy_manager:
            await self.caddy_manager.stop()
        
        # Stop static routes file watcher
        if self.static_routes_manager:
            self.static_routes_manager.stop_watching()
        
        main_logger.info("Docker Monitor service stopped")
    
    async def run_api_server(self) -> None:
        """Run the FastAPI server."""
        # Parse host and port from api_bind
        host, port_str = settings.api_bind.split(':')
        port = int(port_str)
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level=settings.log_level.lower(),
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # Start server in background
        await server.serve()
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        main_logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    service = DockerMonitorService()
    
    # Set up signal handlers
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, service.signal_handler)
    
    try:
        # Start service
        await service.start()
        
        # Start API server and wait for shutdown
        api_task = asyncio.create_task(service.run_api_server())
        shutdown_task = asyncio.create_task(service.wait_for_shutdown())
        
        # Wait for either API server to finish or shutdown signal
        done, pending = await asyncio.wait(
            [api_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        main_logger.info("Received keyboard interrupt")
    except Exception as e:
        main_logger.error(f"Service error: {e}")
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())