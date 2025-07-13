"""Docker container monitoring and event handling."""
import asyncio
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .logger import docker_logger


class ContainerInfo:
    """Container information and metadata."""
    
    def __init__(self, container_id: str, host: str, host_ip: str, labels: dict, name: str):
        self.container_id = container_id
        self.host = host
        self.host_ip = host_ip
        self.name = name
        self.labels = labels
        self.last_seen = datetime.utcnow()
        
        # Extract reverse proxy configuration
        self.domain = labels.get("snadboy.revp.domain", "")
        self.backend_port = labels.get("snadboy.revp.backend-port", "")
        self.backend_proto = labels.get("snadboy.revp.backend-proto", "https")
        self.backend_path = labels.get("snadboy.revp.backend-path", "/")
        self.force_ssl = labels.get("snadboy.revp.force-ssl", "true").lower() == "true"
    
    @property
    def is_valid(self) -> bool:
        """Check if container has valid reverse proxy configuration."""
        return bool(self.domain and self.backend_port)
    
    @property
    def backend_url(self) -> str:
        """Get the backend URL for this container."""
        path = self.backend_path if self.backend_path.startswith('/') else f"/{self.backend_path}"
        return f"{self.backend_proto}://{self.host_ip}:{self.backend_port}{path}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "container_id": self.container_id,
            "host": self.host,
            "host_ip": self.host_ip,
            "name": self.name,
            "domain": self.domain,
            "backend_url": self.backend_url,
            "force_ssl": self.force_ssl,
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
    
    async def _handle_container_start(self, alias: str, host: str, host_ip: str, container_id: str) -> None:
        """Handle container start event."""
        try:
            # Get container details
            container_info = await self._get_container_info(alias, container_id)
            
            if not container_info:
                return
            
            # Check if container has our labels
            labels = container_info.get("Labels", {})
            if "snadboy.revp.domain" not in labels:
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
                    f"Container {container.name} has snadboy.revp.domain but missing backend-port"
                )
                return
            
            # Store container
            self.containers[container_id] = container
            
            docker_logger.info(
                f"Detected container {container.name} on {host} "
                f"with domain {container.domain} -> {container.backend_url}"
            )
            
            # Update Caddy
            if self.caddy_manager:
                await self.caddy_manager.add_route(container)
            
        except Exception as e:
            docker_logger.error(f"Error handling container start: {e}")
    
    async def _handle_container_stop(self, container_id: str) -> None:
        """Handle container stop event."""
        container = self.containers.get(container_id)
        
        if not container:
            return
        
        docker_logger.info(
            f"Container {container.name} stopped, removing route for {container.domain}"
        )
        
        # Remove from Caddy
        if self.caddy_manager:
            await self.caddy_manager.remove_route(container)
        
        # Remove from tracking
        del self.containers[container_id]
    
    async def _get_container_info(self, alias: str, container_id: str) -> Optional[dict]:
        """Get detailed container information."""
        try:
            cmd = [
                "docker", "-H", f"ssh://{alias}",
                "inspect", container_id
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                docker_logger.error(f"Failed to inspect container: {stderr.decode()}")
                return None
            
            containers = json.loads(stdout.decode())
            return containers[0] if containers else None
            
        except Exception as e:
            docker_logger.error(f"Error getting container info: {e}")
            return None
    
    async def _reconciliation_loop(self) -> None:
        """Periodically reconcile container state."""
        await asyncio.sleep(10)  # Initial delay
        
        while self._running:
            try:
                docker_logger.info("Starting reconciliation")
                await self._reconcile_all_hosts()
                docker_logger.info("Reconciliation completed")
            except Exception as e:
                docker_logger.error(f"Reconciliation error: {e}")
            
            await asyncio.sleep(settings.reconcile_interval)
    
    async def _reconcile_all_hosts(self) -> None:
        """Reconcile containers from all hosts."""
        seen_containers: Set[str] = set()
        
        # Check all hosts
        tasks = []
        for alias, host, port in self.hosts_config:
            task = self._reconcile_host(alias, host, port, seen_containers)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
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
    
    async def _reconcile_host(self, alias: str, host: str, port: int, seen_containers: Set[str]) -> None:
        """Reconcile containers from a specific host."""
        try:
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
            for line in stdout.decode().strip().split('\n'):
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
            host_status[container.host]["domains"].append(container.domain)
        
        return {
            "total_containers": len(self.containers),
            "hosts": host_status,
            "monitored_hosts": [
                {"alias": alias, "host": host, "port": port}
                for alias, host, port in self.hosts_config
            ]
        }